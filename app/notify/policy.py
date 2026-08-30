# 발송 정책 — 알림 강도·하루 push 상한·무음 시간을 이 파일 한 곳에서 결정

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import NotifyConfig
from app.db.models import Notification
from app.schemas import Level


@dataclass(slots=True)
class Verdict:
    level: Level | None  # None 이면 지금 보내지 않고 QUEUED 로 대기
    reason: str


def level_for(importance: int) -> Level:
    if importance >= 4:
        return Level.PUSH
    if importance == 3:
        return Level.SILENT
    return Level.FEED


def in_quiet_hours(cfg: NotifyConfig, now: datetime) -> bool:
    """무음 시간은 자정을 넘길 수 있다 (예: 23시~8시)."""
    hour = now.astimezone(ZoneInfo(cfg.timezone)).hour
    if cfg.quiet_start_hour == cfg.quiet_end_hour:
        return False
    if cfg.quiet_start_hour < cfg.quiet_end_hour:
        return cfg.quiet_start_hour <= hour < cfg.quiet_end_hour
    return hour >= cfg.quiet_start_hour or hour < cfg.quiet_end_hour


async def push_count_today(session: AsyncSession, cfg: NotifyConfig, now: datetime) -> int:
    tz = ZoneInfo(cfg.timezone)
    start = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.level == Level.PUSH.value,
            Notification.error.is_(None),
            Notification.sent_at >= start,
        )
    )
    return (await session.execute(stmt)).scalar_one()


async def decide(
    session: AsyncSession, cfg: NotifyConfig, *, importance: int, now: datetime
) -> Verdict:
    """importance → 강도. 무음 시간의 push 는 아침으로 미루고, 상한 초과는 silent 로 낮춘다."""
    level = level_for(importance)
    if level is Level.FEED:
        return Verdict(None, "feed_only")
    if level is Level.PUSH:
        if in_quiet_hours(cfg, now):
            return Verdict(None, "quiet_hours")
        if await push_count_today(session, cfg, now) >= cfg.daily_push_cap:
            return Verdict(Level.SILENT, "daily_cap")
    return Verdict(level, "ok")
