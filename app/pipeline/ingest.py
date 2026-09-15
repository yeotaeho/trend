# 적재 — url_hash 기준 INSERT. 아는 URL 은 raw 를 병합하고 점수 탈락 항목은 되살린다

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ScoringConfig, get_rules
from app.db.models import Decision, Item, Source
from app.log import get_logger
from app.pipeline.normalize import normalize_url, url_hash
from app.pipeline.scoring import freshness, is_stale, revive_gain, score_terms
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
    if not mentions:
        return {**existing, "metrics": metrics}, True
    return {**existing, "metrics": metrics, "mentions": sorted(mentions)}, True


def is_same_source(row_source_id: int, source_id: int, families: dict[int, str | None]) -> bool:
    """같은 소스이거나 같은 family(sources.yaml config.family)면 멘션으로 세지 않는다."""
    if row_source_id == source_id:
        return True
    family = families.get(row_source_id)
    return family is not None and family == families.get(source_id)


async def _last_score_fail(
    session: AsyncSession, item_id: int
) -> tuple[float, dict[str, object]] | None:
    """마지막 결정이 점수 탈락이면 (그 점수, details), 아니면 None.

    판정 false·중복·exclude·선별 폐기는 되살리지 않는다. details 는 되살림 이득의 기준
    (breakdown 의 hot·multi) 을 찾는 데 쓴다.
    """
    stmt = (
        select(Decision.stage, Decision.passed, Decision.score, Decision.details)
        .where(Decision.item_id == item_id)
        .order_by(Decision.created_at.desc(), Decision.id.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    stage, passed, score, details = row
    if stage == Stage.SCORE.value and not passed and score is not None:
        return float(score), details if isinstance(details, dict) else {}
    return None


def _metrics(raw: dict[str, object]) -> dict[str, float]:
    """raw 의 metrics 딕셔너리, 없거나 dict 가 아니면 빈 딕셔너리."""
    metrics = raw.get("metrics")
    return metrics if isinstance(metrics, dict) else {}


def _mention_len(raw: dict[str, object]) -> int:
    """raw 의 mentions 목록 길이, 없거나 list 가 아니면 0."""
    mentions = raw.get("mentions")
    return len(mentions) if isinstance(mentions, list) else 0


def _base_terms(
    cfg: ScoringConfig,
    details: dict[str, object],
    existing_raw: dict[str, object],
    published_at: datetime,
) -> tuple[float, float, float]:
    """되살림 이득의 기준.

    마지막 점수 결정의 breakdown 이 있으면 그 hot·multi·fresh, 없으면 직전 관측의 hot·multi 와
    지금 기준 fresh(기록된 결정 항이 없으니 감쇠분은 0 으로 둔다).
    """
    breakdown = details.get("breakdown")
    if isinstance(breakdown, dict):
        hot, multi, fresh = breakdown.get("hot"), breakdown.get("multi"), breakdown.get("fresh")
        if (
            isinstance(hot, int | float)
            and isinstance(multi, int | float)
            and isinstance(fresh, int | float)
        ):
            return float(hot), float(multi), float(fresh)
    return (
        *score_terms(cfg, _metrics(existing_raw), _mention_len(existing_raw)),
        cfg.w_fresh * freshness(published_at),
    )


async def store_items(
    session: AsyncSession, source_id: int, items: list[NormalizedItem]
) -> list[int]:
    """새로 INSERT 된 항목의 id 만 돌려준다 (임베딩 대상).

    이미 아는 URL 은 버리지 않고 raw 를 병합한다. 값이 바뀌었고 72h 안인 점수 탈락 항목은
    마지막 점수 + hot·multi 변화량이 임계값 이상이면 NEW 로 되돌린다. 선별 결과는 decisions
    캐시라 다시 호출하지 않고 점수만 새 metrics·mentions 로 다시 매긴다.
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

    # 파이프라인(_claim_batch)이 같은 행을 FOR UPDATE 로 잡고 LLM 호출 내내 들고 있을 수 있다.
    # 잠긴 행은 SKIP LOCKED 로 건너뛴다. 병합은 다음 폴링으로 미루고, INSERT 는 충돌로 no-op 된다.
    known = {
        row.url_hash: row
        for row in (
            await session.execute(
                select(Item)
                .where(Item.url_hash.in_(list(by_hash)))
                .with_for_update(skip_locked=True)
            )
        ).scalars()
    }
    rules = get_rules()
    max_age = rules.scoring.max_age_hours
    # known 이 비어 있지 않을 때만 소스 family 를 한 번에 조회한다. 같은 family(예: arXiv 두
    # 피드)는 교차 등재로 인한 관측이라 서로 멘션으로 세지 않는다.
    families: dict[int, str | None] = {}
    if known:
        ids = {row.source_id for row in known.values()} | {source_id}
        rows = await session.execute(select(Source.id, Source.config).where(Source.id.in_(ids)))
        for sid, config in rows:
            family = config.get("family") if isinstance(config, dict) else None
            families[sid] = family if isinstance(family, str) else None
    merged = revived = 0
    for hash_, row in known.items():
        item = by_hash[hash_]
        existing_raw = row.raw if isinstance(row.raw, dict) else {}
        raw, changed = merge_raw(
            existing_raw,
            item,
            same_source=is_same_source(row.source_id, source_id, families),
        )
        if not changed:
            continue
        row.raw = raw
        merged += 1
        if row.status == ItemStatus.DROPPED.value and not is_stale(row.published_at, max_age):
            last = await _last_score_fail(session, row.id)
            if last is not None:
                last_score, details = last
                base_hot, base_multi, base_fresh = _base_terms(
                    rules.scoring, details, existing_raw, row.published_at
                )
                gain = revive_gain(
                    rules.scoring,
                    _metrics(raw),
                    _mention_len(raw),
                    row.published_at,
                    base_hot=base_hot,
                    base_multi=base_multi,
                    base_fresh=base_fresh,
                )
                # 부동소수 합이 0.4499999 로 떨어지지 않게 소수 6자리에서 비교한다
                # (score_item 과 같은 규칙).
                if round(last_score + gain, 6) >= rules.scoring.threshold:
                    row.status = ItemStatus.NEW.value
                    revived += 1
                    log.info(
                        "ingest.revived",
                        item_id=row.id,
                        source=item.source,
                        last_score=last_score,
                        gain=round(gain, 4),
                        base_hot=round(base_hot, 4),
                        base_multi=round(base_multi, 4),
                        base_fresh=round(base_fresh, 4),
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
