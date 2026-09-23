# 화면 04·05 설정 — 관심사·알림 설정 조회·저장. 저장은 user_prefs 덮어쓰기 + 유효 설정 즉시 교체

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import Session, UserId
from app.api.v1.errors import ApiError
from app.api.v1.queries import settings as queries
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
    TelegramChannel,
)
from app.config import (
    ChannelsConfig,
    Rules,
    Settings,
    effective_rules,
    get_rules,
    get_settings,
    merge_overlay,
    yaml_rules,
)
from app.db import prefs
from app.notify.base import channel_connected
from app.schemas import Kind

router = APIRouter(prefix="/settings")

_CHANNEL_LABELS = {"fcm": "앱 푸시(FCM)", "discord": "Discord", "telegram": "Telegram"}


async def save_or_422(session: AsyncSession, user_id: int, data: dict[str, Any]) -> datetime:
    """요청 모델을 통과해도 저장된 다른 값과 합쳐 검증에 실패할 수 있다. 그때는 저장하지 않는다."""
    try:
        return await prefs.save_prefs(session, user_id, data)
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
    data = await prefs.prefs_for_update(session, user_id)
    policy = {
        "interests": body.profile.self_description,
        "not_interested": body.profile.not_interested,
        "categories": body.selected_categories,
        # `/` 가 들어간 키워드는 저장소 패턴(anthropics/*)이다.
        "focus_stack": [k for k in body.watch_keywords if "/" not in k],
        "focus_repos": [k for k in body.watch_keywords if "/" in k],
    }
    weights = {kind.value: round(w, 2) for kind, w in body.kind_weights.items()}
    data = merge_overlay(data, {"policy": policy, "scoring": {"kind_weights": weights}})
    updated_at = await save_or_422(session, user_id, data)
    return _interests(get_rules(), updated_at)


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
    """요청 필드 → rules.notify 덮어쓰기 키. dedupe_same_issue_daily 는 따로 옮긴다."""
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
    return patch


def _with_cluster_cap(data: dict[str, Any], dedupe: bool) -> dict[str, Any]:
    """토글은 상한 숫자를 바꾸지 않는다. 끄면 0, 켜면 YAML 값(0 이면 1)으로 돌아간다."""
    notify = dict(data.get("notify", {}))
    if not dedupe:
        notify["cluster_daily_cap"] = 0
    elif yaml_rules().notify.cluster_daily_cap >= 1:
        notify.pop("cluster_daily_cap", None)
    else:
        notify["cluster_daily_cap"] = 1
    return {**data, "notify": notify}


@router.get("/notifications")
async def get_notifications(session: Session, user_id: UserId) -> NotificationSettings:
    _, updated_at = await prefs.current_prefs(session, user_id)
    return await _notifications(session, user_id, updated_at)


@router.patch("/notifications")
async def patch_notifications(
    body: NotificationSettingsIn, session: Session, user_id: UserId
) -> NotificationSettings:
    data = await prefs.prefs_for_update(session, user_id)
    if body.channels:
        _require_connected(body.channels, effective_rules(data).notify.channels)
    if patch := _notify_patch(body):
        data = merge_overlay(data, {"notify": patch})
    if body.dedupe_same_issue_daily is not None:
        data = _with_cluster_cap(data, body.dedupe_same_issue_daily)
    updated_at = await save_or_422(session, user_id, data)
    return await _notifications(session, user_id, updated_at)
