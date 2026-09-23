# 발송 잡 — SCORED 항목에 정책을 적용해 켜진 채널 전부로 보내고, 끝에 하루 1건 경계 항목을 실험한다

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.config import NotifyConfig, Rules, get_rules, get_settings
from app.db.budget import reserve_call, today_start
from app.db.models import Decision, Item, Notification, Source, Summary
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.log import get_logger
from app.notify.base import APP_CHANNEL, Notifier, RateLimited, channel_connected
from app.notify.discord import DiscordNotifier
from app.notify.fcm import FcmNotifier
from app.notify.policy import (
    cluster_sent_count,
    decide,
    decorate_title,
    in_quiet_hours,
    sibling_versions,
)
from app.notify.telegram import TelegramNotifier
from app.pipeline import llm
from app.pipeline.feedback import examples_details, format_examples, nearest_feedback
from app.schemas import ItemStatus, Level, Stage

BATCH_SIZE = 20
# QUEUED 는 무음 시간 항목을 아침까지 미루던 때의 상태다. 이제 만들지 않지만 남은 행은 마저 보낸다.
PENDING = (ItemStatus.SCORED.value, ItemStatus.QUEUED.value)
# 제목 병기에 쓰는 형제 항목 상태. 탈락·실패 항목의 버전은 붙이지 않는다.
SIBLING_STATUSES = (ItemStatus.SCORED.value, ItemStatus.QUEUED.value, ItemStatus.SENT.value)
EXPLORE_BAND = 0.10  # 임계값 바로 아래 이 폭 안에서 떨어진 항목이 탐색 후보
RATE_LIMITED = "rate_limited"
log = get_logger(__name__)


def enabled_notifiers(rules: Rules) -> list[Notifier]:
    """켜져 있고 연결 정보(.env)가 있는 채널. 비어 있으면 모든 항목이 피드 전용이 된다."""
    on = rules.notify.channels
    connected = channel_connected(get_settings())
    notifiers: list[Notifier] = []
    if on.fcm and connected["fcm"]:
        notifiers.append(FcmNotifier())
    if on.discord and connected["discord"]:
        notifiers.append(DiscordNotifier())
    if on.telegram and connected["telegram"]:
        notifiers.append(TelegramNotifier())
    return notifiers


async def _claim_one(session: AsyncSession) -> tuple[Item, Summary, Source] | None:
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
    row = (await session.execute(stmt)).first()
    return (row[0], row[1], row[2]) if row else None


async def _send_title(
    session: AsyncSession, rules: Rules, item: Item, summary: Summary, now: datetime
) -> str:
    """같은 클러스터 형제 항목(중복 판정 창 안) 제목의 버전을 병기한 발송 제목."""
    if item.cluster_id is None:
        return summary.title_ko
    stmt = (
        select(Item.title)
        .where(
            Item.cluster_id == item.cluster_id,
            Item.id != item.id,
            Item.status.in_(SIBLING_STATUSES),
            Item.published_at >= now - timedelta(hours=rules.dedupe.window_hours),
        )
        .order_by(Item.published_at.desc(), Item.id.desc())
    )
    titles = list((await session.execute(stmt)).scalars())
    if not titles:
        # 형제가 없으면 제목 그대로다. 자기 제목의 버전만으로는 병기하지 않는다.
        return summary.title_ko
    return decorate_title(summary.title_ko, sibling_versions(item.title, titles))


async def deliver(
    session: AsyncSession,
    notifiers: list[Notifier],
    item: Item,
    summary: Summary,
    level: Level,
    source_name: str,
    *,
    title: str,
) -> bool | None:
    """켜진 채널 전부로 보내고 채널마다 notifications 행을 남긴다. 커밋은 호출자가 한다.

    한 채널이라도 성공하면 SENT, 전부 실패하면 FAILED 로 두고 성공 여부를 돌려준다.
    아직 어느 채널도 성공하지 않았는데 RateLimited 면 기록 없이 None 을 돌려준다 — 배치를
    멈추라는 뜻이고, 대기가 지나면 다음 잡이 이 항목부터 다시 시도한다. 이미 다른 채널로
    나갔으면 되돌릴 수 없으므로 그 채널 행에 error='rate_limited' 만 남긴다.
    """
    rows: list[Notification] = []
    for notifier in notifiers:
        row = Notification(
            user_id=DEFAULT_USER_ID,
            item_id=item.id,
            channel=notifier.channel,
            level=level.value,
            title=title,
        )
        try:
            row.message_id = await notifier.send(item, summary, level, source_name, title=title)
        except RateLimited as exc:
            if all(r.error is not None for r in rows):
                log.warning("notify.rate_limited", item_id=item.id, error=str(exc))
                return None
            row.error = RATE_LIMITED
        except Exception as exc:
            row.error = f"{type(exc).__name__}: {exc}"
            log.warning("notify.failed", item_id=item.id, channel=notifier.channel, error=str(exc))
        rows.append(row)

    session.add_all(rows)
    delivered = any(r.error is None for r in rows)
    item.status = ItemStatus.SENT.value if delivered else ItemStatus.FAILED.value
    return delivered


