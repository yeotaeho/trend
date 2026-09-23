# 걸러진 항목 조회 — 탈락 항목 + 클러스터 하루 상한 항목 집합, 관문 분류, 요약·그룹·목록, 복원·취소

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, Row, Subquery, delete, func, null, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.v1.errors import ApiError
from app.api.v1.pagination import PageParams, paginate
from app.api.v1.queries.alerts import (
    CLUSTER_DUP,
    VERDICT_TO_FEEDBACK,
    score_rationale,
    screening_of,
    source_display_name,
)
from app.api.v1.schemas.filtered import (
    Borderline,
    DroppedItem,
    FilteredGroup,
    FilteredSummary,
    FilteredView,
    Gate,
    GroupSort,
    GroupSource,
    KindFeedback,
)
from app.db.feedback import clear_feedback, set_app_feedback
from app.db.models import Decision, Feedback, Item, Notification, Source
from app.jobs.notify import EXPLORE_BAND, explore_candidate
from app.notify.base import APP_CHANNEL
from app.schemas import ItemStatus, Kind, Level, Stage

WINDOW_HOURS = 24
MAX_WINDOW_HOURS = 168
PREVIEW_SIZE = 3
KIND_FEEDBACK_DAYS = 30
UNCLASSIFIED = "unclassified"
DROPPED_STATUSES = (ItemStatus.DROPPED.value, ItemStatus.FILTERED_OUT.value)
RESTORE_REASON = "restored"


# ---------- 걸러진 항목 집합 ----------


def _restored(user_id: int) -> ColumnElement[bool]:
    """Item 에 상관. 이 사용자가 복원한 항목인가. 취소하면 결정 행을 지우므로 존재가 곧 복원이다."""
    return (
        select(Decision.id)
        .where(
            Decision.item_id == Item.id,
            Decision.stage == Stage.USER.value,
            Decision.passed.is_(True),
            Decision.details.contains({"user_id": user_id}),
        )
        .exists()
    )


def filtered_set(
    user_id: int, *, since: datetime | None = None, item_id: int | None = None
) -> Subquery:
    """걸러진 항목 (item_id, dropped_at, decision_id). since 가 없으면 창 제한 없이 전부.

    - 상태 DROPPED·FILTERED_OUT, 마지막 비사용자 결정이 창 안. decision_id 는 그 결정 행이다.
      마지막 결정 시각 ≥ since 는 "창 안에 비사용자 결정이 하나라도 있다" 와 같아서 결정 시각
      인덱스로 창부터 좁힌다.
    - 상태 SENT 이고 이 사용자의 알림이 cluster_dup 행뿐이며(오류 행은 전달이 아니다) 그 행이
      창 안. decision_id 는 null. 복원으로 붙은 피드 행은 전달로 치지 않는다 — 복원해도 남는다.
    """
    last = (
        select(
            Decision.item_id,
            Decision.created_at.label("dropped_at"),
            Decision.id.label("decision_id"),
        )
        .join(Item, Item.id == Decision.item_id)
        .where(Decision.stage != Stage.USER.value, Item.status.in_(DROPPED_STATUSES))
        .distinct(Decision.item_id)
        .order_by(Decision.item_id, Decision.created_at.desc(), Decision.id.desc())
    )
    if since is not None:
        recent = select(Decision.item_id).where(
            Decision.created_at >= since, Decision.stage != Stage.USER.value
        )
        last = last.where(Decision.item_id.in_(recent))
    if item_id is not None:
        last = last.where(Decision.item_id == item_id)
    dropped = last.subquery("last_decision")

    other = aliased(Notification)
    delivered = select(other.id).where(
        other.item_id == Notification.item_id,
        other.user_id == user_id,
        other.level != CLUSTER_DUP,
        other.error.is_(None),
    )
    clustered = (
        select(
            Notification.item_id,
            func.max(Notification.sent_at).label("dropped_at"),
            null().label("decision_id"),
        )
        .join(Item, Item.id == Notification.item_id)
        .where(
            Notification.user_id == user_id,
            Notification.level == CLUSTER_DUP,
            Item.status == ItemStatus.SENT.value,
            or_(~delivered.exists(), _restored(user_id)),
        )
        .group_by(Notification.item_id)
    )
    if since is not None:
        clustered = clustered.having(func.max(Notification.sent_at) >= since)
    if item_id is not None:
        clustered = clustered.where(Notification.item_id == item_id)
    return union_all(select(dropped), clustered).subquery("filtered")


