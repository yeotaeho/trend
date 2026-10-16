# 사용자 설정 저장소 — user_prefs 읽기·차이만 저장(이력·소스 행·유효 설정 같이), 기동 시 적재

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    get_source_configs,
    overlay_changes,
    prune_overlay,
    sanitize_overlay,
    set_prefs_overlay,
    validate_overlay,
    warn_changed_defaults,
)
from app.db.models import RevisionOrigin, SettingsRevision, Source, User, UserPrefs
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


async def save_prefs(
    session: AsyncSession,
    user_id: int,
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    origin: RevisionOrigin = "app",
    note: str | None = None,
) -> SettingsRevision:
    """검증 → YAML 과 같은 값 지우기 → 저장·이력 한 행 → 소스 행 맞추기 → 커밋 → 유효 설정 교체.

    before 는 prefs_for_update 로 잠그고 읽은 값, after 는 거기에 바꿀 것을 합친 전체다. 앱 소유가
    아닌 키나 틀린 값은 ValueError 로 저장 전에 막는다. 커밋 뒤에 갈아끼운다. 먼저 바꾸면 커밋이
    실패한 설정이 프로세스에 남는다. 돌려주는 이력 행의 created_at 이 user_prefs.updated_at 이다.
    """
    validate_overlay(after)
    after = prune_overlay(after)
    updated_at = await upsert_prefs(session, user_id, after)
    revision = SettingsRevision(
        user_id=user_id,
        data=after,
        changes=overlay_changes(before, after),
        origin=origin,
        note=note,
        created_at=updated_at,
    )
    session.add(revision)
    default_user = user_id == DEFAULT_USER_ID  # 유효 설정과 소스 행은 기본 사용자 것 하나뿐이다
    if default_user:
        await _sync_source_rows(session, after)
    await session.commit()
    if default_user:
        set_prefs_overlay(after, updated_at)
    return revision


async def source_rows(session: AsyncSession, names: list[str]) -> dict[str, Source]:
    rows = await session.execute(select(Source).where(Source.name.in_(names)))
    return {s.name: s for s in rows.scalars()}


async def _sync_source_rows(session: AsyncSession, data: dict[str, Any]) -> None:
    """06 토글을 sources 행에 맞춘다. 덮어쓰기가 없으면 YAML 값이다(sync_sources 와 같은 규칙)."""
    configs = get_source_configs()
    rows = await source_rows(session, [c.name for c in configs])
    overrides = source_overrides(data)
    for cfg in configs:
        if row := rows.get(cfg.name):
            row.enabled = overrides.get(cfg.name, cfg.enabled)


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
        data = prefs.data if prefs else {}
        if data:
            warn_changed_defaults(data, await last_defaults(session, DEFAULT_USER_ID))
    set_prefs_overlay(data, prefs.updated_at if prefs else None)


async def last_defaults(session: AsyncSession, user_id: int) -> dict[str, Any]:
    """키마다 앱이 마지막으로 바꿀 때의 YAML 값(이력 changes 의 default)."""
    # ponytail: 이력을 전부 읽는다. 행이 수천을 넘으면 키별 최신 한 건만 SQL 로 뽑는다.
    stmt = (
        select(SettingsRevision.changes)
        .where(SettingsRevision.user_id == user_id)
        .order_by(SettingsRevision.id.desc())
    )
    defaults: dict[str, Any] = {}
    for changes in (await session.execute(stmt)).scalars():
        for change in changes:
            defaults.setdefault(change["key"], change["default"])
    return defaults


async def latest_revision_id(session: AsyncSession, user_id: int) -> int | None:
    """가장 최근 설정 이력 id. 전체 설정 조회와 결정 행의 settings_rev(#39)가 쓴다."""
    stmt = select(func.max(SettingsRevision.id)).where(SettingsRevision.user_id == user_id)
    latest: int | None = (await session.execute(stmt)).scalar_one()
    return latest
