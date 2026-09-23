# 화면 09·10 걸러진 항목 응답 모델 — 관문·보기·정렬 열거형, DroppedItem, 요약·그룹·복원

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.api.v1.schemas.alerts import Alert, ScoreRationale
from app.api.v1.schemas.common import UtcDateTime
from app.schemas import Kind


class Gate(StrEnum):
    """걸러진 관문. 순서가 GateBar 구간 순서다 (계약 2)."""

    EXCLUDE = "exclude"
    DEDUP = "dedup"
    STALE = "stale"
    SCREENING = "screening"
    SCORE = "score"
    JUDGMENT = "judgment"
    CLUSTER_DUP = "cluster_dup"


class FilteredView(StrEnum):
    SOURCE = "source"
    KIND = "kind"
    GATE = "gate"


class GroupSort(StrEnum):
    COUNT_DESC = "count_desc"
    NAME_ASC = "name_asc"


class DroppedItem(BaseModel):
    id: str
    title: str
    url: str
    source_id: str
    source_name: str
    source_type: str
    dropped_gate: Gate
    dropped_at: UtcDateTime
    relevance: float | None
    kind: Kind | None
    topics: list[str]
    reason: str | None
    score: ScoreRationale | None
    matched_keywords: list[str]
    exploration_candidate: bool
    restored: bool


class Borderline(BaseModel):
    count: int
    range: tuple[float, float]


class FilteredSummary(BaseModel):
    window_hours: int
    filtered_total: int
    collected_total: int
    gate_counts: dict[Gate, int]
    borderline: Borderline
    unclassified_count: int


class GroupSource(BaseModel):
    id: str
    display_name: str
    type: str


class KindFeedback(BaseModel):
    not_useful: int
    total: int


class FilteredGroup(BaseModel):
    key: str
    count: int
    gate_counts: dict[Gate, int]
    source: GroupSource | None
    kind: Kind | None
    gate: Gate | None
    low_relevance_ratio: float | None
    kind_weight: float | None
    kind_feedback: KindFeedback | None
    penalty_active: bool
    borderline_count: int
    exclude_keyword_hits: int
    preview: list[DroppedItem]


class FilteredGroups(BaseModel):
    view: FilteredView
    groups: list[FilteredGroup]


class RestoreOut(BaseModel):
    item_id: str
    restored: bool
    alert: Alert
