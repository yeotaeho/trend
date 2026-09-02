# 중복 제거 — url_hash 는 DB unique 제약이 막고, 여기서는 72시간 내 제목 유사도(pg_trgm)

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item
from app.schemas import ItemStatus

WINDOW_HOURS = 72
SIMILARITY_THRESHOLD = 0.6
# 알림된 적 없는 항목은 중복 "알림"의 기준이 될 수 없다. 점수·규칙에서 떨어졌거나
# 발송이 3회 실패로 종결된 항목을 기준으로 삼으면, 같은 이슈가 다른 소스에서 새로
# 들어와도 dup 으로 죽어 사용자가 영영 못 듣는다.
# NEW 는 남긴다. 아직 판정 전인 대표에 중복이 묶여야 mention_count 가 오르고,
# 대표를 점수화할 때 다중 소스 boost 를 받는다(구현도 5.2). 대표가 나중에 떨어지면
# 그 뒤 재등장은 위 규칙으로 살아난다.
_NEVER_NOTIFIED = (
    ItemStatus.DROPPED.value,
    ItemStatus.FILTERED_OUT.value,
    ItemStatus.FAILED.value,
)


async def find_cluster(session: AsyncSession, title: str, *, exclude_item_id: int) -> int | None:
    """최근 72시간 안에 제목이 충분히 비슷한 항목이 있으면 그 클러스터 id 를 돌려준다."""
    since = datetime.now(UTC) - timedelta(hours=WINDOW_HOURS)
    similarity = func.similarity(Item.title, title)
    stmt = (
        select(func.coalesce(Item.cluster_id, Item.id))
        .where(
            Item.id != exclude_item_id,
            Item.status.notin_(_NEVER_NOTIFIED),
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
