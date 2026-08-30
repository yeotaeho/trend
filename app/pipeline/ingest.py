# 적재 — 정규화 항목을 url_hash 기준으로 중복 없이 INSERT (같은 해시면 조용히 스킵)

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item
from app.pipeline.normalize import normalize_url, url_hash
from app.schemas import Category, ItemStatus, NormalizedItem

SUMMARY_LIMIT = 3000


def to_row(source_id: int, item: NormalizedItem) -> dict[str, object]:
    normalized = normalize_url(item.url)
    return {
        "source_id": source_id,
        "external_id": item.external_id,
        "url": item.url,
        "url_normalized": normalized,
        "url_hash": url_hash(normalized),
        "title": item.title,
        "summary_raw": (item.body or "")[:SUMMARY_LIMIT] or None,
        "author": item.author,
        "published_at": item.published_at,
        "category": (item.category_hint or Category.UNKNOWN).value,
        "status": ItemStatus.NEW.value,
        "raw": {**item.raw, "metrics": item.metrics, "source": item.source},
    }


async def store_items(
    session: AsyncSession, source_id: int, items: list[NormalizedItem]
) -> list[int]:
    """새로 들어간 항목의 id 목록을 돌려준다. 이미 있던 항목은 비어 있는 결과가 된다."""
    if not items:
        return []
    rows = [to_row(source_id, item) for item in items]
    # 같은 배치 안의 중복도 미리 걸러야 ON CONFLICT 가 한 문장에서 두 번 터지지 않는다.
    unique: dict[str, dict[str, object]] = {}
    for row in rows:
        unique.setdefault(str(row["url_hash"]), row)

    stmt = (
        insert(Item)
        .values(list(unique.values()))
        .on_conflict_do_nothing(index_elements=["url_hash"])
        .returning(Item.id)
    )
    return list((await session.execute(stmt)).scalars())
