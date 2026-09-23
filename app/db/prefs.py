# 사용자 설정 저장소 — user_prefs 행 읽기·upsert, 저장 후 유효 설정 교체, 기동 시 덮어쓰기 적재

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import sanitize_overlay, set_prefs_overlay, validate_overlay
from app.db.models import User, UserPrefs
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID


async def fetch_prefs(
    session: AsyncSession, user_id: int, *, for_update: bool = False
) -> UserPrefs | None:
    """for_update 는 읽고-고쳐-쓰는 저장 경로용. 동시 저장 두 개가 서로를 덮지 않는다.

    user_prefs 행이 아직 없으면 잠글 것이 없어, 언제나 있는 users 행을 잠근다.
    """
    if for_update:
        # FOR NO KEY UPDATE — user_id FK 를 거는 삽입(알림·피드백)의 KEY SHARE 와 부딪치지 않는다.
        lock = select(User.id).where(User.id == user_id).with_for_update(key_share=True)
        await session.execute(lock)
    stmt = select(UserPrefs).where(UserPrefs.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def current_prefs(
    session: AsyncSession, user_id: int
) -> tuple[dict[str, Any], datetime | None]:
    """조회용 (data, updated_at). 한 번도 저장하지 않았으면 ({}, None)."""
    row = await fetch_prefs(session, user_id)
    return (dict(row.data), row.updated_at) if row else ({}, None)


async def prefs_for_update(session: AsyncSession, user_id: int) -> dict[str, Any]:
    """저장 경로용 data. 잠그고 읽으며, 기동 때 무시된 틀린 키는 떼어 낸다."""
    row = await fetch_prefs(session, user_id, for_update=True)
    return sanitize_overlay(row.data) if row else {}


async def upsert_prefs(session: AsyncSession, user_id: int, data: dict[str, Any]) -> datetime:
    """data 를 통째로 바꾸고 updated_at 을 돌려준다.

    now() 는 트랜잭션 시작 시각이라 잠금을 기다린 뒤 저장이 앞 저장보다 이를 수 있다.
    실제 시각(clock_timestamp)이어야 set_prefs_overlay 의 순서 비교가 맞다.
    """
    now = func.clock_timestamp()
    stmt = (
        insert(UserPrefs)
        .values(user_id=user_id, data=data, updated_at=now)
        .on_conflict_do_update(
            index_elements=[UserPrefs.user_id], set_={"data": data, "updated_at": now}
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
    if user_id == DEFAULT_USER_ID:  # 프로세스 유효 설정은 기본 사용자 것 하나뿐이다
        set_prefs_overlay(data, updated_at)
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
    set_prefs_overlay(prefs.data if prefs else {}, prefs.updated_at if prefs else None)
