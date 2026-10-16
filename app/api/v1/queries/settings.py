# 설정 화면 조회 SQL — 활성 FCM 기기 수, 설정 저장 이력(커서 목록·한 건·최신 id)

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import ApiError
from app.api.v1.pagination import PageParams, paginate
from app.api.v1.queries.alerts import INT4_MAX
from app.db.models import Device, SettingsRevision


async def active_device_count(session: AsyncSession, user_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Device)
        .where(Device.user_id == user_id, Device.disabled_at.is_(None))
    )
    count: int = (await session.execute(stmt)).scalar_one()
    return count


def _after_id(key: dict[str, Any]) -> int:
    """목록 커서 = 직전 페이지 마지막 행의 id. bool 은 int 의 하위형이라 따로 막는다."""
    rid = key.get("id")
    if type(rid) is not int or not 0 < rid <= INT4_MAX:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.")
    return rid


async def revision_page(
    session: AsyncSession, user_id: int, page: PageParams
) -> tuple[list[SettingsRevision], str | None]:
    """최신 저장부터."""
    stmt = select(SettingsRevision).where(SettingsRevision.user_id == user_id)
    if page.after is not None:
        stmt = stmt.where(SettingsRevision.id < _after_id(page.after))
    stmt = stmt.order_by(SettingsRevision.id.desc()).limit(page.limit + 1)
    rows = (await session.execute(stmt)).scalars().all()
    return paginate(rows, page.limit, lambda r: {"id": r.id})


async def find_revision(
    session: AsyncSession, user_id: int, revision_id: int
) -> SettingsRevision | None:
    """다른 사용자의 이력도 없는 이력과 같다."""
    stmt = select(SettingsRevision).where(
        SettingsRevision.id == revision_id, SettingsRevision.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()
