# 파이프라인 잡 — NEW 항목을 중복·규칙·점수·LLM 관문에 차례로 통과시킨다

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_rules, get_settings
from app.db.models import Decision, Item, Source, Summary
from app.db.session import session_scope
from app.log import get_logger
from app.pipeline import llm
from app.pipeline.dedupe import find_cluster, mention_count
from app.pipeline.rules import apply_rules
from app.pipeline.scoring import score_item
from app.schemas import ItemStatus, Stage

BATCH_SIZE = 50
log = get_logger(__name__)


def _record(item: Item, stage: Stage, passed: bool, details: dict[str, object]) -> Decision:
    return Decision(
        item_id=item.id, stage=stage.value, passed=passed, score=item.score, details=details
    )


async def _llm_calls_today(session: AsyncSession) -> int:
    since = datetime.now(UTC) - timedelta(days=1)
    stmt = select(func.count()).select_from(Summary).where(Summary.created_at >= since)
    return (await session.execute(stmt)).scalar_one()


async def _claim_batch(session: AsyncSession) -> list[tuple[Item, Source]]:
    """점수가 높을 항목부터 처리하도록 최신순으로 집는다."""
    stmt = (
        select(Item, Source)
        .join(Source, Source.id == Item.source_id)
        .where(Item.status == ItemStatus.NEW.value)
        .order_by(Item.published_at.desc())
        .limit(BATCH_SIZE)
        .with_for_update(of=Item, skip_locked=True)
    )
    return [(item, source) for item, source in (await session.execute(stmt)).all()]


async def _process(session: AsyncSession, item: Item, source: Source, llm_budget: int) -> bool:
    """항목 하나를 관문에 통과시킨다. 돌려주는 값은 LLM 을 실제로 호출했는지 여부."""
    rules = get_rules()

    cluster_id = await find_cluster(session, item.title, exclude_item_id=item.id)
    if cluster_id is not None:
        item.cluster_id = cluster_id
        item.status = ItemStatus.FILTERED_OUT.value
        session.add(_record(item, Stage.RULE, False, {"reason": "dup", "cluster_id": cluster_id}))
        return False

    repo = item.raw.get("repo") if isinstance(item.raw, dict) else None
    verdict = apply_rules(
        rules,
        source=source.name,
        title=item.title,
        body=item.summary_raw,
        url=item.url,
        repo=str(repo) if repo else None,
    )
    session.add(
        _record(
            item,
            Stage.RULE,
            verdict.passed,
            {"reason": verdict.reason, "matched": verdict.matched_keywords},
        )
    )
    if not verdict.passed:
        item.status = ItemStatus.FILTERED_OUT.value
        return False

    mentions = await mention_count(session, item.id)
    metrics = item.raw.get("metrics", {}) if isinstance(item.raw, dict) else {}
    score = score_item(
        rules.scoring,
        trust=source.trust_score,
        keyword_hits=len(verdict.matched_keywords),
        metrics=metrics if isinstance(metrics, dict) else {},
        mention_count=mentions,
        published_at=item.published_at,
    )
    item.score = score.score
    session.add(_record(item, Stage.SCORE, score.passed, {"breakdown": score.breakdown}))
    if not score.passed:
        item.status = ItemStatus.DROPPED.value
        return False

    if llm_budget <= 0:
        log.info("pipeline.llm_cap_reached", item_id=item.id)
        return False  # NEW 로 남겨 다음 실행에서 다시 시도한다.

    body = item.summary_raw
    enrich_failed = False
    if not body or len(body) < llm.ENRICH_MIN_CHARS:
        enriched = await llm.enrich_body(item.url)
        if enriched:
            body = enriched
            item.summary_raw = enriched[:3000]
        else:
            enrich_failed = True

    result = await llm.judge(rules, source=source.name, title=item.title, body=body)
    session.add(
        _record(
            item,
            Stage.LLM,
            result.verdict.worth_notifying,
            {
                "enrich_failed": enrich_failed,
                "importance": result.verdict.importance,
                "tags": result.verdict.tags,
            },
        )
    )
    session.add(
        Summary(
            item_id=item.id,
            title_ko=result.verdict.title_ko,
            summary_ko=result.verdict.summary_ko,
            tags=result.verdict.tags,
            importance=result.verdict.importance,
            worth_notifying=result.verdict.worth_notifying,
            model=result.model,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )
    )
    item.category = result.verdict.category.value
    item.status = (
        ItemStatus.SCORED.value if result.verdict.worth_notifying else ItemStatus.DROPPED.value
    )
    return True


async def run_pipeline() -> int:
    """한 배치를 처리하고 통과(SCORED)한 항목 수를 돌려준다."""
    settings = get_settings()
    passed = 0
    async with session_scope() as session:
        budget = settings.llm_daily_cap - await _llm_calls_today(session)
        for item, source in await _claim_batch(session):
            try:
                used = await _process(session, item, source, budget)
            except Exception as exc:
                log.warning("pipeline.item_failed", item_id=item.id, error=str(exc))
                continue
            if used:
                budget -= 1
            if item.status == ItemStatus.SCORED.value:
                passed += 1
    log.info("pipeline.done", scored=passed)
    return passed
