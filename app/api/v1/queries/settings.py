# 설정 화면 조회 SQL — 활성 FCM 기기 수

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device


async def active_device_count(session: AsyncSession, user_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Device)
        .where(Device.user_id == user_id, Device.disabled_at.is_(None))
    )
    count: int = (await session.execute(stmt)).scalar_one()
    return count
