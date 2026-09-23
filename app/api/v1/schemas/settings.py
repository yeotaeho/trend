# 화면 04·05 설정 모델 — 관심사(PUT 전체 교체)·알림 설정(PATCH 부분 병합) 요청·응답

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.v1.schemas.common import (
    DAILY_PUSH_CAP_MAX,
    DAILY_PUSH_CAP_MIN,
    KIND_WEIGHT_MAX,
    KIND_WEIGHT_MIN,
    WATCH_KEYWORDS_MAX,
    UtcDateTime,
)
from app.config import Delivery, get_rules
from app.schemas import Kind

WATCH_KEYWORD_MAX_LEN = 50
# 정적 — 탐색 슬롯은 하루 한 건이다 (jobs/notify.py _explore_sent_today).
EXPLORATION_DAILY_LIMIT = 1


class _In(BaseModel):
    # 모르는 키·읽기 전용 키(timezone·connected·daily_limit …)를 보내면 422.
    model_config = ConfigDict(extra="forbid")


class InterestProfile(BaseModel):
    self_description: str
    not_interested: str


class Interests(BaseModel):
    profile: InterestProfile
    selected_categories: list[str]
    watch_keywords: list[str]
    kind_weights: dict[Kind, float]
    updated_at: UtcDateTime | None


class InterestProfileIn(_In):
    self_description: str = Field(min_length=1, max_length=1000)
    not_interested: str = Field(max_length=500)


KindWeight = Annotated[float, Field(ge=KIND_WEIGHT_MIN, le=KIND_WEIGHT_MAX)]


class InterestsIn(_In):
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
    delivery_by_importance: DeliveryByImportance
    exploration_slot: ExplorationSlot
    updated_at: UtcDateTime | None


# 발송 정책이 시 단위라 정각만 받는다.
HourTime = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):00$")]


class ChannelIn(_In):
    enabled: bool


class ChannelsIn(_In):
    fcm: ChannelIn | None = None
    discord: ChannelIn | None = None
    telegram: ChannelIn | None = None


class QuietHoursIn(_In):
    start: HourTime | None = None
    end: HourTime | None = None


class DeliveryByImportanceIn(_In):
    high: Delivery | None = None
    mid: Delivery | None = None
    low: Delivery | None = None


class ExplorationSlotIn(_In):
    enabled: bool


class NotificationSettingsIn(_In):
    """바꿀 키만 보낸다. null 은 보내지 않은 것과 같다."""

    channels: ChannelsIn | None = None
    daily_push_cap: int | None = Field(default=None, ge=DAILY_PUSH_CAP_MIN, le=DAILY_PUSH_CAP_MAX)
    quiet_hours: QuietHoursIn | None = None
    dedupe_same_issue_daily: bool | None = None
    delivery_by_importance: DeliveryByImportanceIn | None = None
    exploration_slot: ExplorationSlotIn | None = None
