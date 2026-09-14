# 적재 병합·되살림 통합 테스트 — 같은 URL 의 재관측이 raw 를 합치고 점수 탈락만 NEW 로 되돌린다

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.config import get_rules
from app.db.models import Decision, Item, Source
from app.db.session import SessionLocal
from app.pipeline.ingest import store_items
from app.pipeline.normalize import normalize_url, url_hash
from app.pipeline.scoring import score_terms
from app.schemas import NormalizedItem

URL = "https://example.com/merge-test"


def observation(source: str, points: float) -> NormalizedItem:
    return NormalizedItem(
        source=source,
        external_id=f"{source}-1",
        url=URL,
        title="t",
        published_at=datetime.now(UTC),
        metrics={"points": points},
    )


async def _seed(
    status: str,
    last_stage: str,
    *,
    age_hours: int = 1,
    # 0.42 + revive_gain(10 → 50점) ≈ 0.42 + 0.049 ≥ 0.45.
    # 가중치를 바꾸면 score_terms 로 다시 계산한다.
    last_score: float = 0.42,
    family: str | None = None,
    points: float = 10.0,
) -> tuple[int, int, int]:
    """항목 하나를 소스 a 로 넣고 마지막 결정을 심는다. (item_id, source_a_id, source_b_id).

    0.42 는 rules.yaml 의 threshold(0.45) 바로 아래 — points 10→50 관측 하나의 되살림 변화량
    (hot·multi 합 약 0.149)이면 넘어선다.
    """
    normalized = normalize_url(URL)
    hot, multi = score_terms(get_rules().scoring, {"points": points}, 0)
    async with SessionLocal() as s, s.begin():
        # 이전 실행이 중간에 죽으면 같은 URL·소스명이 남아 unique 제약을 건드린다.
        # 새로 심기 전에 잔여물을 정리해 다음 실행이 그 흔적으로 실패하지 않게 한다.
        await s.execute(delete(Item).where(Item.url_hash == url_hash(normalized)))
        await s.execute(delete(Source).where(Source.name.in_(("test:merge-a", "test:merge-b"))))
        config: dict[str, object] = {"family": family} if family else {}
        a = Source(name="test:merge-a", type="rss", config=config)
        b = Source(name="test:merge-b", type="hackernews", config=config)
        s.add_all([a, b])
        await s.flush()
        item = Item(
            source_id=a.id,
            external_id="a-1",
            url=URL,
            url_normalized=normalized,
            url_hash=url_hash(normalized),
            title="t",
            published_at=datetime.now(UTC) - timedelta(hours=age_hours),
            status=status,
            raw={"metrics": {"points": points}, "source": "test:merge-a"},
        )
        s.add(item)
        await s.flush()
        s.add(
            Decision(
                item_id=item.id,
                stage=last_stage,
                passed=False,
                score=last_score,
                details={"breakdown": {"hot": hot, "multi": multi}},
            )
        )
        return item.id, a.id, b.id


async def _cleanup(item_id: int, a_id: int, b_id: int) -> None:
    async with SessionLocal() as s, s.begin():
        await s.execute(delete(Item).where(Item.id == item_id))
        await s.execute(delete(Source).where(Source.id.in_([a_id, b_id])))


async def _load(item_id: int) -> Item:
    async with SessionLocal() as s:
        return (await s.execute(select(Item).where(Item.id == item_id))).scalar_one()


async def _observe(source_id: int, item: NormalizedItem) -> list[int]:
    async with SessionLocal() as s, s.begin():
        return await store_items(s, source_id, [item])


