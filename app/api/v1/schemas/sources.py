# 화면 06 수집 소스 모델 — 소스 한 줄(Source)·상단 Stat·목록 응답, on/off 요청

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.api.v1.schemas.common import StrictIn, UtcDateTime

SourceGroup = Literal["blog_rss", "paper_release_video", "community"]


class Source(BaseModel):
    id: str
    display_name: str
    type: str
    group: SourceGroup
    enabled: bool
    poll_interval_min: int
    trust: float
    trust_base: float
    trust_calibrated: float | None
    consecutive_failures: int
    error_hint: str | None
    last_error: str | None
    last_polled_at: UtcDateTime | None
    repo_count: int | None


class BudgetUse(BaseModel):
    used: int
    cap: int


class LlmBudget(BaseModel):
    triage: BudgetUse
    judge: BudgetUse
    explore: BudgetUse


class SourceStats(BaseModel):
    enabled_count: int
    total: int
    window_hours: int
    items_collected: int
    llm_budget: LlmBudget


class SourceList(BaseModel):
    stats: SourceStats
    sources: list[Source]
    planned_sources: list[str]


class SourcePatch(StrictIn):
    enabled: bool
