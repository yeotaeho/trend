# GET /meta 응답 모델 — taxonomy 라벨·kind 목록·입력 한도·재알림 일수

from __future__ import annotations

from pydantic import BaseModel

from app.api.v1.schemas.common import UtcDateTime
from app.schemas import Kind


class TaxonomyEntry(BaseModel):
    slug: str
    label: str


class StepRange(BaseModel):
    min: float
    max: float
    step: float


class IntRange(BaseModel):
    min: int
    max: int


class Limits(BaseModel):
    kind_weight: StepRange
    daily_push_cap: IntRange
    watch_keywords_max: int
    folder_name_max: int
    memo_max: int


class Meta(BaseModel):
    server_time: UtcDateTime
    timezone: str
    taxonomy: list[TaxonomyEntry]
    kinds: list[Kind]
    limits: Limits
    resurface_unread_after_days: int
