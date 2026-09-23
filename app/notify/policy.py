# 발송 정책 — 알림 강도·하루 push 상한·무음 시간·클러스터 하루 상한을 이 파일 한 곳에서 결정

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute, aliased

from app.config import Delivery, NotifyConfig
from app.db.budget import today_start
from app.db.models import Item, Notification
from app.pipeline.dedupe import version_tokens
from app.schemas import Level

DELIVERY_LEVEL: dict[Delivery, Level] = {
    "instant": Level.PUSH,
    "quiet": Level.SILENT,
    "feed_only": Level.FEED,
}
# 클러스터 하루 상한이 세는 "나간" 강도. cluster_dup·feed 는 발송이 아니다.
SENT_LEVELS = (Level.PUSH.value, Level.SILENT.value, Level.EXPLORE.value)


@dataclass(slots=True)
class Verdict:
    level: Level  # FEED·CLUSTER_DUP 이면 어느 채널로도 보내지 않고 기록만 남긴다
    reason: str


def delivery_for(cfg: NotifyConfig, importance: int) -> Delivery:
    """importance 구간 high 5·4, mid 3, low 2·1."""
    by = cfg.delivery_by_importance
    if importance >= 4:
        return by.high
    if importance == 3:
        return by.mid
    return by.low


def in_quiet_hours(cfg: NotifyConfig, now: datetime) -> bool:
    """무음 시간은 자정을 넘길 수 있다 (예: 23시~8시)."""
    hour = now.astimezone(ZoneInfo(cfg.timezone)).hour
    if cfg.quiet_start_hour == cfg.quiet_end_hour:
        return False
    if cfg.quiet_start_hour < cfg.quiet_end_hour:
        return cfg.quiet_start_hour <= hour < cfg.quiet_end_hour
    return hour >= cfg.quiet_start_hour or hour < cfg.quiet_end_hour


async def push_count_today(session: AsyncSession, cfg: NotifyConfig, now: datetime) -> int:
    """오늘 push 로 나간 서로 다른 항목 수. 채널이 여럿이어도 항목 하나는 1건이다."""
    stmt = select(func.count(Notification.item_id.distinct())).where(
        Notification.level == Level.PUSH.value,
        Notification.error.is_(None),
        Notification.sent_at >= today_start(cfg.timezone, now),
    )
    return (await session.execute(stmt)).scalar_one()


def cluster_sent_count(
    cfg: NotifyConfig, cluster_id: int | QueryableAttribute[int | None], user_id: int, now: datetime
) -> Select[tuple[int]]:
    """오늘(달력일) 같은 클러스터에서 push·silent·explore 로 나간 서로 다른 항목 수.

    cluster_id 에 바깥 쿼리의 열을 넘기면 상관 서브쿼리로 쓸 수 있다 (탐색 후보).
    """
    sent = aliased(Item)
    return (
        select(func.count(Notification.item_id.distinct()))
        .join(sent, sent.id == Notification.item_id)
        .where(
            sent.cluster_id == cluster_id,
            Notification.user_id == user_id,
            Notification.level.in_(SENT_LEVELS),
            Notification.error.is_(None),
            Notification.sent_at >= today_start(cfg.timezone, now),
        )
    )


async def cluster_sent_today(
    session: AsyncSession, cfg: NotifyConfig, cluster_id: int, user_id: int, now: datetime
) -> int:
    return (await session.execute(cluster_sent_count(cfg, cluster_id, user_id, now))).scalar_one()


def sibling_versions(own_title: str, sibling_titles: list[str]) -> list[str]:
    """자기 제목부터 형제 제목 순으로 버전 토큰을 모은다. 중복은 처음 나온 자리만 남긴다."""
    seen: list[str] = []
    for title in [own_title, *sibling_titles]:
        for token in sorted(version_tokens(title)):
            if token not in seen:
                seen.append(token)
    return seen


def decorate_title(title_ko: str, versions: list[str]) -> str:
    """버전이 2개 이상이면 제목 끝에 `(v2.2.0 · v1.30.0)` 을 붙인다."""
    if len(versions) < 2:
        return title_ko
    return f"{title_ko} ({' · '.join(versions)})"


async def decide(
    session: AsyncSession,
    cfg: NotifyConfig,
    *,
    importance: int,
    cluster_id: int | None,
    user_id: int,
    now: datetime,
) -> Verdict:
    """강도 결정 → 무음 시간 → push 상한 강등 → 클러스터 상한 순서로 본다.

    무음 시간 중엔 보내지 않고 피드에만 남긴다. 피드 전용이 된 항목은 클러스터 검사를 거치지 않는다.
    """
    level = DELIVERY_LEVEL[delivery_for(cfg, importance)]
    if level is Level.FEED:
        return Verdict(Level.FEED, "feed_only")
    if in_quiet_hours(cfg, now):
        return Verdict(Level.FEED, "quiet_hours")
    reason = "ok"
    if level is Level.PUSH and await push_count_today(session, cfg, now) >= cfg.daily_push_cap:
        level, reason = Level.SILENT, "daily_cap"
    if (
        cfg.cluster_daily_cap > 0
        and cluster_id is not None
        and await cluster_sent_today(session, cfg, cluster_id, user_id, now)
        >= cfg.cluster_daily_cap
    ):
        return Verdict(Level.CLUSTER_DUP, "cluster_dup")
    return Verdict(level, reason)
