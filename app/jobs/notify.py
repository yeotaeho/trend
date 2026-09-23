# 발송 잡 — SCORED/QUEUED 항목에 정책을 적용해 디스코드로 보내고, 끝에 하루 1건 경계 항목을 실험한다

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.config import NotifyConfig, Rules, get_rules
from app.db.budget import reserve_call, today_start
from app.db.models import Decision, Item, Notification, Source, Summary
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.log import get_logger
from app.notify.base import Notifier, RateLimited
from app.notify.discord import DiscordNotifier
from app.notify.policy import decide, in_quiet_hours
from app.pipeline import llm
from app.pipeline.feedback import examples_details, format_examples, nearest_feedback
from app.schemas import ItemStatus, Level, Stage

BATCH_SIZE = 20
PENDING = (ItemStatus.SCORED.value, ItemStatus.QUEUED.value)
EXPLORE_BAND = 0.10  # 임계값 바로 아래 이 폭 안에서 떨어진 항목이 탐색 후보
log = get_logger(__name__)


async def _claim_one(
    session: AsyncSession, skip_ids: set[int]
) -> tuple[Item, Summary, Source] | None:
    """한 건씩 잠근다. 락은 커밋 때 풀리므로 항목 하나가 곧 트랜잭션 하나여야 한다.

    한 번에 20건을 잠그고 루프 안에서 커밋하면 첫 커밋에서 나머지 19건의 락까지
    풀려, 워커를 늘렸을 때 같은 항목이 두 번 발송될 수 있다.
    """
    stmt = (
        select(Item, Summary, Source)
        .join(Summary, Summary.item_id == Item.id)
        .join(Source, Source.id == Item.source_id)
        .where(Item.status.in_(PENDING), Summary.worth_notifying.is_(True))
        .order_by(Summary.importance.desc(), Item.published_at)
        .limit(1)
        .with_for_update(of=Item, skip_locked=True)
    )
    if skip_ids:
        # QUEUED 로 미룬 항목은 여전히 PENDING 이라 그냥 두면 같은 건만 계속 잡는다.
        stmt = stmt.where(Item.id.notin_(skip_ids))
    row = (await session.execute(stmt)).first()
    return (row[0], row[1], row[2]) if row else None


async def run_notify(notifier: Notifier | None = None) -> int:
    """실제로 발송한 건수를 돌려준다."""
    notifier = notifier or DiscordNotifier()
    rules = get_rules()
    cfg = rules.notify
    sent = 0

    async with session_scope() as session:
        visited: set[int] = set()
        for _ in range(BATCH_SIZE):
            claimed = await _claim_one(session, visited)
            if claimed is None:
                break
            item, summary, source = claimed
            visited.add(item.id)
            # 매 항목마다 새로 읽는다. 잡 시작 시각을 재사용하면 자정을 넘길 때 날짜가 어긋난다.
            now = datetime.now(UTC)
            verdict = await decide(session, cfg, importance=summary.importance, now=now)

            if verdict.level is None:
                if verdict.reason == "feed_only":
                    # 발송하지 않고 이력만 남긴다.
                    session.add(
                        Notification(
                            user_id=DEFAULT_USER_ID,
                            item_id=item.id,
                            channel=notifier.channel,
                            level=Level.FEED.value,
                        )
                    )
                    item.status = ItemStatus.SENT.value
                else:
                    item.status = ItemStatus.QUEUED.value
                    log.info("notify.deferred", item_id=item.id, reason=verdict.reason)
                await session.commit()
                continue

            try:
                message_id = await notifier.send(item, summary, verdict.level, source.name)
            except RateLimited as exc:
                # 항목 탓이 아니다. 기록하지 않고 배치를 멈춘다 — 채널이 준 대기 시간이
                # 지나면 다음 발송 잡이 이 항목부터 다시 시도한다.
                log.warning("notify.rate_limited", item_id=item.id, error=str(exc))
                break
            except Exception as exc:
                session.add(
                    Notification(
                        user_id=DEFAULT_USER_ID,
                        item_id=item.id,
                        channel=notifier.channel,
                        level=verdict.level.value,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                item.status = ItemStatus.FAILED.value
                log.warning("notify.failed", item_id=item.id, error=str(exc))
                await session.commit()
                continue

            session.add(
                Notification(
                    user_id=DEFAULT_USER_ID,
                    item_id=item.id,
                    channel=notifier.channel,
                    level=verdict.level.value,
                    message_id=message_id,
                )
            )
            item.status = ItemStatus.SENT.value
            # 발송 직후 커밋한다. 배치를 한 트랜잭션으로 묶으면 뒤쪽 한 건이 실패했을 때
            # 이미 발송이 끝난 앞쪽 항목까지 롤백돼 다음 잡에서 다시 발송된다.
            await session.commit()
            sent += 1

        try:
            await _explore(session, rules, notifier, now=datetime.now(UTC))
        except Exception as exc:
            await session.rollback()
            log.warning("notify.explore_failed", error=str(exc))

    log.info("notify.done", sent=sent)
    return sent


# ---------- 탐색 슬롯 ----------


async def _explore_sent_today(session: AsyncSession, cfg: NotifyConfig, now: datetime) -> bool:
    start = today_start(cfg.timezone, now)
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.level == Level.EXPLORE.value,
            Notification.error.is_(None),
            Notification.sent_at >= start,
        )
    )
    return (await session.execute(stmt)).scalar_one() > 0


