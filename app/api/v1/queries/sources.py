# 수집 소스 화면 조회 SQL — 이름으로 소스 행, 최근 N시간 수집 건수

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item, Source


async def sources_by_name(session: AsyncSession, names: list[str]) -> dict[str, Source]:
    rows = await session.execute(select(Source).where(Source.name.in_(names)))
    return {s.name: s for s in rows.scalars()}


async def items_collected(session: AsyncSession, window_hours: int) -> int:
    """최근 window_hours 시간에 적재된 항목 수 (롤링 창, 전 소스)."""
    stmt = (
        select(func.count())
        .select_from(Item)
        .where(Item.fetched_at >= func.now() - timedelta(hours=window_hours))
    )
    count: int = (await session.execute(stmt)).scalar_one()
    return count
