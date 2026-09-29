# Alert 조회·직렬화 — 첫 전달 행, 카드 조립, 점수·선별 해석, 상세 근거 (피드·찜·걸러짐 공용)

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Row, Select, Subquery, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.alerts import (
    Alert,
    DeliveryMode,
    FeedbackValue,
    Judgment,
    Rationale,
    RecentFeedback,
    RecentFeedbackEntry,
    Routing,
    ScoreRationale,
    Screening,
    SimilarFeedback,
)
from app.db.models import Bookmark, Decision, Feedback, Item, Notification, Source, Summary
from app.schemas import Kind, Level, Stage

# notifications.level — 클러스터 하루 상한으로 보내지 않은 기록. 전달이 아니다 (계약 2).
CLUSTER_DUP = "cluster_dup"

LEVEL_TO_MODE = {
    Level.PUSH.value: DeliveryMode.INSTANT,
    Level.SILENT.value: DeliveryMode.QUIET,
    Level.FEED.value: DeliveryMode.FEED_ONLY,
    Level.EXPLORE.value: DeliveryMode.EXPERIMENT,
}
# DB 값은 그대로 두고 API 계층에서만 옮긴다. cleared(앱 해제)는 null.
VERDICT_TO_FEEDBACK = {"useful": FeedbackValue.USEFUL, "useless": FeedbackValue.NOT_USEFUL}
FEEDBACK_TO_VERDICT = {v: k for k, v in VERDICT_TO_FEEDBACK.items()}
# items.id 는 int4. 범위 밖 값을 바인딩하면 asyncpg 가 500 을 낸다.
INT4_MAX = 2**31 - 1
# 요약 없는 항목(복원 등)의 카드 본문 길이.
RAW_SUMMARY_CHARS = 200


def first_delivery(user_id: int) -> Subquery:
    """사용자의 항목별 첫 전달 행 하나. 오류 행·cluster_dup 행은 전달이 아니다.

    채널이 여럿이어도 카드는 한 장이고, 시각·강도·발송 제목은 가장 이른 행을 따른다.
    """
    return (
        select(
            Notification.item_id,
            Notification.sent_at,
            Notification.level,
            Notification.title,
        )
        .where(
            Notification.user_id == user_id,
            Notification.error.is_(None),
            Notification.level != CLUSTER_DUP,
        )
        .distinct(Notification.item_id)
        .order_by(Notification.item_id, Notification.sent_at, Notification.id)
        .subquery("delivery")
    )


def alert_select(user_id: int, delivery: Subquery, *, delivered_only: bool) -> Select[Any]:
    """Alert 한 장에 필요한 열. delivered_only 면 전달된 항목만 (피드), 아니면 전부 (상세)."""
    stmt = (
        select(
            Item.id,
            Item.title.label("item_title"),
            Item.url,
            Item.summary_raw,
            Source.name.label("source_id"),
            Source.type.label("source_type"),
            Source.config.label("source_config"),
            Summary.title_ko,
            Summary.summary_ko,
            Summary.tags,
            Summary.importance,
            delivery.c.sent_at,
            delivery.c.level,
            delivery.c.title.label("sent_title"),
            Feedback.verdict,
            Bookmark.item_id.label("saved_item_id"),
        )
        .select_from(Item)
        .join(Source, Source.id == Item.source_id)
    )
    on_delivery = delivery.c.item_id == Item.id
    stmt = (
        stmt.join(delivery, on_delivery)
        if delivered_only
        else stmt.outerjoin(delivery, on_delivery)
    )
    return (
        stmt.outerjoin(Summary, Summary.item_id == Item.id)
        .outerjoin(Feedback, and_(Feedback.item_id == Item.id, Feedback.user_id == user_id))
        .outerjoin(Bookmark, and_(Bookmark.item_id == Item.id, Bookmark.user_id == user_id))
    )


def source_display_name(name: str, config: dict[str, Any] | None) -> str:
    display = (config or {}).get("display_name")
    return display if isinstance(display, str) and display else name


def alert_title(sent_title: str | None, title_ko: str | None, item_title: str) -> str:
    """발송한 제목(형제 버전 병기) → 요약 제목 → 원문 제목."""
    return sent_title or title_ko or item_title


