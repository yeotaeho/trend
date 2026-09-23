# 화면 03 피드 응답 모델 — 오늘 요약 줄, 피드 필터 칩

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class FeedFilter(StrEnum):
    ALL = "all"
    INSTANT = "instant"
    QUIET = "quiet"
    EXPERIMENT = "experiment"
    USEFUL = "useful"


class TodayStats(BaseModel):
    date: str
    timezone: str
    push_sent_today: int
    daily_push_cap: int
    window_hours: int
    collected_count: int
    filtered_count: int
