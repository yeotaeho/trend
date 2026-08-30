# 중복 제거 — url_hash 는 DB unique 제약이 막고, 여기서는 72시간 내 제목 유사도(pg_trgm)

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item

WINDOW_HOURS = 72
SIMILARITY_THRESHOLD = 0.6


async def find_cluster(session: AsyncSession, title: str, *, exclude_item_id: int) -> int | None:
    """최근 72시간 안에 제목이 충분히 비슷한 항목이 있으면 그 클러스터 id 를 돌려준다."""
    since = datetime.now(UTC) - timedelta(hours=WINDOW_HOURS)
    similarity = func.similarity(Item.title, title)
    stmt = (
        select(func.coalesce(Item.cluster_id, Item.id))
        .where(
            Item.id != exclude_item_id,
            Item.published_at >= since,
            similarity > SIMILARITY_THRESHOLD,
        )
        .order_by(similarity.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def mention_count(session: AsyncSession, item_id: int) -> int:
    """이 항목을 대표로 삼는 중복들 + 자기 자신 = 여러 소스에 등장한 횟수."""
    stmt = select(func.count()).select_from(Item).where(Item.cluster_id == item_id)
    return (await session.execute(stmt)).scalar_one() + 1
