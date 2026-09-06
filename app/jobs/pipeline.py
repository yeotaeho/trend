# 파이프라인 잡 — NEW 배치를 1국면(항목 관문) → 2국면(선별 배치) → 3국면(점수·판정) 으로 통과시킨다

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Rules, get_rules, get_settings
from app.db.budget import reserve_call
from app.db.models import Decision, Item, Source, Summary
from app.db.session import session_scope
from app.log import get_logger
from app.notify.discord import send_ops_alert
from app.pipeline import llm
from app.pipeline.dedupe import Verdict, classify, find_candidates
from app.pipeline.embedding import EmbeddingDimError, alert_dim_error, embed_pending
from app.pipeline.feedback import format_examples, nearest_feedback
from app.pipeline.rules import apply_rules
from app.pipeline.scoring import is_stale, score_item
from app.pipeline.triage import (
    TriageBatchError,
    TriageEntry,
    TriageItem,
    call_triage,
    parse_triage,
)
from app.schemas import ItemStatus, Stage

BATCH_SIZE = 50
SNIPPET_CHARS = 300
TRIAGE_ERROR_LIMIT = 2  # 같은 항목의 항목 실패가 이만큼 쌓이면 폐기
INFRA_FAIL_LIMIT = 2  # 한 잡에서 기반·배치 실패가 연속 이만큼이면 운영 알림 후 종료
log = get_logger(__name__)


def _record(item: Item, stage: Stage, passed: bool, details: dict[str, object]) -> Decision:
    return Decision(
        item_id=item.id, stage=stage.value, passed=passed, score=item.score, details=details
    )


async def _claim_batch(session: AsyncSession) -> list[tuple[Item, Source]]:
    """최신순으로 집어 잠근다. 잠금은 세 국면과 외부 호출 동안 유지된다 (단일 프로세스 전제)."""
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


# ---------- 1국면 ----------


async def _gate(session: AsyncSession, rules: Rules, item: Item, source: Source) -> Verdict | None:
    """stale → 중복 → exclude. 살아남으면 중복 판정 결과를, 탈락하면 None 을 돌려준다."""
    if is_stale(item.published_at, rules.scoring.max_age_hours):
        item.status = ItemStatus.DROPPED.value
        age = (datetime.now(UTC) - item.published_at).total_seconds() / 3600
        session.add(_record(item, Stage.SCORE, False, {"reason": "stale", "age_hours": round(age)}))
        return None

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
        return None

    rule = apply_rules(rules, title=item.title, body=item.summary_raw, url=item.url)
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
        return None
    return verdict


# ---------- 2국면 ----------


async def _existing_relevance(session: AsyncSession, item_ids: list[int]) -> dict[int, TriageItem]:
    """판정 예산이 바닥나 NEW 로 남았던 항목은 이미 선별 결과가 있다. 다시 호출하지 않는다."""
    if not item_ids:
        return {}
    stmt = (
        select(Decision.item_id, Decision.details)
        .where(
            Decision.item_id.in_(item_ids),
            Decision.stage == Stage.TRIAGE.value,
            Decision.passed.is_(True),
        )
        .order_by(Decision.created_at.desc())
    )
    found: dict[int, TriageItem] = {}
    for item_id, details in (await session.execute(stmt)).all():
        if item_id not in found and "relevance" in details:
            found[item_id] = TriageItem(
                idx=item_id, relevance=float(details["relevance"]), reason=str(details["reason"])
            )
    return found


async def _triage_error_count(session: AsyncSession, item_id: int) -> int:
    stmt = select(Decision).where(
        Decision.item_id == item_id,
        Decision.stage == Stage.TRIAGE.value,
        Decision.passed.is_(False),
    )
    return len((await session.execute(stmt)).scalars().all())


class _CapReached(Exception):
    """선별 예산 소진. 배치 루프를 끝내는 신호."""


async def _triage_once(
    rules: Rules, entries: list[TriageEntry], expected: list[int]
) -> tuple[dict[int, TriageItem], list[int], str]:
    """예약 → 호출 → 파싱 한 번. 재시도도 이 함수를 다시 부르므로 호출마다 예약 행이 남는다."""
    batch_id = await reserve_call("triage")
    if batch_id is None:
        raise _CapReached
    batch = await call_triage(rules, entries)
    ok, failed = parse_triage(batch, expected)
    return ok, failed, batch_id


