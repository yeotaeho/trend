# 사용자 설정 저장소 — user_prefs 행 읽기·upsert, 저장 후 유효 설정 교체, 기동 시 덮어쓰기 적재

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import set_prefs_overlay, validate_overlay
from app.db.models import UserPrefs
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID


async def fetch_prefs(
    session: AsyncSession, user_id: int, *, for_update: bool = False
) -> UserPrefs | None:
    """for_update 는 읽고-고쳐-쓰는 저장 경로용. 동시 PATCH 두 개가 서로를 덮지 않는다."""
    stmt = select(UserPrefs).where(UserPrefs.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert_prefs(session: AsyncSession, user_id: int, data: dict[str, Any]) -> datetime:
    """data 를 통째로 바꾸고 DB 시각의 updated_at 을 돌려준다."""
    stmt = (
        insert(UserPrefs)
        .values(user_id=user_id, data=data)
        .on_conflict_do_update(
            index_elements=[UserPrefs.user_id], set_={"data": data, "updated_at": func.now()}
        )
        .returning(UserPrefs.updated_at)
    )
    updated_at: datetime = (await session.execute(stmt)).scalar_one()
    return updated_at


async def save_prefs(session: AsyncSession, user_id: int, data: dict[str, Any]) -> datetime:
    """검증 → 저장 → 커밋 → 유효 설정 교체. 틀린 설정은 ValueError 로 저장 전에 막는다.

    커밋 뒤에 갈아끼운다. 먼저 바꾸면 커밋이 실패한 설정이 프로세스에 남는다.
    """
    validate_overlay(data)
    updated_at = await upsert_prefs(session, user_id, data)
    await session.commit()
    set_prefs_overlay(data)
    return updated_at


def source_overrides(data: dict[str, Any]) -> dict[str, bool]:
    """user_prefs.data.sources → {소스 이름: enabled}. 모양이 틀린 항목은 건너뛴다."""
    sources = data.get("sources")
    if not isinstance(sources, dict):
        return {}
    return {
        name: value["enabled"]
        for name, value in sources.items()
        if isinstance(value, dict) and isinstance(value.get("enabled"), bool)
    }


async def load_prefs_overlay() -> None:
    """기동 시 한 번, 스케줄러보다 먼저. 첫 잡부터 앱에서 저장한 설정으로 돈다."""
    async with session_scope() as session:
        prefs = await fetch_prefs(session, DEFAULT_USER_ID)
    set_prefs_overlay(prefs.data if prefs else {})