async def run_notify(notifiers: list[Notifier] | None = None) -> int:
    """실제로 발송한 건수를 돌려준다. notifiers 를 생략하면 켜지고 연결된 채널 전부다."""
    rules = get_rules()
    cfg = rules.notify
    if notifiers is None:
        notifiers = enabled_notifiers(rules)
    sent = 0
    rate_limited = False

    async with session_scope() as session:
        for _ in range(BATCH_SIZE):
            claimed = await _claim_one(session)
            if claimed is None:
                break
            item, summary, source = claimed
            # 매 항목마다 새로 읽는다. 잡 시작 시각을 재사용하면 자정을 넘길 때 날짜가 어긋난다.
            now = datetime.now(UTC)
            verdict = await decide(
                session,
                cfg,
                importance=summary.importance,
                cluster_id=item.cluster_id,
                user_id=DEFAULT_USER_ID,
                now=now,
            )
            # 켜진 채널이 없으면 보낼 곳이 없으니 피드에만 남긴다. 클러스터 억제는 그대로 둔다.
            keep = notifiers or verdict.level is Level.CLUSTER_DUP
            level = verdict.level if keep else Level.FEED
            if level in (Level.FEED, Level.CLUSTER_DUP):
                # 발송하지 않고 이력만 남긴다. 피드·걸러진 항목 화면이 이 행을 읽는다.
                session.add(
                    Notification(
                        user_id=DEFAULT_USER_ID,
                        item_id=item.id,
                        channel=APP_CHANNEL,
                        level=level.value,
                    )
                )
                item.status = ItemStatus.SENT.value
                log.info(
                    "notify.not_sent", item_id=item.id, level=level.value, reason=verdict.reason
                )
                await session.commit()
                continue

            title = await _send_title(session, rules, item, summary, now)
            delivered = await deliver(
                session, notifiers, item, summary, level, source.name, title=title
            )
            if delivered is None:
                rate_limited = True
                break
            # 항목마다 커밋한다. 배치를 한 트랜잭션으로 묶으면 뒤쪽 한 건이 실패했을 때
            # 이미 발송이 끝난 앞쪽 항목까지 롤백돼 다음 잡에서 다시 발송된다.
            await session.commit()
            if delivered:
                sent += 1

        try:
            # 채널이 대기 중이면 탐색 판정(예산 3회/일)을 태우지 않는다. 발송에서 되돌려진다.
            if not rate_limited:
                await _explore(session, rules, notifiers, now=datetime.now(UTC))
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
    """점수 관문 바로 아래로 떨어진 최근 24시간 항목 중 최고점. Summary 가 없어야 한다.

    클러스터 하루 상한이 켜져 있으면 오늘 이미 나간 클러스터의 항목은 후보가 아니다.
    """
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
    if rules.notify.cluster_daily_cap > 0:
        sent = cluster_sent_count(rules.notify, Item.cluster_id, DEFAULT_USER_ID, now)
        stmt = stmt.where(sent.scalar_subquery() == 0)
    return (await session.execute(stmt)).first()


async def _explore(
    session: AsyncSession, rules: Rules, notifiers: list[Notifier], *, now: datetime
) -> bool:
    """하루 1건 경계 항목 실험. 판정 → 통과면 🧪 발송 → SENT. false 면 그날은 보내지 않는다.

    일반 발송 흐름을 타지 않는다. 후보는 DROPPED 이고 Summary 가 없어 일반 발송 쿼리에 안 잡힌다.
    이게 없으면 파이프는 자기가 버린 것에 대해 영원히 배우지 못한다. now 는 호출 직전 시각이다.
    토글이 꺼졌거나 켜진 채널이 없으면 판정(LLM 예약)도 하지 않는다.
    """
    cfg = rules.notify
    if not cfg.explore_enabled or not notifiers:
        return False
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

    title = await _send_title(session, rules, item, summary, now)
    delivered = await deliver(
        session, notifiers, item, summary, Level.EXPLORE, source.name, title=title
    )
    if delivered is None:
        # 판정까지 되돌린다. 후보로 남아 대기가 풀린 뒤 다음 잡이 다시 시도한다.
        await session.rollback()
        return False
    await session.commit()
    log.info("notify.explore_done", item_id=item.id, delivered=delivered)
    return delivered
