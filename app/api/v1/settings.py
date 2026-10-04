# 화면 04·05 설정 — 관심사·알림 조회·저장, 키 되돌리기, 저장 이력·버전 되돌리기

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Session, UserId
from app.api.v1.errors import ApiError
from app.api.v1.pagination import Paging
from app.api.v1.queries import settings as queries
from app.api.v1.queries.saved import parse_id
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.settings import (
    EXPLORATION_DAILY_LIMIT,
    Channels,
    ChannelsIn,
    DeliveryByImportance,
    DiscordChannel,
    ExplorationSlot,
    FcmChannel,
    InterestProfile,
    Interests,
    InterestsIn,
    NotificationSettings,
    NotificationSettingsIn,
    QuietHours,
    RestoreResult,
    Revision,
    SettingChange,
    TelegramChannel,
)
from app.config import (
    ChannelsConfig,
    Rules,
    Settings,
    app_key_path,
    effective_rules,
    get_rules,
    get_settings,
    merge_overlay,
    restorable,
    without_key,
    yaml_rules,
)
from app.db import prefs
from app.db.models import RevisionOrigin, SettingsRevision
from app.notify.base import channel_connected
from app.schemas import Kind

router = APIRouter(prefix="/settings")

_CHANNEL_LABELS = {"fcm": "앱 푸시(FCM)", "discord": "Discord", "telegram": "Telegram"}


async def save_or_422(
    session: AsyncSession,
    user_id: int,
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    origin: RevisionOrigin = "app",
    note: str | None = None,
) -> SettingsRevision:
    """요청 모델을 통과해도 저장된 다른 값과 합쳐 검증에 실패할 수 있다. 그때는 저장하지 않는다."""
    try:
        return await prefs.save_prefs(session, user_id, before, after, origin=origin, note=note)
    except ValueError as exc:
        raise ApiError(
            422, "validation_error", "설정을 저장할 수 없습니다.", {"reason": str(exc)}
        ) from exc


def _interests(rules: Rules, updated_at: datetime | None) -> Interests:
    policy = rules.policy
    return Interests(
        profile=InterestProfile(
            self_description=policy.interests, not_interested=policy.not_interested
        ),
        selected_categories=policy.categories,
        watch_keywords=policy.focus_stack + policy.focus_repos,
        kind_weights={k: rules.scoring.kind_weights.get(k, 0.0) for k in Kind},
        updated_at=updated_at,
    )


@router.get("/interests")
async def get_interests(session: Session, user_id: UserId) -> Interests:
    _, updated_at = await prefs.current_prefs(session, user_id)
    return _interests(get_rules(), updated_at)


@router.put("/interests")
async def put_interests(body: InterestsIn, session: Session, user_id: UserId) -> Interests:
    before = await prefs.prefs_for_update(session, user_id)
    policy = {
        "interests": body.profile.self_description,
        "not_interested": body.profile.not_interested,
        "categories": body.selected_categories,
        # `/` 가 들어간 키워드는 저장소 패턴(anthropics/*)이다.
        "focus_stack": [k for k in body.watch_keywords if "/" not in k],
        "focus_repos": [k for k in body.watch_keywords if "/" in k],
    }
    weights = {kind.value: round(w, 2) for kind, w in body.kind_weights.items()}
    after = merge_overlay(before, {"policy": policy, "scoring": {"kind_weights": weights}})
    saved = await save_or_422(session, user_id, before, after)
    return _interests(get_rules(), saved.created_at)


def _discord_channel_name(settings: Settings) -> str | None:
    if settings.discord_channel_name:
        return settings.discord_channel_name
    return f"#{settings.discord_channel_id}" if settings.discord_channel_id else None


async def _notifications(
    session: AsyncSession, user_id: int, updated_at: datetime | None
) -> NotificationSettings:
    notify = get_rules().notify
    settings = get_settings()
    connected = channel_connected(settings)
    return NotificationSettings(
        channels=Channels(
            fcm=FcmChannel(
                enabled=notify.channels.fcm,
                connected=connected["fcm"],
                device_count=await queries.active_device_count(session, user_id),
            ),
            discord=DiscordChannel(
                enabled=notify.channels.discord,
                connected=connected["discord"],
                channel_name=_discord_channel_name(settings),
                # 리액션 폴링 잡은 디스코드가 연결돼 있으면 돈다.
                reaction_sync=connected["discord"],
            ),
            telegram=TelegramChannel(
                enabled=notify.channels.telegram, connected=connected["telegram"]
            ),
        ),
        daily_push_cap=notify.daily_push_cap,
        quiet_hours=QuietHours(
            start=f"{notify.quiet_start_hour:02d}:00",
            end=f"{notify.quiet_end_hour:02d}:00",
            timezone=notify.timezone,
        ),
        dedupe_same_issue_daily=notify.cluster_daily_cap > 0,
        delivery_by_importance=DeliveryByImportance(**notify.delivery_by_importance.model_dump()),
        exploration_slot=ExplorationSlot(
            enabled=notify.explore_enabled, daily_limit=EXPLORATION_DAILY_LIMIT
        ),
        updated_at=updated_at,
    )


