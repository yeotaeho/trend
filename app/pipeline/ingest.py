# 적재 — url_hash 기준 INSERT. 아는 URL 은 raw 를 병합하고 점수 탈락 항목은 되살린다

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_rules
from app.db.models import Decision, Item
from app.log import get_logger
from app.pipeline.normalize import normalize_url, url_hash
from app.pipeline.scoring import is_stale
from app.schemas import Category, ItemStatus, NormalizedItem, Stage

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


def merge_raw(
    existing: dict[str, object], item: NormalizedItem, *, same_source: bool
) -> tuple[dict[str, object], bool]:
    """같은 URL 의 재관측을 기존 raw 에 합친다. (새 raw, 바뀌었는지).

    metrics 는 키별 max, mentions 는 자기 소스를 뺀 소스 이름의 정렬 목록. 바뀐 게 없으면
    existing 을 그대로 돌려준다. 같은 값의 재관측(HN 이 10분마다 같은 프론트 페이지를 줄 때)이
    되살림을 일으키지 않아야 하기 때문이다.
    """
    old_metrics = existing.get("metrics")
    old_m: dict[str, float] = dict(old_metrics) if isinstance(old_metrics, dict) else {}
    metrics = dict(old_m)
    for key, value in item.metrics.items():
        if key not in metrics or value > float(metrics[key]):
            metrics[key] = value

    old_mentions = existing.get("mentions")
    old_s: set[str] = set(old_mentions) if isinstance(old_mentions, list) else set()
    mentions = set(old_s)
    if not same_source:
        mentions.add(item.source)

    if metrics == old_m and mentions == old_s:
        return existing, False
    return {**existing, "metrics": metrics, "mentions": sorted(mentions)}, True


async def _last_decision_is_score_fail(session: AsyncSession, item_id: int) -> bool:
    """되살림은 점수에서만 떨어진 항목에 한한다. 판정 false·중복·exclude·선별 폐기는 그대로 둔다."""
    stmt = (
        select(Decision.stage, Decision.passed)
        .where(Decision.item_id == item_id)
        .order_by(Decision.created_at.desc(), Decision.id.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return False
    stage, passed = row
    return stage == Stage.SCORE.value and not passed


async def store_items(
    session: AsyncSession, source_id: int, items: list[NormalizedItem]
) -> list[int]:
    """새로 INSERT 된 항목의 id 만 돌려준다 (임베딩 대상).

    이미 아는 URL 은 버리지 않고 raw 를 병합한다. 값이 바뀌었고 점수에서 떨어졌던 항목이
    72h 안이면 NEW 로 되돌린다. 선별 결과는 decisions 캐시라 다시 호출하지 않고
    점수만 새 metrics·mentions 로 다시 매긴다.
    """
    accepted = [item for item in items if is_web_url(item.url)]
    if len(accepted) != len(items):
        log.warning("ingest.rejected_url", source_id=source_id, count=len(items) - len(accepted))
    if not accepted:
        return []

    # 같은 배치 안의 중복은 첫 관측만 쓴다. ON CONFLICT 가 한 문장에서 두 번 터지지 않아야 한다.
    by_hash: dict[str, NormalizedItem] = {}
    for item in accepted:
        by_hash.setdefault(url_hash(normalize_url(item.url)), item)

    known = {
        row.url_hash: row
        for row in (
            await session.execute(select(Item).where(Item.url_hash.in_(list(by_hash))))
        ).scalars()
    }
    max_age = get_rules().scoring.max_age_hours
    merged = revived = 0
    for hash_, row in known.items():
        item = by_hash[hash_]
        raw, changed = merge_raw(
            row.raw if isinstance(row.raw, dict) else {},
            item,
            same_source=row.source_id == source_id,
        )
        if not changed:
            continue
        row.raw = raw
        merged += 1
        if (
            row.status == ItemStatus.DROPPED.value
            and not is_stale(row.published_at, max_age)
            and await _last_decision_is_score_fail(session, row.id)
        ):
            row.status = ItemStatus.NEW.value
            revived += 1
            log.info(
                "ingest.revived",
                item_id=row.id,
                source=item.source,
                mentions=raw.get("mentions"),
                metrics=raw.get("metrics"),
            )
    if merged:
        log.info("ingest.merged", source_id=source_id, merged=merged, revived=revived)

    new_rows = [to_row(source_id, item) for hash_, item in by_hash.items() if hash_ not in known]
    if not new_rows:
        return []
    # 웹훅 경로와의 경쟁은 여전히 유니크 제약이 막는다.
    stmt = (
        insert(Item)
        .values(new_rows)
        .on_conflict_do_nothing(index_elements=["url_hash"])
        .returning(Item.id)
    )
    return list((await session.execute(stmt)).scalars())
