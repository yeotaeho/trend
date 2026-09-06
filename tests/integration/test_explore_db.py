# 탐색 후보 통합 테스트 — 임계값 바로 아래·24h 이내·Summary 없음·마지막 score 탈락인 최고점

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.config import Rules
from app.db.models import Decision, Item, Source, Summary
from app.db.session import SessionLocal
from app.jobs.notify import _explore_candidate


async def test_explore_candidate_picks_highest_in_band_without_summary():
    rules = Rules()  # threshold 0.45 → 후보 구간 [0.35, 0.45)
    now = datetime.now(UTC)
    async with SessionLocal() as s, s.begin():
        src = Source(name="test:explore", type="rss", config={})
        s.add(src)
        await s.flush()

        def item(key: str, score: float, age_h: int = 1) -> Item:
            return Item(
                source_id=src.id,
                external_id=key,
                url=f"https://t/{key}",
                url_normalized=f"https://t/{key}",
                url_hash=f"ex-{key}",
                title=key,
                published_at=now - timedelta(hours=age_h),
                status="DROPPED",
                score=score,
            )

        best, low, old, summarized, passed_later = (
            item("best", 0.44),
            item("low", 0.30),
            item("old", 0.44, age_h=30),
            item("summarized", 0.43),
            item("passed_later", 0.44),
        )
        s.add_all([best, low, old, summarized, passed_later])
        await s.flush()
        for it in (best, low, old, summarized):
            s.add(Decision(item_id=it.id, stage="score", passed=False, score=it.score, details={}))
        s.add(Decision(item_id=passed_later.id, stage="score", passed=True, score=0.44, details={}))
        s.add(
            Summary(
                item_id=summarized.id,
                title_ko="x",
                summary_ko="",
                importance=1,
                worth_notifying=False,
                model="m",
            )
        )
        ids = ([best.id, low.id, old.id, summarized.id, passed_later.id], src.id)

    try:
        async with SessionLocal() as s:
            row = await _explore_candidate(s, rules, now)
        assert row is not None and row[0].id == ids[0][0]
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(ids[0])))
            await s.execute(delete(Source).where(Source.id == ids[1]))
