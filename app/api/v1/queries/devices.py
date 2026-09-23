# 기기 등록 SQL — 토큰 기준 upsert(다시 활성·사용자 이동), 현재 사용자 기기 삭제

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Boolean, delete, func, literal_column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device


class Registered(NamedTuple):
    id: int
    platform: str
    created_at: datetime
    created: bool


async def register_device(
    session: AsyncSession, user_id: int, token: str, platform: str, app_version: str | None
) -> Registered:
    """새 토큰이면 넣고, 있으면 last_seen_at 갱신·다시 활성·user_id 이동. created 로 구분한다."""
    new = insert(Device).values(
        user_id=user_id, token=token, platform=platform, app_version=app_version
    )
    upsert = new.on_conflict_do_update(
        index_elements=[Device.token],
        set_={
            "user_id": new.excluded.user_id,
            "platform": new.excluded.platform,
            "app_version": new.excluded.app_version,
            "last_seen_at": func.now(),
            "disabled_at": None,
            "last_error": None,
        },
    ).returning(
        Device.id,
        Device.platform,
        Device.created_at,
        # 방금 넣은 행은 xmax 가 0 이다. 충돌로 갱신한 행은 아니다.
        literal_column("xmax = 0", Boolean).label("created"),
    )
    row = (await session.execute(upsert)).one()
    return Registered(row.id, row.platform, row.created_at, bool(row.created))


async def delete_device(session: AsyncSession, user_id: int, token: str) -> None:
    await session.execute(delete(Device).where(Device.token == token, Device.user_id == user_id))