async def filtered_total(session: AsyncSession, user_id: int, since: datetime) -> int:
    """계약 4.6 의 걸러진 항목 수 (`filtered_total`, 03 `filtered_count`)."""
    both = filtered_set(user_id, since=since)
    return (await session.execute(select(func.count()).select_from(both))).scalar_one()


async def collected_total(session: AsyncSession, since: datetime) -> int:
    stmt = select(func.count()).select_from(Item).where(Item.fetched_at >= since)
    return (await session.execute(stmt)).scalar_one()


# ---------- DroppedItem ----------


def classify(
    stage: str | None, details: dict[str, Any] | None, relevance: float | None, *, floor: float
) -> Gate:
    """마지막 비사용자 결정 → 관문 (계약 2 의 표). 결정이 없으면 cluster_dup 알림 행 항목이다.

    선별은 탈락시키지 않는다. screening 은 선별 오류 폐기이거나, 점수에서 떨어졌는데 relevance 가
    floor 미만인 표시용 분류다.
    """
    if stage is None:
        return Gate.CLUSTER_DUP
    reason = (details or {}).get("reason")
    if stage == Stage.RULE.value:
        return Gate.DEDUP if reason == "dup" else Gate.EXCLUDE
    if stage == Stage.TRIAGE.value:
        return Gate.SCREENING
    if stage == Stage.LLM.value:
        return Gate.JUDGMENT
    if reason == "stale":
        return Gate.STALE
    return Gate.SCREENING if relevance is not None and relevance < floor else Gate.SCORE


def _keywords(details: dict[str, Any] | None) -> list[str]:
    matched = (details or {}).get("matched")
    return [m for m in matched if isinstance(m, str)] if isinstance(matched, list) else []


def to_dropped(row: Row[Any], *, floor: float, threshold: float) -> DroppedItem:
    screening = screening_of(row.triage_details)
    relevance = screening.relevance if screening else None
    gate = classify(row.gate_stage, row.gate_details, relevance, floor=floor)
    return DroppedItem(
        id=str(row.id),
        title=row.title,
        url=row.url,
        source_id=row.source_id,
        source_name=source_display_name(row.source_id, row.source_config),
        source_type=row.source_type,
        dropped_gate=gate,
        dropped_at=row.dropped_at,
        relevance=relevance,
        kind=screening.kind if screening else None,
        topics=screening.topics if screening else [],
        reason=screening.reason if screening else None,
        score=score_rationale(row.score_details, threshold),
        matched_keywords=_keywords(row.gate_details) if gate is Gate.EXCLUDE else [],
        exploration_candidate=bool(row.exploration_candidate),
        restored=bool(row.restored),
    )


def _last_details(stage: Stage, *, passed_only: bool = False) -> Any:
    """Item 에 상관. 그 단계의 마지막 결정 details."""
    stmt = select(Decision.details).where(
        Decision.item_id == Item.id, Decision.stage == stage.value
    )
    if passed_only:
        stmt = stmt.where(Decision.passed.is_(True))
    return (
        stmt.order_by(Decision.created_at.desc(), Decision.id.desc())
        .limit(1)
        .correlate(Item)
        .scalar_subquery()
    )