async def _explore_candidate(
    session: AsyncSession, rules: Rules, now: datetime
) -> Row[tuple[Item, Source]] | None:
    """점수 관문 바로 아래로 떨어진 최근 24시간 항목 중 최고점. Summary 가 없어야 한다."""
    thr = rules.scoring.threshold
    # 항목의 "마지막" 결정 행 하나를 고른 뒤 그것이 score 탈락인지 본다. 최근 score 행만 보면
    # 그 뒤에 다른 단계 결정이 붙은 항목까지 후보가 된다.
    latest = aliased(Decision)
    last_decision = (
        select(latest.id)
        .where(latest.item_id == Item.id)
        .order_by(latest.created_at.desc(), latest.id.desc())
        .limit(1)
        .correlate(Item)
        .scalar_subquery()
    )
    stmt = (
        select(Item, Source)
        .join(Source, Source.id == Item.source_id)
        .join(Decision, Decision.id == last_decision)
        .outerjoin(Summary, Summary.item_id == Item.id)
        .where(
            Item.status == ItemStatus.DROPPED.value,
            Summary.item_id.is_(None),
            Item.score >= thr - EXPLORE_BAND,
            Item.score < thr,
            Item.published_at >= now - timedelta(hours=24),
            Decision.stage == Stage.SCORE.value,
            Decision.passed.is_(False),
        )
        .order_by(Item.score.desc())
        .limit(1)
        .with_for_update(of=Item, skip_locked=True)
    )
    return (await session.execute(stmt)).first()


async def _explore(
    session: AsyncSession, rules: Rules, notifier: Notifier, *, now: datetime
) -> bool:
    """하루 1건 경계 항목 실험. 판정 → 통과면 🧪 발송 → SENT. false 면 그날은 보내지 않는다.

    일반 발송 흐름을 타지 않는다. 후보는 DROPPED 이고 Summary 가 없어 일반 발송 쿼리에 안 잡힌다.
    이게 없으면 파이프는 자기가 버린 것에 대해 영원히 배우지 못한다. now 는 호출 직전 시각이다.
    """
    cfg = rules.notify
    if in_quiet_hours(cfg, now) or await _explore_sent_today(session, cfg, now):
        return False
    row = await _explore_candidate(session, rules, now)
    if row is None:
        return False
    item, source = row[0], row[1]

    body, enrich_failed = await llm.body_for_judge(item)
    if await reserve_call("explore") is None:
        return False
    examples = await nearest_feedback(session, item.id, k=3)
    result = await llm.judge(
        rules, source=source.name, title=item.title, body=body, examples=format_examples(examples)
    )
    session.add(
        Decision(
            item_id=item.id,
            stage=Stage.LLM.value,
            passed=result.verdict.worth_notifying,
            score=item.score,
            details={
                "explore": True,
                "enrich_failed": enrich_failed,
                "importance": result.verdict.importance,
                "tags": result.verdict.tags,
                "examples": examples_details(examples),
            },
        )
    )
    summary = Summary(
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
    session.add(summary)
    item.category = result.verdict.category.value
    if not result.verdict.worth_notifying:
        # Summary 가 생겼으니 같은 후보를 다시 판정하지 않는다. 오늘 슬롯은 소진되지 않는다.
        await session.commit()
        return False

    message_id = await notifier.send(item, summary, Level.EXPLORE, source.name)
    session.add(
        Notification(
            user_id=DEFAULT_USER_ID,
            item_id=item.id,
            channel=notifier.channel,
            level=Level.EXPLORE.value,
            message_id=message_id,
        )
    )
    item.status = ItemStatus.SENT.value
    await session.commit()
    log.info("notify.explore_sent", item_id=item.id)
    return True
