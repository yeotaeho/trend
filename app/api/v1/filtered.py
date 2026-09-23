# 화면 09·10 걸러진 항목 — 요약·그룹·목록·복원 (B8)

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.v1.alerts import existing_item_id
from app.api.v1.deps import Session, UserId
from app.api.v1.pagination import Paging
from app.api.v1.queries import filtered as queries
from app.api.v1.queries.alerts import alert_select, build_alerts, first_delivery
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.filtered import (
    DroppedItem,
    FilteredGroups,
    FilteredSummary,
    FilteredView,
    GroupSort,
    RestoreOut,
)
from app.config import get_app_config, get_rules
from app.db.models import Item

router = APIRouter(prefix="/filtered")

Hours = Annotated[int, Query(ge=1, le=queries.MAX_WINDOW_HOURS)]


async def _window(session: Session, user_id: int, hours: int, now: datetime) -> list[DroppedItem]:
    return await queries.load_dropped(
        session,
        user_id,
        now - timedelta(hours=hours),
        now=now,
        floor=get_app_config().screening_relevance_floor,
        threshold=get_rules().scoring.threshold,
    )


@router.get("/summary")
async def get_summary(
    session: Session, user_id: UserId, hours: Hours = queries.WINDOW_HOURS
) -> FilteredSummary:
    now = datetime.now(UTC)
    items = await _window(session, user_id, hours, now)
    return queries.summarize(
        items,
        hours=hours,
        collected=await queries.collected_total(session, now - timedelta(hours=hours)),
        threshold=get_rules().scoring.threshold,
    )


@router.get("/groups")
async def get_groups(
    session: Session,
    user_id: UserId,
    view: FilteredView = FilteredView.SOURCE,
    sort: GroupSort = GroupSort.COUNT_DESC,
    hours: Hours = queries.WINDOW_HOURS,
) -> FilteredGroups:
    now = datetime.now(UTC)
    items = await _window(session, user_id, hours, now)
    feedback = (
        await queries.kind_feedback(session, user_id, now) if view is FilteredView.KIND else {}
    )
    groups = queries.build_groups(
        items,
        view,
        sort,
        floor=get_app_config().screening_relevance_floor,
        kind_weights=get_rules().scoring.kind_weights,
        feedback=feedback,
    )
    return FilteredGroups(view=view, groups=groups)


@router.get("/items")
async def get_items(
    session: Session,
    user_id: UserId,
    paging: Paging,
    view: FilteredView,
    key: str,
    hours: Hours = queries.WINDOW_HOURS,
) -> Page[DroppedItem]:
    items = await _window(session, user_id, hours, datetime.now(UTC))
    page, next_cursor = queries.page_items(items, view, key, paging)
    return Page[DroppedItem](items=page, next_cursor=next_cursor)


@router.post("/items/{item_id}/restore")
async def post_restore(item_id: str, session: Session, user_id: UserId) -> RestoreOut:
    """이미 복원한 항목도 같은 응답. 걸러진 항목이 아니면 404."""
    iid = await existing_item_id(session, item_id)
    await queries.restore(session, user_id, iid)
    stmt = alert_select(user_id, first_delivery(user_id), delivered_only=False).where(
        Item.id == iid
    )
    [alert] = await build_alerts(session, (await session.execute(stmt)).all())
    return RestoreOut(item_id=str(iid), restored=True, alert=alert)


@router.delete("/items/{item_id}/restore", status_code=204)
async def delete_restore(item_id: str, session: Session, user_id: UserId) -> Response:
    """복원한 적 없는 걸러진 항목도 204. 걸러진 항목이 아니면 404."""
    iid = await existing_item_id(session, item_id)
    await queries.unrestore(session, user_id, iid)
    return Response(status_code=204)