async def _triage(
    session: AsyncSession, rules: Rules, survivors: list[tuple[Item, Source]]
) -> dict[int, TriageItem]:
    """배치별 선별. 돌려주는 값은 item_id → 결과. 없는 항목은 NEW 로 남는다."""
    results = await _existing_relevance(session, [item.id for item, _ in survivors])
    pending = [(i, s) for i, s in survivors if i.id not in results]
    infra_failures = 0
    size = rules.triage.batch_size

    for start in range(0, len(pending), size):
        chunk = pending[start : start + size]
        entries = []
        for item, source in chunk:
            examples = await nearest_feedback(session, item.id, k=2)
            entries.append(
                TriageEntry(
                    item.id,
                    source.name,
                    item.title,
                    (item.summary_raw or "")[:SNIPPET_CHARS],
                    format_examples(examples),
                )
            )
        expected = [item.id for item, _ in chunk]
        try:
            try:
                ok, failed, batch_id = await _triage_once(rules, entries, expected)
            except TriageBatchError as exc:
                log.warning("pipeline.triage_batch_retry", error=str(exc))
                ok, failed, batch_id = await _triage_once(rules, entries, expected)
        except _CapReached:
            log.info("pipeline.triage_cap_reached")
            break
        except Exception as exc:
            # 기반 실패든 두 번째 배치 실패든 항목 탓이 아니다. 결정 행 없이 NEW 로 둔다.
            infra_failures += 1
            log.warning("pipeline.triage_failed", error=str(exc), consecutive=infra_failures)
            if infra_failures >= INFRA_FAIL_LIMIT:
                try:
                    await send_ops_alert(f"선별 호출이 연속 {infra_failures}배치 실패: {exc}")
                except Exception as alert_exc:
                    log.warning("pipeline.alert_failed", error=str(alert_exc))
                break
            continue
        infra_failures = 0

        for item, _ in chunk:
            if item.id in ok:
                res = ok[item.id]
                results[item.id] = res
                session.add(
                    _record(
                        item,
                        Stage.TRIAGE,
                        True,
                        {"relevance": res.relevance, "reason": res.reason, "batch_id": batch_id},
                    )
                )
            else:
                # 세기 전에 add 하면 autoflush 로 방금 행까지 세어져 첫 실패에 폐기된다. 먼저 센다.
                prior = await _triage_error_count(session, item.id)
                session.add(_record(item, Stage.TRIAGE, False, {"reason": "triage_error"}))
                if prior + 1 >= TRIAGE_ERROR_LIMIT:
                    item.status = ItemStatus.DROPPED.value
        await session.flush()
    return results


# ---------- 3국면 ----------


async def _judge(
    session: AsyncSession,
    rules: Rules,
    item: Item,
    source: Source,
    verdict: Verdict,
    tri: TriageItem,
) -> bool:
    """점수 → 보강 → 판정. 돌려주는 값은 판정 호출 여부. 예산이 없으면 False, 항목은 NEW 유지."""
    trust = source.trust_adjusted if source.trust_adjusted is not None else source.trust_score
    metrics = item.raw.get("metrics", {}) if isinstance(item.raw, dict) else {}
    score = score_item(
        rules.scoring,
        trust=trust,
        relevance=tri.relevance,
        metrics=metrics if isinstance(metrics, dict) else {},
        mention_count=verdict.mention_count,
        published_at=item.published_at,
    )
    item.score = score.score
    session.add(
        _record(
            item,
            Stage.SCORE,
            score.passed,
            {"breakdown": score.breakdown, "triage_reason": tri.reason},
        )
    )
    if not score.passed:
        item.status = ItemStatus.DROPPED.value
        return False

    body, enrich_failed = await llm.body_for_judge(item)

    if await reserve_call("judge") is None:
        log.info("pipeline.judge_cap_reached", item_id=item.id)
        return False

    examples = format_examples(await nearest_feedback(session, item.id, k=3))
    result = await llm.judge(
        rules, source=source.name, title=item.title, body=body, examples=examples
    )
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


# ---------- 잡 ----------


async def run_pipeline() -> int:
    """한 배치를 처리하고 SCORED 수를 돌려준다."""
    rules = get_rules()
    passed = 0
    async with session_scope() as session:
        if await _reembedding_in_progress(session):
            log.info("pipeline.paused_for_reembedding")
            return 0
        batch = await _claim_batch(session)
        if not batch:
            return 0
        try:
            await embed_pending(session, [item.id for item, _ in batch])
        except EmbeddingDimError as exc:
            await alert_dim_error(exc)
            raise

        survivors: list[tuple[Item, Source, Verdict]] = []
        for item, source in batch:
            item_id = item.id
            savepoint = await session.begin_nested()
            try:
                verdict = await _gate(session, rules, item, source)
            except Exception as exc:
                await savepoint.rollback()
                log.warning("pipeline.gate_failed", item_id=item_id, error=str(exc))
                continue
            await savepoint.commit()
            if verdict is not None:
                survivors.append((item, source, verdict))

        triaged = await _triage(session, rules, [(i, s) for i, s, _ in survivors])

        for item, source, verdict in survivors:
            tri = triaged.get(item.id)
            if tri is None or item.status != ItemStatus.NEW.value:
                continue
            item_id = item.id
            savepoint = await session.begin_nested()
            try:
                await _judge(session, rules, item, source, verdict, tri)
            except Exception as exc:
                await savepoint.rollback()
                log.warning("pipeline.judge_failed", item_id=item_id, error=str(exc))
                continue
            await savepoint.commit()
            if item.status == ItemStatus.SCORED.value:
                passed += 1

    log.info("pipeline.done", scored=passed)
    return passed
