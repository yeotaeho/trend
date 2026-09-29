# 화면 03·07 알림 상세·판정 — GET /alerts/{id}, 피드백 PUT·DELETE, GET /feedback/recent

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response
from sqlalchemy import select

from app.api.v1.deps import Session, UserId
from app.api.v1.errors import ApiError
from app.api.v1.queries.alerts import (
    FEEDBACK_TO_VERDICT,
    INT4_MAX,
    alert_select,
    build_alerts,
    first_delivery,
    rationale_for,
    recent_feedback,
)
from app.api.v1.schemas.alerts import AlertDetail, FeedbackIn, FeedbackOut, RecentFeedback
from app.config import get_rules
from app.db.budget import today_start
from app.db.feedback import clear_feedback, set_app_feedback
from app.db.models import Item

router = APIRouter()

RECENT_DEFAULT = 5
RECENT_MAX = 20


async def existing_item_id(session: Session, alert_id: str) -> int:
    """alert_id 는 items.id 문자열이다. 숫자가 아니거나 없는 항목은 404."""
    # isdecimal 은 전각 숫자도 받는다. ASCII 숫자만 ID 다.
    item_id = int(alert_id) if alert_id.isascii() and alert_id.isdecimal() else 0
    exists = 0 < item_id <= INT4_MAX and await session.scalar(
        select(Item.id).where(Item.id == item_id)
    )
    if not exists:
        raise ApiError(404, "not_found", "알림을 찾을 수 없습니다.", {"alert_id": alert_id})
    return item_id


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str, session: Session, user_id: UserId) -> AlertDetail:
    """발송된 적 없는 항목도 조회된다 (delivered_at·delivery_mode 가 null)."""
    item_id = await existing_item_id(session, alert_id)
    stmt = alert_select(user_id, first_delivery(user_id), delivered_only=False).where(
        Item.id == item_id
    )
    [alert] = await build_alerts(session, (await session.execute(stmt)).all())
    rationale = await rationale_for(
        session,
        alert,
        item_id=item_id,
        user_id=user_id,
        threshold=get_rules().scoring.threshold,
    )
    return AlertDetail(**alert.model_dump(), rationale=rationale)


@router.put("/alerts/{alert_id}/feedback")
async def put_feedback(
    alert_id: str, body: FeedbackIn, session: Session, user_id: UserId
) -> FeedbackOut:
    """앱 판정은 리액션 폴링이 덮어쓰지 않는다. 걸러진 항목에도 쓸 수 있다."""
    item_id = await existing_item_id(session, alert_id)
    updated_at = await set_app_feedback(
        session, user_id, item_id, FEEDBACK_TO_VERDICT[body.verdict]
    )
    return FeedbackOut(alert_id=str(item_id), feedback=body.verdict, updated_at=updated_at)


@router.delete("/alerts/{alert_id}/feedback", status_code=204)
async def delete_feedback(alert_id: str, session: Session, user_id: UserId) -> Response:
    """판정이 없어도 204. 행은 cleared 로 남아 리액션 폴링이 되살리지 못한다."""
    item_id = await existing_item_id(session, alert_id)
    await clear_feedback(session, user_id, item_id)
    return Response(status_code=204)


@router.get("/feedback/recent")
async def get_recent_feedback(
    session: Session,
    user_id: UserId,
    limit: Annotated[int, Query(ge=1, le=RECENT_MAX)] = RECENT_DEFAULT,
) -> RecentFeedback:
    tz = get_rules().notify.timezone
    today = today_start(tz, datetime.now(UTC))
    return await recent_feedback(session, user_id, limit=limit, today=today)
