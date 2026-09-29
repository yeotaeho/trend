# 피드 조회 — 전달된 항목 카드 목록(필터·커서)과 오늘 요약 줄 집계

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import ApiError
from app.api.v1.pagination import PageParams, paginate
from app.api.v1.queries.alerts import INT4_MAX, alert_select, build_alerts, first_delivery
from app.api.v1.queries.filtered import WINDOW_HOURS, filtered_total
from app.api.v1.schemas.alerts import Alert
from app.api.v1.schemas.feed import FeedFilter, TodayStats
from app.config import NotifyConfig
from app.db.budget import today_start
from app.db.models import Feedback, Item, Notification
from app.schemas import Level

FILTER_LEVEL = {
    FeedFilter.INSTANT: Level.PUSH.value,
    FeedFilter.QUIET: Level.SILENT.value,
    FeedFilter.EXPERIMENT: Level.EXPLORE.value,
}


def _after(key: dict[str, Any]) -> tuple[datetime, int]:
    """피드 커서 = 직전 페이지 마지막 카드의 (delivered_at, id)."""
    try:
        sent_at, item_id = datetime.fromisoformat(key["t"]), int(key["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.") from exc
    if not 0 < item_id <= INT4_MAX:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.")
    return sent_at, item_id


async def feed_page(
    session: AsyncSession, user_id: int, flt: FeedFilter, page: PageParams
) -> tuple[list[Alert], str | None]:
    """delivered_at 내림차순, 같으면 id 내림차순. 기간 제한 없이 커서로 내려간다."""
    delivery = first_delivery(user_id)
    stmt = alert_select(user_id, delivery, delivered_only=True)
    if flt in FILTER_LEVEL:
        stmt = stmt.where(delivery.c.level == FILTER_LEVEL[flt])
    elif flt is FeedFilter.USEFUL:
        stmt = stmt.where(Feedback.verdict == "useful")
    if page.after is not None:
        sent_at, item_id = _after(page.after)
        stmt = stmt.where(
            tuple_(delivery.c.sent_at, Item.id) < tuple_(literal(sent_at), literal(item_id))
        )
    stmt = stmt.order_by(delivery.c.sent_at.desc(), Item.id.desc()).limit(page.limit + 1)
    rows, next_cursor = paginate(
        (await session.execute(stmt)).all(),
        page.limit,
        lambda r: {"t": r.sent_at.isoformat(), "id": r.id},
    )
    return await build_alerts(session, rows), next_cursor


async def today_stats(
    session: AsyncSession, user_id: int, cfg: NotifyConfig, now: datetime
) -> TodayStats:
    start = today_start(cfg.timezone, now)
    since = now - timedelta(hours=WINDOW_HOURS)
    # 채널이 여럿이어도 한 항목은 한 번만 센다.
    push_sent = await session.scalar(
        select(func.count(func.distinct(Notification.item_id))).where(
            Notification.user_id == user_id,
            Notification.level == Level.PUSH.value,
            Notification.error.is_(None),
            Notification.sent_at >= start,
        )
    )
    collected = await session.scalar(
        select(func.count()).select_from(Item).where(Item.fetched_at >= since)
    )
    return TodayStats(
        date=start.date().isoformat(),
        timezone=cfg.timezone,
        push_sent_today=push_sent or 0,
        daily_push_cap=cfg.daily_push_cap,
        window_hours=WINDOW_HOURS,
        collected_count=collected or 0,
        filtered_count=await filtered_total(session, user_id, since),
    )