def _require_connected(channels: ChannelsIn, current: ChannelsConfig) -> None:
    """꺼진 채널을 켤 때만 본다. YAML 기본으로 이미 켜진 미연결 채널을 그대로 보내는 건 된다.

    current 는 잠근 뒤 읽은 저장값 기준이어야 한다. 잠그기 전 캐시로 보면 동시 PATCH 가 끈
    미연결 채널을 다시 켤 수 있다.
    """
    connected = channel_connected(get_settings())
    for name, change in channels:
        turning_on = change is not None and change.enabled and not getattr(current, name)
        if turning_on and not connected[name]:
            raise ApiError(
                409,
                "channel_not_connected",
                f"{_CHANNEL_LABELS[name]} 연결 정보가 없어 켤 수 없습니다.",
                {"channel": name},
            )


def _notify_patch(body: NotificationSettingsIn) -> dict[str, Any]:
    """요청 필드 → rules.notify 덮어쓰기 키."""
    patch: dict[str, Any] = {}
    if body.channels:
        patch["channels"] = {name: c.enabled for name, c in body.channels if c is not None}
    if body.daily_push_cap is not None:
        patch["daily_push_cap"] = body.daily_push_cap
    if body.quiet_hours:
        if body.quiet_hours.start is not None:
            patch["quiet_start_hour"] = int(body.quiet_hours.start[:2])
        if body.quiet_hours.end is not None:
            patch["quiet_end_hour"] = int(body.quiet_hours.end[:2])
    if body.delivery_by_importance:
        patch["delivery_by_importance"] = body.delivery_by_importance.model_dump(exclude_none=True)
    if body.exploration_slot:
        patch["explore_enabled"] = body.exploration_slot.enabled
    if body.dedupe_same_issue_daily is not None:
        # 토글은 상한 숫자를 바꾸지 않는다. 끄면 0, 켜면 YAML 값(0 이면 1)이다.
        on = yaml_rules().notify.cluster_daily_cap or 1
        patch["cluster_daily_cap"] = on if body.dedupe_same_issue_daily else 0
    return patch


@router.get("/notifications")
async def get_notifications(session: Session, user_id: UserId) -> NotificationSettings:
    _, updated_at = await prefs.current_prefs(session, user_id)
    return await _notifications(session, user_id, updated_at)


@router.patch("/notifications")
async def patch_notifications(
    body: NotificationSettingsIn, session: Session, user_id: UserId
) -> NotificationSettings:
    before = await prefs.prefs_for_update(session, user_id)
    if body.channels:
        _require_connected(body.channels, effective_rules(before).notify.channels)
    after = merge_overlay(before, {"notify": _notify_patch(body)})
    saved = await save_or_422(session, user_id, before, after)
    return await _notifications(session, user_id, saved.created_at)


@router.delete("/overrides/{key}", status_code=204)
async def delete_override(key: str, session: Session, user_id: UserId) -> None:
    """앱이 덮어쓴 키 하나를 YAML 값으로 되돌린다. 덮어쓰지 않은 키여도 204 다."""
    path = app_key_path(key)
    if path is None:
        raise ApiError(404, "not_found", "되돌릴 수 있는 설정 키가 아닙니다.", {"key": key})
    before = await prefs.prefs_for_update(session, user_id)
    await save_or_422(session, user_id, before, without_key(before, path), origin="reset")


def _revision(row: SettingsRevision) -> Revision:
    return Revision(
        id=str(row.id),
        origin=cast(RevisionOrigin, row.origin),
        note=row.note,
        changes=[SettingChange(**change) for change in row.changes],
        created_at=row.created_at,
    )


@router.get("/revisions")
async def list_revisions(session: Session, user_id: UserId, paging: Paging) -> Page[Revision]:
    rows, next_cursor = await queries.revision_page(session, user_id, paging)
    return Page[Revision](items=[_revision(r) for r in rows], next_cursor=next_cursor)


@router.post("/revisions/{revision_id}/restore")
async def restore_revision(revision_id: str, session: Session, user_id: UserId) -> RestoreResult:
    """그 저장 뒤의 덮어쓰기로 되돌린다. 지금 모델·주인에 맞지 않는 키는 버리고 dropped 로 알린다.

    되돌리기도 저장 한 번이라 이력이 한 행 늘어난다.
    """
    rid = parse_id(revision_id)
    row = await queries.find_revision(session, user_id, rid) if rid else None
    if row is None:
        raise ApiError(
            404, "not_found", "설정 이력을 찾을 수 없습니다.", {"revision_id": revision_id}
        )
    data, dropped = restorable(row.data)
    before = await prefs.prefs_for_update(session, user_id)
    saved = await save_or_422(
        session, user_id, before, data, origin="restore", note=f"#{rid} 저장으로 되돌림"
    )
    return RestoreResult(revision=_revision(saved), dropped=dropped)
