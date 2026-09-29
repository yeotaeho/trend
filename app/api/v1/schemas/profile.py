# 화면 08 내 프로필 응답 모델 — 기간, 사용자 행, 통계, 카테고리 반응, 학습된 취향, 표시 이름 변경

from __future__ import annotations

from enum import IntEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.api.v1.schemas.common import StrictIn
from app.api.v1.schemas.reports import ReportRef
from app.schemas import Kind

DISPLAY_NAME_MAX = 20
CATEGORY_REACTIONS_TOP = 6


class PeriodDays(IntEnum):
    WEEK = 7
    TWO_WEEKS = 14
    MONTH = 30


class ProfileUser(BaseModel):
    display_name: str
    discord_connected: bool
    onboarding_done: int
    onboarding_total: int


class ProfileStats(BaseModel):
    alerts_received: int
    push_count: int
    experiment_count: int
    useful_count: int
    not_useful_count: int
    useful_ratio: int | None
    missed_issues: int


class CategoryReaction(BaseModel):
    category: str
    useful: int
    not_useful: int
    total: int


class KindPenalty(BaseModel):
    kind: Kind
    weight: float
    not_useful: int
    total: int
    active: bool


class SourceTrustChange(BaseModel):
    source_id: str
    source_name: str
    # from 은 파이썬 예약어라 필드 이름만 바꾸고 JSON 키는 계약대로 둔다.
    from_: float = Field(serialization_alias="from")
    to: float


class Learned(BaseModel):
    kind_penalties: list[KindPenalty]
    source_trust_changes: list[SourceTrustChange]
    profile_vector_labels: int
    personal_model_threshold: int


class Profile(BaseModel):
    period_days: PeriodDays
    user: ProfileUser
    stats: ProfileStats
    category_reactions: list[CategoryReaction]
    learned: Learned
    weekly_report_latest: ReportRef | None


class ProfileIn(StrictIn):
    display_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=DISPLAY_NAME_MAX)
    ]