async def load_dropped(
    session: AsyncSession,
    user_id: int,
    since: datetime,
    *,
    now: datetime,
    floor: float,
    threshold: float,
) -> list[DroppedItem]:
    """창 안의 걸러진 항목 전부, dropped_at 내림차순(같으면 id 내림차순).

    그룹·요약 통계가 전체를 봐야 하므로 한 번에 읽어 파이썬에서 나눈다 (하루 수백 건 규모).
    """
    flt = filtered_set(user_id, since=since)
    gate = aliased(Decision)
    stmt = (
        select(
            Item.id,
            Item.title,
            Item.url,
            Source.name.label("source_id"),
            Source.type.label("source_type"),
            Source.config.label("source_config"),
            flt.c.dropped_at,
            gate.stage.label("gate_stage"),
            gate.details.label("gate_details"),
            _last_details(Stage.TRIAGE, passed_only=True).label("triage_details"),
            _last_details(Stage.SCORE).label("score_details"),
            explore_candidate(threshold, now).label("exploration_candidate"),
            _restored(user_id).label("restored"),
        )
        .select_from(flt)
        .join(Item, Item.id == flt.c.item_id)
        .join(Source, Source.id == Item.source_id)
        .outerjoin(gate, gate.id == flt.c.decision_id)
        .order_by(flt.c.dropped_at.desc(), Item.id.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [to_dropped(r, floor=floor, threshold=threshold) for r in rows]


# ---------- 요약 · 그룹 · 목록 ----------


def gate_counts(items: Sequence[DroppedItem]) -> dict[Gate, int]:
    counts = dict.fromkeys(Gate, 0)
    for it in items:
        counts[it.dropped_gate] += 1
    return counts


def borderline_range(threshold: float) -> tuple[float, float]:
    """탐색 슬롯 후보 폭과 같다. 0.45 − 0.10 이 0.35000000000000003 이 되지 않게 자른다."""
    return round(threshold - EXPLORE_BAND, 6), threshold


def summarize(
    items: Sequence[DroppedItem], *, hours: int, collected: int, threshold: float
) -> FilteredSummary:
    return FilteredSummary(
        window_hours=hours,
        filtered_total=len(items),
        collected_total=collected,
        gate_counts=gate_counts(items),
        borderline=Borderline(
            count=sum(it.exploration_candidate for it in items),
            range=borderline_range(threshold),
        ),
        unclassified_count=sum(it.kind is None for it in items),
    )


def group_key(item: DroppedItem, view: FilteredView) -> str:
    if view is FilteredView.SOURCE:
        return item.source_id
    if view is FilteredView.KIND:
        return item.kind.value if item.kind else UNCLASSIFIED
    return item.dropped_gate.value


def _low_relevance_ratio(items: Sequence[DroppedItem], floor: float) -> float | None:
    rated = [it.relevance for it in items if it.relevance is not None]
    if not rated:
        return None
    return sum(r < floor for r in rated) / len(rated)


def _group(
    key: str,
    items: list[DroppedItem],
    view: FilteredView,
    *,
    floor: float,
    kind_weights: dict[Kind, float],
    feedback: dict[Kind, KindFeedback],
) -> FilteredGroup:
    first = items[0]
    kind = first.kind if view is FilteredView.KIND else None
    weight = kind_weights.get(kind, 0.0) if kind else None
    return FilteredGroup(
        key=key,
        count=len(items),
        gate_counts=gate_counts(items),
        source=(
            GroupSource(id=first.source_id, display_name=first.source_name, type=first.source_type)
            if view is FilteredView.SOURCE
            else None
        ),
        kind=kind,
        gate=first.dropped_gate if view is FilteredView.GATE else None,
        low_relevance_ratio=_low_relevance_ratio(items, floor),
        kind_weight=weight,
        kind_feedback=feedback.get(kind) if kind else None,
        penalty_active=weight is not None and weight < 0,
        borderline_count=sum(it.exploration_candidate for it in items),
        exclude_keyword_hits=sum(bool(it.matched_keywords) for it in items),
        preview=items[:PREVIEW_SIZE],
    )


def _sort_key(group: FilteredGroup, view: FilteredView, sort: GroupSort) -> tuple[Any, ...]:
    """kind 보기의 unclassified 는 정렬과 무관하게 항상 마지막이다."""
    name = (group.source.display_name if group.source else group.key).casefold()
    last = view is FilteredView.KIND and group.kind is None
    return (last, -group.count, name) if sort is GroupSort.COUNT_DESC else (last, name)


def build_groups(
    items: Sequence[DroppedItem],
    view: FilteredView,
    sort: GroupSort,
    *,
    floor: float,
    kind_weights: dict[Kind, float],
    feedback: dict[Kind, KindFeedback],
) -> list[FilteredGroup]:
    """items 는 dropped_at 내림차순이라 그룹 안 순서도 그렇다. preview 는 앞 3건."""
    by_key: dict[str, list[DroppedItem]] = {}
    for it in items:
        by_key.setdefault(group_key(it, view), []).append(it)
    groups = [
        _group(k, v, view, floor=floor, kind_weights=kind_weights, feedback=feedback)
        for k, v in by_key.items()
    ]
    return sorted(groups, key=lambda g: _sort_key(g, view, sort))


def _after(key: dict[str, Any]) -> tuple[datetime, int]:
    """목록 커서 = 직전 페이지 마지막 항목의 (dropped_at, id)."""
    try:
        dropped_at, item_id = datetime.fromisoformat(key["t"]), int(key["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.") from exc
    # 시간대 없는 시각은 DB 의 UTC 시각과 비교할 수 없다.
    if dropped_at.tzinfo is None:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.")
    return dropped_at, item_id


def page_items(
    items: Sequence[DroppedItem], view: FilteredView, key: str, page: PageParams
) -> tuple[list[DroppedItem], str | None]:
    """그룹 하나의 항목을 dropped_at 내림차순(같으면 id 내림차순) 커서로 자른다."""
    rows = [it for it in items if group_key(it, view) == key]
    if page.after is not None:
        after = _after(page.after)
        rows = [it for it in rows if (it.dropped_at, int(it.id)) < after]
    return paginate(rows, page.limit, lambda it: {"t": it.dropped_at.isoformat(), "id": int(it.id)})


async def kind_feedback(
    session: AsyncSession, user_id: int, now: datetime
) -> dict[Kind, KindFeedback]:
    """최근 30일 판정(👍/👎)을 그 항목의 마지막 선별 kind 별로 센다. 판정이 없는 kind 는 빠진다."""
    since = now - timedelta(days=KIND_FEEDBACK_DAYS)
    judged = (
        Feedback.user_id == user_id,
        Feedback.verdict.in_(list(VERDICT_TO_FEEDBACK)),
        Feedback.created_at >= since,
    )
    triage = (
        select(Decision.item_id, Decision.details["kind"].astext.label("kind"))
        .where(
            Decision.stage == Stage.TRIAGE.value,
            Decision.passed.is_(True),
            Decision.item_id.in_(select(Feedback.item_id).where(*judged)),
        )
        .distinct(Decision.item_id)
        .order_by(Decision.item_id, Decision.created_at.desc(), Decision.id.desc())
        .subquery("triage")
    )
    stmt = (
        select(
            triage.c.kind,
            func.count().filter(Feedback.verdict == "useless").label("not_useful"),
            func.count().label("total"),
        )
        .join(Feedback, Feedback.item_id == triage.c.item_id)
        .where(*judged)
        .group_by(triage.c.kind)
    )
    return {
        Kind(r.kind): KindFeedback(not_useful=r.not_useful, total=r.total)
        for r in (await session.execute(stmt)).all()
        if r.kind in Kind
    }


# ---------- 복원 ----------


async def _lock_filtered(session: AsyncSession, user_id: int, item_id: int) -> bool:
    """항목 행을 잠그고(동시 복원이 행을 두 번 넣지 않게) 이 사용자의 걸러진 항목인지 본다.

    복원은 창과 무관하다 — 창이 지난 항목도 걸러진 항목이면 복원·취소할 수 있다.
    """
    await session.execute(select(Item.id).where(Item.id == item_id).with_for_update())
    flt = filtered_set(user_id, item_id=item_id)
    restored = select(_restored(user_id)).select_from(Item).where(Item.id == item_id)
    if not await session.scalar(select(select(flt.c.item_id).exists())):
        raise ApiError(404, "not_found", "걸러진 항목이 아닙니다.", {"item_id": str(item_id)})
    return bool(await session.scalar(restored))


async def restore(session: AsyncSession, user_id: int, item_id: int) -> None:
    """👍 복원 — 판정 useful(app) + 사용자 결정 + 피드 행. 어느 채널로도 보내지 않는다.

    커밋은 요청 세션이 한 번에 한다. 이미 복원한 항목은 아무것도 바꾸지 않는다.
    항목 상태는 그대로 두므로 발송 잡이 집지 않고, 마지막 결정이 user 라 탐색 후보도 아니다.
    """
    if await _lock_filtered(session, user_id, item_id):
        return
    await set_app_feedback(session, user_id, item_id, "useful")
    session.add_all(
        [
            Decision(
                item_id=item_id,
                stage=Stage.USER.value,
                passed=True,
                details={"reason": RESTORE_REASON, "user_id": user_id},
            ),
            Notification(
                user_id=user_id, item_id=item_id, channel=APP_CHANNEL, level=Level.FEED.value
            ),
        ]
    )
    await session.flush()


async def unrestore(session: AsyncSession, user_id: int, item_id: int) -> None:
    """복원 취소 — 피드 행·사용자 결정을 지우고 판정은 cleared. 복원한 적 없으면 그대로 둔다."""
    if not await _lock_filtered(session, user_id, item_id):
        return
    await session.execute(
        delete(Decision).where(
            Decision.item_id == item_id,
            Decision.stage == Stage.USER.value,
            Decision.details.contains({"user_id": user_id}),
        )
    )
    # 걸러진 항목의 app·feed 행은 복원만 만든다. 발송 잡이 피드 행을 남긴 항목은 전달된 것이라
    # 걸러진 집합에 없다.
    await session.execute(
        delete(Notification).where(
            Notification.user_id == user_id,
            Notification.item_id == item_id,
            Notification.channel == APP_CHANNEL,
            Notification.level == Level.FEED.value,
        )
    )
    await clear_feedback(session, user_id, item_id)
