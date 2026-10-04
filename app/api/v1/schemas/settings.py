# 설정 모델 — 04 관심사(PUT 전체)·05 알림(PATCH 부분) 요청·응답, 저장 이력, 전체 설정

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.api.v1.schemas.common import (
    DAILY_PUSH_CAP_MAX,
    DAILY_PUSH_CAP_MIN,
    INTERESTS_MAX_CHARS,
    NOT_INTERESTED_MAX_CHARS,
    WATCH_KEYWORDS_MAX,
    StrictIn,
    UtcDateTime,
)
from app.config import Delivery, KindWeight, get_rules
from app.db.models import RevisionOrigin
from app.notify.policy import DeliveryBlocked
from app.schemas import Kind

WATCH_KEYWORD_MAX_LEN = 50
# 정적 — 탐색 슬롯은 하루 한 건이다 (jobs/notify.py _explore_sent_today).
EXPLORATION_DAILY_LIMIT = 1


class InterestProfile(BaseModel):
    self_description: str
    not_interested: str


class Interests(BaseModel):
    profile: InterestProfile
    selected_categories: list[str]
    watch_keywords: list[str]
    kind_weights: dict[Kind, float]
    updated_at: UtcDateTime | None
    # 이 화면 키 가운데 앱 값이 있는 것(점 경로). 없으면 빈 목록이다(#35).
    overridden: list[str] = Field(default_factory=list)


class InterestProfileIn(StrictIn):
    self_description: str = Field(min_length=1, max_length=INTERESTS_MAX_CHARS)
    not_interested: str = Field(max_length=NOT_INTERESTED_MAX_CHARS)


class InterestsIn(StrictIn):
    profile: InterestProfileIn
    selected_categories: list[str] = Field(min_length=1)
    watch_keywords: list[str] = Field(max_length=WATCH_KEYWORDS_MAX)
    # 빠진 kind 는 현재 유효값을 유지한다.
    kind_weights: dict[Kind, KindWeight]

    @field_validator("selected_categories")
    @classmethod
    def _within_taxonomy(cls, value: list[str]) -> list[str]:
        taxonomy = get_rules().policy.taxonomy
        unknown = [c for c in value if c not in taxonomy]
        if unknown:
            raise ValueError(f"분류표에 없는 카테고리입니다: {', '.join(unknown)}")
        if len(set(value)) != len(value):
            raise ValueError("카테고리가 중복되었습니다.")
        return value

    @field_validator("watch_keywords")
    @classmethod
    def _normalize_keywords(cls, value: list[str]) -> list[str]:
        """앞뒤 공백을 떼고 대소문자 무시로 중복을 지운다. 처음 나온 표기를 남긴다."""
        seen: set[str] = set()
        keywords: list[str] = []
        for raw in value:
            keyword = raw.strip()
            if not 1 <= len(keyword) <= WATCH_KEYWORD_MAX_LEN:
                raise ValueError(f"키워드는 1~{WATCH_KEYWORD_MAX_LEN}자여야 합니다.")
            if keyword.casefold() not in seen:
                seen.add(keyword.casefold())
                keywords.append(keyword)
        return keywords


class FcmChannel(BaseModel):
    enabled: bool
    connected: bool
    device_count: int


class DiscordChannel(BaseModel):
    enabled: bool
    connected: bool
    channel_name: str | None
    reaction_sync: bool


class TelegramChannel(BaseModel):
    enabled: bool
    connected: bool


class Channels(BaseModel):
    fcm: FcmChannel
    discord: DiscordChannel
    telegram: TelegramChannel


class QuietHours(BaseModel):
    start: str
    end: str
    timezone: str


class DeliveryByImportance(BaseModel):
    high: Delivery
    mid: Delivery
    low: Delivery


class ExplorationSlot(BaseModel):
    enabled: bool
    daily_limit: int


class NotificationSettings(BaseModel):
    channels: Channels
    daily_push_cap: int
    quiet_hours: QuietHours
    dedupe_same_issue_daily: bool
    # 같은 이슈 하루 상한(유효값, 0 = 끔). 읽기 전용이라 PATCH 로 보내면 422 다.
    cluster_daily_cap: int
    delivery_by_importance: DeliveryByImportance
    exploration_slot: ExplorationSlot
    updated_at: UtcDateTime | None
    # 이 화면 키 가운데 앱 값이 있는 것(점 경로). 없으면 빈 목록이다(#35).
    overridden: list[str] = Field(default_factory=list)


# 발송 정책이 시 단위라 정각만 받는다.
HourTime = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):00$")]


class ChannelIn(StrictIn):
    enabled: bool


class ChannelsIn(StrictIn):
    fcm: ChannelIn | None = None
    discord: ChannelIn | None = None
    telegram: ChannelIn | None = None


class QuietHoursIn(StrictIn):
    start: HourTime | None = None
    end: HourTime | None = None


class DeliveryByImportanceIn(StrictIn):
    high: Delivery | None = None
    mid: Delivery | None = None
    low: Delivery | None = None


class ExplorationSlotIn(StrictIn):
    enabled: bool


class NotificationSettingsIn(StrictIn):
    """바꿀 키만 보낸다. null 은 보내지 않은 것과 같다."""

    channels: ChannelsIn | None = None
    daily_push_cap: int | None = Field(default=None, ge=DAILY_PUSH_CAP_MIN, le=DAILY_PUSH_CAP_MAX)
    quiet_hours: QuietHoursIn | None = None
    dedupe_same_issue_daily: bool | None = None
    delivery_by_importance: DeliveryByImportanceIn | None = None
    exploration_slot: ExplorationSlotIn | None = None


class SettingChange(BaseModel):
    """유효값이 바뀐 앱 소유 키 하나. default 는 저장 때의 YAML 값이다."""

    key: str
    old: Any
    new: Any
    default: Any


class Revision(BaseModel):
    id: str
    origin: RevisionOrigin
    note: str | None
    changes: list[SettingChange]
    created_at: UtcDateTime


class RestoreResult(BaseModel):
    revision: Revision
    # 옛 저장값 가운데 지금 모델·주인에 맞지 않아 버린 키
    dropped: list[str]


# 키의 첫 마디. app 은 config/app.yaml, sources 는 config/sources.yaml, server 는 VM .env 다.
SettingCategory = Literal[
    "policy",
    "exclude",
    "dedupe",
    "triage",
    "scoring",
    "notify",
    "budget",
    "app",
    "sources",
    "server",
]


class SettingItem(BaseModel):
    key: str
    label: str
    category: SettingCategory
    value: Any
    default: Any
    source: Literal["default", "app"]
    owner: Literal["app", "yaml", "server"]
    apply: Literal["next_job", "deploy", "restart"]
    # 앱 값이 있는데 앱이 마지막으로 바꾼 뒤 YAML 기본값이 바뀌었다
    default_changed: bool
    edit_url: str | None


class SettingsOverview(BaseModel):
    revision: str | None
    git_sha: str | None
    delivery_blocked: list[DeliveryBlocked]
    items: list[SettingItem]
