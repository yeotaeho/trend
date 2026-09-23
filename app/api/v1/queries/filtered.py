# 걸러진 항목 집계 — 창 안의 탈락 항목 + 클러스터 하루 상한 항목 (B8 이 관문·그룹으로 확장)

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.v1.queries.alerts import CLUSTER_DUP, USER_STAGE
from app.db.models import Decision, Item, Notification
from app.schemas import ItemStatus

WINDOW_HOURS = 24


async def filtered_total(session: AsyncSession, user_id: int, since: datetime) -> int:
    """계약 4.6 의 걸러진 항목 수 (`filtered_total`, 03 `filtered_count`).

    - DROPPED·FILTERED_OUT 이고 마지막 비사용자 결정이 창 안. 마지막 결정 시각 ≥ since 는
      "창 안에 비사용자 결정이 하나라도 있다" 와 같아서 결정 시각 인덱스로 창부터 좁힌다.
    - 이 사용자의 알림이 cluster_dup 행뿐이고(오류 행은 전달이 아니다) 그 행이 창 안 (상태 SENT).
    """
    dropped = (
        select(Decision.item_id)
        .join(Item, Item.id == Decision.item_id)
        .where(
            Decision.created_at >= since,
            Decision.stage != USER_STAGE,
            Item.status.in_([ItemStatus.DROPPED.value, ItemStatus.FILTERED_OUT.value]),
        )
    )
    other = aliased(Notification)
    non_cluster = select(other.id).where(
        other.item_id == Notification.item_id,
        other.user_id == user_id,
        other.level != CLUSTER_DUP,
        other.error.is_(None),
    )
    clustered = select(Notification.item_id).where(
        Notification.user_id == user_id,
        Notification.level == CLUSTER_DUP,
        Notification.sent_at >= since,
        ~non_cluster.exists(),
    )
    both = union(dropped, clustered).subquery()
    return (await session.execute(select(func.count()).select_from(both))).scalar_one()
