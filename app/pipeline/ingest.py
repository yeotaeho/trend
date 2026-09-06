# 적재 — 정규화 항목을 url_hash 기준으로 중복 없이 INSERT (같은 해시면 조용히 스킵)

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item
from app.log import get_logger
from app.pipeline.normalize import normalize_url, url_hash
from app.schemas import Category, ItemStatus, NormalizedItem

SUMMARY_LIMIT = 3000
log = get_logger(__name__)


def is_web_url(url: str) -> bool:
    """피드가 주는 링크는 신뢰할 수 없다. javascript:·data: 같은 스킴은 여기서 막는다.

    모든 수집 경로(RSS·GitHub 폴링·웹훅)가 store_items 를 지나므로 이 한 곳이면 된다.
    발송 버튼과 본문 보강이 이 URL 을 그대로 쓴다.
    """
    return url.startswith(("http://", "https://"))


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
    accepted = [item for item in items if is_web_url(item.url)]
    if len(accepted) != len(items):
        log.warning("ingest.rejected_url", source_id=source_id, count=len(items) - len(accepted))
    if not accepted:
        return []
    rows = [to_row(source_id, item) for item in accepted]
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
