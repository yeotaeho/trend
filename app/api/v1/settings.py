# 설정 — 04·05 조회·저장, 키 되돌리기, 저장 이력·버전 되돌리기, 전체 설정·발송 막힘 사유

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
    SettingItem,
    SettingsOverview,
    TelegramChannel,
)
from app.config import (
    ChannelsConfig,
    Rules,
    Settings,
    app_key_path,
    changed_defaults,
    effective_rules,
    get_rules,
    get_settings,
    merge_overlay,
    overridden_keys,
    restorable,
    sanitize_overlay,
    setting_leaves,
    without_key,
    yaml_rules,
)
from app.db import prefs
from app.db.models import RevisionOrigin, SettingsRevision
from app.notify.base import channel_connected
from app.notify.policy import delivery_blocked
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


def _overridden(data: dict[str, Any], prefixes: tuple[str, ...]) -> list[str]:
    return [key for key in overridden_keys(data) if key.startswith(prefixes)]


_INTERESTS_KEYS = ("policy.", "scoring.kind_weights.")
_NOTIFICATION_KEYS = ("notify.",)


def _interests(rules: Rules, data: dict[str, Any], updated_at: datetime | None) -> Interests:
    """data 는 저장된 덮어쓰기다. overridden 을 고른다."""
    policy = rules.policy
    return Interests(
        profile=InterestProfile(
            self_description=policy.interests, not_interested=policy.not_interested
        ),
        selected_categories=policy.categories,
        watch_keywords=policy.focus_stack + policy.focus_repos,
        kind_weights={k: rules.scoring.kind_weights.get(k, 0.0) for k in Kind},
        updated_at=updated_at,
        overridden=_overridden(data, _INTERESTS_KEYS),
    )


@router.get("/interests")
async def get_interests(session: Session, user_id: UserId) -> Interests:
    data, updated_at = await prefs.current_prefs(session, user_id)
    return _interests(get_rules(), data, updated_at)


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
    return _interests(get_rules(), saved.data, saved.created_at)


def _discord_channel_name(settings: Settings) -> str | None:
    if settings.discord_channel_name:
        return settings.discord_channel_name
    return f"#{settings.discord_channel_id}" if settings.discord_channel_id else None


async def _notifications(
    session: AsyncSession, user_id: int, data: dict[str, Any], updated_at: datetime | None
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
        cluster_daily_cap=notify.cluster_daily_cap,
        delivery_by_importance=DeliveryByImportance(**notify.delivery_by_importance.model_dump()),
        exploration_slot=ExplorationSlot(
            enabled=notify.explore_enabled, daily_limit=EXPLORATION_DAILY_LIMIT
        ),
        updated_at=updated_at,
        overridden=_overridden(data, _NOTIFICATION_KEYS),
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
    data, updated_at = await prefs.current_prefs(session, user_id)
    return await _notifications(session, user_id, data, updated_at)


@router.patch("/notifications")
async def patch_notifications(
    body: NotificationSettingsIn, session: Session, user_id: UserId
) -> NotificationSettings:
    before = await prefs.prefs_for_update(session, user_id)
    if body.channels:
        _require_connected(body.channels, effective_rules(before).notify.channels)
    after = merge_overlay(before, {"notify": _notify_patch(body)})
    saved = await save_or_422(session, user_id, before, after)
    return await _notifications(session, user_id, saved.data, saved.created_at)


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


# GET /settings 에 보이는 서버 소유 키(VM .env). 비밀값은 키 이름도 내보내지 않는다.
_SERVER_KEYS = {
    "llm_model": "LLM 모델",
    "embedding_model": "임베딩 모델",
    "scheduler_enabled": "스케줄러",
}
# 공개 레포의 YAML 편집 화면. 앱은 YAML 소유 키를 여기로 보낸다.
_EDIT_URL = "https://github.com/yeotaeho/trend/edit/main/config"


@router.get("")
async def settings_overview(session: Session, user_id: UserId) -> SettingsOverview:
    """모든 설정 키를 값·기본값·출처·주인과 함께. 앱에서 바꿀 수 있는 것은 owner=app 뿐이다."""
    data, _ = await prefs.current_prefs(session, user_id)
    overlay = sanitize_overlay(data)
    app_keys = set(overridden_keys(overlay))
    changed = changed_defaults(overlay, await prefs.last_defaults(session, user_id))
    settings = get_settings()
    items = [
        SettingItem.model_validate(
            {
                "key": leaf.key,
                "label": leaf.label,
                "category": leaf.key.split(".")[0],
                "value": leaf.value,
                "default": leaf.default,
                "source": "app" if leaf.key in app_keys else "default",
                "owner": leaf.owner,
                "apply": leaf.apply,
                "default_changed": leaf.key in changed,
                "edit_url": f"{_EDIT_URL}/{leaf.file}",
            }
        )
        for leaf in setting_leaves(overlay)
    ]
    items += [
        SettingItem(
            key=f"server.{name}",
            label=label,
            category="server",
            value=getattr(settings, name),
            default=Settings.model_fields[name].default,
            source="default",
            owner="server",
            apply="restart",
            default_changed=False,
            edit_url=None,
        )
        for name, label in _SERVER_KEYS.items()
    ]
    latest = await queries.latest_revision_id(session, user_id)
    blocked = delivery_blocked(
        effective_rules(overlay).notify,
        channel_connected(settings),
        fcm_devices=await queries.active_device_count(session, user_id),
    )
    return SettingsOverview(
        revision=str(latest) if latest else None,
        git_sha=settings.git_sha or None,
        delivery_blocked=blocked,
        items=items,
    )
