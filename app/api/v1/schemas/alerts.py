# 알림 응답 모델 — Alert 카드, 상세 근거(rationale), 피드백 설정·최근 판정, 관련 열거형

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.api.v1.schemas.common import UtcDateTime
from app.schemas import Kind


class DeliveryMode(StrEnum):
    INSTANT = "instant"
    QUIET = "quiet"
    FEED_ONLY = "feed_only"
    EXPERIMENT = "experiment"


class FeedbackValue(StrEnum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"


class Routing(StrEnum):
    PASSED = "passed"
    EXPLORE_SLOT = "explore_slot"
    RESTORED = "restored"
    DROPPED = "dropped"
    CLUSTER_DUP = "cluster_dup"


class Alert(BaseModel):
    """피드 카드 한 장. 발송된 적 없는 항목(상세)은 delivered_at·delivery_mode 가 null."""

    id: str
    source_id: str
    source_name: str
    source_type: str
    delivered_at: UtcDateTime | None
    delivery_mode: DeliveryMode | None
    is_exploration: bool
    title: str
    summary: str | None
    categories: list[str]
    tags: list[str]
    url: str
    importance: int | None
    is_saved: bool
    feedback: FeedbackValue | None


class ScoreRationale(BaseModel):
    total: float
    threshold: float
    components: dict[str, float]


class Screening(BaseModel):
    relevance: float | None
    kind: Kind | None
    topics: list[str]
    reason: str | None


class SimilarFeedback(BaseModel):
    alert_id: str
    feedback: FeedbackValue
    title: str


class Judgment(BaseModel):
    importance: int | None
    worth_notifying: bool
    similar_feedback: list[SimilarFeedback]


class Rationale(BaseModel):
    score: ScoreRationale | None
    routing: Routing
    screening: Screening | None
    judgment: Judgment | None
    trust_note_source: str


class AlertDetail(Alert):
    rationale: Rationale


class FeedbackIn(BaseModel):
    verdict: FeedbackValue


class FeedbackOut(BaseModel):
    alert_id: str
    feedback: FeedbackValue
    updated_at: UtcDateTime


class RecentFeedbackEntry(BaseModel):
    alert_id: str
    feedback: FeedbackValue
    title: str
    created_at: UtcDateTime


class RecentFeedback(BaseModel):
    today_count: int
    items: list[RecentFeedbackEntry]