async def test_second_source_merges_metrics_and_mentions_without_new_row():
    item_id, a_id, b_id = await _seed("SENT", "llm")
    try:
        assert await _observe(b_id, observation("test:merge-b", 50.0)) == []
        row = await _load(item_id)
        assert row.raw["metrics"] == {"points": 50.0}
        assert row.raw["mentions"] == ["test:merge-b"]
        assert row.status == "SENT"  # 살아 있는 항목은 병합만 한다
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_score_dropped_item_is_revived():
    item_id, a_id, b_id = await _seed("DROPPED", "score")
    try:
        await _observe(b_id, observation("test:merge-b", 50.0))
        assert (await _load(item_id)).status == "NEW"
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_judge_dropped_item_is_merged_but_not_revived():
    item_id, a_id, b_id = await _seed("DROPPED", "llm")
    try:
        await _observe(b_id, observation("test:merge-b", 50.0))
        row = await _load(item_id)
        assert row.status == "DROPPED"
        assert row.raw["metrics"] == {"points": 50.0}
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_same_values_from_same_source_change_nothing():
    item_id, a_id, b_id = await _seed("DROPPED", "score")
    try:
        await _observe(a_id, observation("test:merge-a", 10.0))
        row = await _load(item_id)
        assert row.status == "DROPPED"
        assert "mentions" not in row.raw
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_stale_item_is_merged_but_not_revived():
    item_id, a_id, b_id = await _seed("DROPPED", "score", age_hours=73)
    try:
        await _observe(b_id, observation("test:merge-b", 50.0))
        row = await _load(item_id)
        assert row.status == "DROPPED"
        assert row.raw["mentions"] == ["test:merge-b"]
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_locked_row_is_skipped_and_merged_on_next_poll():
    """파이프라인이 FOR UPDATE 로 잠근 행은 SKIP LOCKED 로 건너뛰고 다음 폴링에 병합한다."""
    item_id, a_id, b_id = await _seed("DROPPED", "score")
    try:
        async with SessionLocal() as locker, locker.begin():
            await locker.execute(select(Item).where(Item.id == item_id).with_for_update())
            assert await _observe(b_id, observation("test:merge-b", 50.0)) == []
        row = await _load(item_id)
        assert row.raw["metrics"] == {"points": 10.0}
        assert row.status == "DROPPED"

        await _observe(b_id, observation("test:merge-b", 50.0))
        row = await _load(item_id)
        assert row.status == "NEW"
        assert row.raw["metrics"] == {"points": 50.0}
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_far_below_threshold_is_merged_but_not_revived():
    """점수 0.20 은 관측 하나의 변화량(약 0.149)을 더해도 임계값(0.45)에 못 미친다."""
    item_id, a_id, b_id = await _seed("DROPPED", "score", last_score=0.20)
    try:
        await _observe(b_id, observation("test:merge-b", 50.0))
        row = await _load(item_id)
        assert row.status == "DROPPED"
        assert row.raw["metrics"] == {"points": 50.0}
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_large_single_step_gain_revives_far_below_item():
    """마지막 점수가 낮아도 hot 변화량이 크면(HN 프론트 진입) 되살아난다."""
    item_id, a_id, b_id = await _seed("DROPPED", "score", last_score=0.305)
    try:
        await _observe(b_id, observation("test:merge-b", 400.0))
        assert (await _load(item_id)).status == "NEW"
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_saturated_hotness_does_not_revive():
    """hotness 가 이미 포화된 항목은 값이 더 올라도 되살아나지 않는다."""
    item_id, a_id, b_id = await _seed("DROPPED", "score", last_score=0.42, points=1000.0)
    try:
        await _observe(a_id, observation("test:merge-a", 1075.0))
        row = await _load(item_id)
        assert row.raw["metrics"] == {"points": 1075.0}
        assert row.status == "DROPPED"
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_gain_accumulates_across_polls():
    """직전 관측이 아니라 마지막 점수 결정의 breakdown 을 기준으로 삼아야 누적된다.

    10 → 20 → 50 으로 조금씩 오르는 관측에서, 매번 직전 관측과 비교하면(20→50 의 gain
    약 0.029) 임계값을 못 넘는다. 기준을 마지막 점수 결정(10점)에 고정해야 최종 gain 이
    약 0.049 로 커져 되살아난다.
    """
    item_id, a_id, b_id = await _seed("DROPPED", "score", last_score=0.42)
    try:
        await _observe(a_id, observation("test:merge-a", 20.0))
        row = await _load(item_id)
        assert row.status == "DROPPED"  # gain ≈ 0.021, 아직 임계값 미달

        await _observe(a_id, observation("test:merge-a", 50.0))
        assert (await _load(item_id)).status == "NEW"  # 10점 기준 gain ≈ 0.049
    finally:
        await _cleanup(item_id, a_id, b_id)


async def test_same_family_source_is_not_a_mention():
    """같은 family(arxiv) 의 다른 소스 관측은 mentions 에 남기지 않는다."""
    item_id, a_id, b_id = await _seed("DROPPED", "score", family="arxiv")
    try:
        await _observe(b_id, observation("test:merge-b", 50.0))
        row = await _load(item_id)
        assert "mentions" not in row.raw
        assert row.raw["metrics"] == {"points": 50.0}
        assert row.status == "NEW"
    finally:
        await _cleanup(item_id, a_id, b_id)
