# 중복 제거 — url_hash 는 DB unique 제약이 막고, 여기서는 72시간 내 제목 유사도(pg_trgm)

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item
from app.schemas import ItemStatus

WINDOW_HOURS = 72
SIMILARITY_THRESHOLD = 0.6

# 중복 "알림"의 기준은 실제로 알림이 나갔거나 나갈 항목뿐이다.
# - DROPPED·FILTERED_OUT·FAILED: 사용자가 못 받았다. 기준으로 삼으면 같은 이슈의 재등장이
#   영영 전달되지 않는다.
# - NEW: 아직 판정 전이라 기준이 될 수 없다. 규칙에서 떨어질 A 가 기준이 되면, 자기 힘으로
#   통과할 B(화이트리스트 릴리즈 등)가 먼저 처리되다 dup 으로 죽는다. 다중 소스 신호는
#   cluster_id 대신 mention_count 가 점수화 시점에 직접 센다.
_SURVIVED = (ItemStatus.SCORED.value, ItemStatus.QUEUED.value, ItemStatus.SENT.value)


def _similar_within_window(
    title: str, *, exclude_item_id: int
) -> tuple[ColumnElement[float], list[ColumnElement[bool]]]:
    since = datetime.now(UTC) - timedelta(hours=WINDOW_HOURS)
    similarity = func.similarity(Item.title, title)
    return (
        similarity,
        [
            Item.id != exclude_item_id,
            Item.published_at >= since,
            similarity > SIMILARITY_THRESHOLD,
        ],
    )


async def find_cluster(session: AsyncSession, title: str, *, exclude_item_id: int) -> int | None:
    """알림이 나갔거나 나갈 항목 중 제목이 충분히 비슷한 것이 있으면 그 클러스터 id."""
    similarity, conds = _similar_within_window(title, exclude_item_id=exclude_item_id)
    stmt = (
        select(func.coalesce(Item.cluster_id, Item.id))
        .where(*conds, Item.status.in_(_SURVIVED))
        .order_by(similarity.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def mention_count(
    session: AsyncSession, title: str, *, exclude_item_id: int, source_id: int
) -> int:
    """72시간 안에 같은 이슈를 올린 서로 다른 소스 수 (자기 소스 포함).

    상태를 가리지 않는다. 다른 소스에서 떨어졌더라도 "여러 곳에 떴다"는 사실은 남는다.
    처리 순서와 무관하게 점수화 시점에 직접 세므로 cluster_id 연결에 의존하지 않는다.
    """
    _, conds = _similar_within_window(title, exclude_item_id=exclude_item_id)
    stmt = (
        select(func.count(func.distinct(Item.source_id)))
        .select_from(Item)
        .where(*conds, Item.source_id != source_id)
    )
    return (await session.execute(stmt)).scalar_one() + 1
