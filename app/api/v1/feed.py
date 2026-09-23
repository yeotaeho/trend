# 화면 03 피드 — GET /stats/today, GET /feed

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.v1.deps import Session, UserId
from app.api.v1.pagination import Paging
from app.api.v1.queries.feed import feed_page, today_stats
from app.api.v1.schemas.alerts import Alert
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.feed import FeedFilter, TodayStats
from app.config import get_rules

router = APIRouter()


@router.get("/stats/today")
async def get_today_stats(session: Session, user_id: UserId) -> TodayStats:
    return await today_stats(session, user_id, get_rules().notify, datetime.now(UTC))


@router.get("/feed")
async def get_feed(
    session: Session,
    user_id: UserId,
    paging: Paging,
    flt: Annotated[FeedFilter, Query(alias="filter")] = FeedFilter.ALL,
) -> Page[Alert]:
    items, next_cursor = await feed_page(session, user_id, flt, paging)
    return Page[Alert](items=items, next_cursor=next_cursor)
