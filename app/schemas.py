# 파이프라인 공용 Pydantic 스키마 — 정규화 항목·LLM 판정·열거형

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    MODEL = "model"
    LIBRARY = "library"
    TECHNIQUE = "technique"
    TOOL_MCP = "tool_mcp"
    COMMUNITY = "community"
    VIDEO = "video"
    UNKNOWN = "unknown"


class ItemStatus(StrEnum):
    NEW = "NEW"
    FILTERED_OUT = "FILTERED_OUT"
    SCORED = "SCORED"
    DROPPED = "DROPPED"
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"


class Stage(StrEnum):
    RULE = "rule"
    TRIAGE = "triage"
    SCORE = "score"
    LLM = "llm"


class Level(StrEnum):
    PUSH = "push"
    SILENT = "silent"
    FEED = "feed"
    EXPLORE = "explore"  # 하루 1건 경계 항목 실험. push 상한에서 제외


class NormalizedItem(BaseModel):
    """수집기가 소스와 무관하게 돌려주는 공통 형태."""

    source: str
    external_id: str
    url: str
    title: str
    body: str | None = None
    author: str | None = None
    published_at: datetime
    category_hint: Category | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    raw: dict[str, object] = Field(default_factory=dict)


class LLMVerdict(BaseModel):
    """LLM 이 한 번의 호출로 돌려주는 구조화 출력."""

    worth_notifying: bool
    importance: int = Field(ge=1, le=5)
    category: Category
    title_ko: str
    summary_ko: str
    tags: list[str] = Field(default_factory=list)
