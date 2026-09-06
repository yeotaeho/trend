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
from app.pipeline.dedupe import Verdict, classify, find_candidates
from app.pipeline.embedding import EmbeddingDimError, alert_dim_error, embed_pending
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


async def _reembedding_in_progress(session: AsyncSession) -> bool:
    """embedding_model 이 현재 설정과 다른 행이 있으면 백필 중이다. 옛 벡터와 섞지 않는다."""
    model = get_settings().embedding_model
    stmt = (
        select(Item.id)
        .where(Item.embedding.is_not(None), Item.embedding_model.is_distinct_from(model))
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None


async def _process(session: AsyncSession, item: Item, source: Source) -> bool:
    """항목 하나를 관문에 통과시킨다. 돌려주는 값은 LLM 을 실제로 호출했는지 여부."""
    rules = get_rules()

    dup, related = await find_candidates(session, item.id, rules.dedupe)
    embedded = await session.scalar(select(Item.embedding.is_not(None)).where(Item.id == item.id))
    if not embedded:
        # 임베딩 실패 항목. 중복·다중소스 판정 없이 진행한다 — 장애가 항목을 죽이면 안 된다.
        session.add(_record(item, Stage.RULE, True, {"reason": "dedupe_skipped"}))
        verdict = Verdict("independent", item.id, 1)
    else:
        verdict = classify(
            item_id=item.id,
            own_source_id=item.source_id,
            own_title=item.title,
            dup=dup,
            related=related,
            cfg=rules.dedupe,
        )
    item.cluster_id = verdict.cluster_id
    if verdict.kind == "dup":
        item.status = ItemStatus.FILTERED_OUT.value
        session.add(
            _record(item, Stage.RULE, False, {"reason": "dup", "cluster_id": verdict.cluster_id})
        )
        return False

    repo = item.raw.get("repo") if isinstance(item.raw, dict) else None
    rule = apply_rules(
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
            rule.passed,
            {"reason": rule.reason, "matched": rule.matched_keywords},
        )
    )
    if not rule.passed:
        item.status = ItemStatus.FILTERED_OUT.value
        return False

    if rule.reason == "always_pass_source":
        # 화이트리스트 소스는 점수 관문을 건너뛴다. 제목에 키워드가 없는 채널(YouTube)은
        # kw=0 이라 어떤 신뢰도로도 임계값을 못 넘는데, 화이트리스트의 뜻은 "이 소스는
        # 봐라"다. 거르는 일은 LLM 의 worth_notifying 이 맡는다. (include_repo 는 키워드성
        # 신호라 그대로 점수화한다.)
        # 단, 신선도는 본다. 첫 실행 백필(GitHub 200건·YouTube 30건)이 전부 LLM 으로 가면
        # 하루 예산 300 을 오래된 항목에 쓰고 첫날 알림이 옛 릴리즈로 넘친다.
        age = datetime.now(UTC) - item.published_at
        if age > timedelta(hours=rules.scoring.whitelist_max_age_hours):
            item.status = ItemStatus.DROPPED.value
            session.add(
                _record(
                    item,
                    Stage.SCORE,
                    False,
                    {"reason": "whitelist_stale", "age_hours": round(age.total_seconds() / 3600)},
                )
            )
            return False
        session.add(_record(item, Stage.SCORE, True, {"reason": "whitelist_bypass"}))
    else:
        metrics = item.raw.get("metrics", {}) if isinstance(item.raw, dict) else {}
        score = score_item(
            rules.scoring,
            trust=source.trust_score,
            keyword_hits=len(rule.matched_keywords),
            metrics=metrics if isinstance(metrics, dict) else {},
            mention_count=verdict.mention_count,
            published_at=item.published_at,
        )
        item.score = score.score
        session.add(_record(item, Stage.SCORE, score.passed, {"breakdown": score.breakdown}))
        if not score.passed:
            item.status = ItemStatus.DROPPED.value
            return False

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
        if budget <= 0:
            log.info("pipeline.llm_cap_reached", cap=settings.llm_daily_cap)
            return 0
        if await _reembedding_in_progress(session):
            log.info("pipeline.paused_for_reembedding")
            return 0

        batch = await _claim_batch(session)
        # 수집 때 실패한 임베딩을 다시 시도한다. 여기서도 실패하면 dedupe_skipped 로 진행한다.
        try:
            await embed_pending(session, [item.id for item, _ in batch])
        except EmbeddingDimError as exc:
            # 설정 오류. 잡을 세우고 알린다. 조용히 NULL 로 두면 중복 판정이 영구히 빠진다.
            await alert_dim_error(exc)
            raise

        for item, source in batch:
            # 예산이 바닥나면 손대지 않고 멈춘다. 판정을 기록해 두고 NEW 로 남기면
            # 다음 실행마다 같은 항목을 다시 판정해 decisions 가 계속 쌓인다.
            if budget <= 0:
                break

            # 항목 하나를 savepoint 로 감싼다. LLM 이 죽어 있으면 rule·score 판정만
            # 기록된 채 NEW 로 남고, 2분마다 같은 판정이 decisions 에 다시 쌓인다.
            # 롤백은 savepoint 안에서 수정된 객체를 만료시키므로, 롤백 뒤에 item 의
            # 속성을 읽으면 동기 로드가 일어나 MissingGreenlet 이 난다. id 는 미리 뺀다.
            item_id = item.id
            savepoint = await session.begin_nested()
            try:
                used = await _process(session, item, source)
            except Exception as exc:
                await savepoint.rollback()
                log.warning("pipeline.item_failed", item_id=item_id, error=str(exc))
                continue
            await savepoint.commit()

            if used:
                budget -= 1
            if item.status == ItemStatus.SCORED.value:
                passed += 1
    log.info("pipeline.done", scored=passed)
    return passed