def topics_of(details: dict[str, Any] | None) -> list[str]:
    """선별 결정의 taxonomy slug. topics 를 내기 전의 옛 행·선별 전 항목은 []."""
    topics = (details or {}).get("topics")
    return [t for t in topics if isinstance(t, str)] if isinstance(topics, list) else []


async def last_triage(session: AsyncSession, item_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    """항목별 마지막 선별 결정(passed=true)의 details. 선별 오류 행은 결과가 아니다."""
    if not item_ids:
        return {}
    stmt = (
        select(Decision.item_id, Decision.details)
        .where(
            Decision.item_id.in_(item_ids),
            Decision.stage == Stage.TRIAGE.value,
            Decision.passed.is_(True),
        )
        .distinct(Decision.item_id)
        .order_by(Decision.item_id, Decision.created_at.desc(), Decision.id.desc())
    )
    return {item_id: details for item_id, details in (await session.execute(stmt)).all()}


def to_alert(row: Row[Any], categories: list[str]) -> Alert:
    level = row.level
    summary = row.summary_ko
    if summary is None and row.summary_raw:
        summary = row.summary_raw[:RAW_SUMMARY_CHARS]
    return Alert(
        id=str(row.id),
        source_id=row.source_id,
        source_name=source_display_name(row.source_id, row.source_config),
        source_type=row.source_type,
        delivered_at=row.sent_at,
        delivery_mode=LEVEL_TO_MODE.get(level) if level else None,
        is_exploration=level == Level.EXPLORE.value,
        title=alert_title(row.sent_title, row.title_ko, row.item_title),
        summary=summary,
        categories=categories,
        tags=list(row.tags or []),
        url=row.url,
        importance=row.importance,
        is_saved=row.saved_item_id is not None,
        feedback=VERDICT_TO_FEEDBACK.get(row.verdict) if row.verdict else None,
    )


async def build_alerts(session: AsyncSession, rows: Sequence[Row[Any]]) -> list[Alert]:
    """alert_select 행 → Alert. categories 는 마지막 선별 결정에서 한 번에 읽는다."""
    triage = await last_triage(session, [r.id for r in rows])
    return [to_alert(r, topics_of(triage.get(r.id))) for r in rows]


# ---------- 상세 근거 ----------


def _last(
    decisions: Sequence[Decision], stage: str, *, passed_only: bool = False
) -> Decision | None:
    """decisions 는 시각 오름차순. 조건에 맞는 마지막 행."""
    for d in reversed(decisions):
        if d.stage == stage and (d.passed or not passed_only):
            return d
    return None


def _details(decision: Decision | None) -> dict[str, Any] | None:
    return None if decision is None else decision.details or {}


def score_rationale(details: dict[str, Any] | None, threshold: float) -> ScoreRationale | None:
    """점수 결정 details → 점수. stale 탈락처럼 breakdown 이 없으면 점수가 없는 것으로 본다."""
    breakdown = (details or {}).get("breakdown")
    if not isinstance(breakdown, dict):
        return None
    components = {k: float(v) for k, v in breakdown.items()}
    return ScoreRationale(
        total=sum(components.values()), threshold=threshold, components=components
    )


def screening_of(details: dict[str, Any] | None) -> Screening | None:
    """선별 결정 details → 선별 결과. 선별 전 항목(None)은 None."""
    if details is None:
        return None
    kind = details.get("kind")
    relevance = details.get("relevance")
    return Screening(
        relevance=float(relevance) if isinstance(relevance, int | float) else None,
        kind=Kind(kind) if isinstance(kind, str) and kind in Kind else None,
        topics=topics_of(details),
        reason=details.get("reason"),
    )


def _similar(details: dict[str, Any]) -> list[SimilarFeedback]:
    """판정 때 프롬프트에 넣은 사례 {item_id, verdict, title}. 사례를 남기기 전 행은 []."""
    out: list[SimilarFeedback] = []
    for ex in details.get("examples") or []:
        if not isinstance(ex, dict) or ex.get("verdict") not in VERDICT_TO_FEEDBACK:
            continue
        out.append(
            SimilarFeedback(
                alert_id=str(ex.get("item_id", "")),
                feedback=VERDICT_TO_FEEDBACK[ex["verdict"]],
                title=str(ex.get("title", "")),
            )
        )
    return out


def _judgment(decision: Decision | None) -> Judgment | None:
    if decision is None:
        return None
    details = decision.details or {}
    importance = details.get("importance")
    return Judgment(
        importance=importance if isinstance(importance, int) else None,
        worth_notifying=decision.passed,
        similar_feedback=_similar(details),
    )


def _restored(decisions: Sequence[Decision], user_id: int) -> bool:
    """이 사용자의 마지막 복원 결정이 복원(passed)인가."""
    for d in reversed(decisions):
        if d.stage == Stage.USER.value and (d.details or {}).get("user_id") == user_id:
            return d.passed
    return False


def routing_for(
    alert: Alert, decisions: Sequence[Decision], *, user_id: int, cluster_dup: bool
) -> Routing:
    if alert.delivery_mode is None:
        return Routing.CLUSTER_DUP if cluster_dup else Routing.DROPPED
    if _restored(decisions, user_id):
        return Routing.RESTORED
    if alert.delivery_mode is DeliveryMode.EXPERIMENT:
        return Routing.EXPLORE_SLOT
    return Routing.PASSED


async def rationale_for(
    session: AsyncSession, alert: Alert, *, item_id: int, user_id: int, threshold: float
) -> Rationale:
    """항목 결정 행(항목당 몇 건)을 한 번에 읽어 단계별 마지막 행으로 근거를 만든다."""
    decisions = (
        await session.scalars(
            select(Decision)
            .where(Decision.item_id == item_id)
            .order_by(Decision.created_at, Decision.id)
        )
    ).all()
    cluster_dup = await session.scalar(
        select(
            select(Notification.id)
            .where(
                Notification.item_id == item_id,
                Notification.user_id == user_id,
                Notification.level == CLUSTER_DUP,
            )
            .exists()
        )
    )
    return Rationale(
        score=score_rationale(_details(_last(decisions, Stage.SCORE.value)), threshold),
        routing=routing_for(alert, decisions, user_id=user_id, cluster_dup=bool(cluster_dup)),
        screening=screening_of(_details(_last(decisions, Stage.TRIAGE.value, passed_only=True))),
        judgment=_judgment(_last(decisions, Stage.LLM.value)),
        trust_note_source=alert.source_name,
    )


# ---------- 최근 판정 ----------


async def recent_feedback(
    session: AsyncSession, user_id: int, *, limit: int, today: datetime
) -> RecentFeedback:
    """채널(앱·디스코드·텔레그램)을 가리지 않는 이 사용자의 판정. cleared 는 판정이 아니다.

    today_count 는 달력일(today = 오늘 자정) 판정 수, items 는 기간과 무관한 최근 limit 건.
    """
    judged = and_(Feedback.user_id == user_id, Feedback.verdict.in_(list(VERDICT_TO_FEEDBACK)))
    today_count = await session.scalar(
        select(func.count()).select_from(Feedback).where(judged, Feedback.created_at >= today)
    )
    delivery = first_delivery(user_id)
    stmt = (
        select(
            Feedback.item_id,
            Feedback.verdict,
            Feedback.created_at,
            Item.title.label("item_title"),
            Summary.title_ko,
            delivery.c.title.label("sent_title"),
        )
        .join(Item, Item.id == Feedback.item_id)
        .outerjoin(Summary, Summary.item_id == Feedback.item_id)
        .outerjoin(delivery, delivery.c.item_id == Feedback.item_id)
        .where(judged)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .limit(limit)
    )
    items = [
        RecentFeedbackEntry(
            alert_id=str(r.item_id),
            feedback=VERDICT_TO_FEEDBACK[r.verdict],
            title=alert_title(r.sent_title, r.title_ko, r.item_title),
            created_at=r.created_at,
        )
        for r in (await session.execute(stmt)).all()
    ]
    return RecentFeedback(today_count=today_count or 0, items=items)
