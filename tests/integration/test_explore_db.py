# 탐색 후보 통합 테스트 — 임계값 아래 구간·24h·요약 없음·마지막 score 탈락·오늘 나간 클러스터 제외

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.config import NotifyConfig, Rules
from app.db.models import Decision, Item, Notification, Source, Summary
from app.db.session import SessionLocal
from app.db.users import DEFAULT_USER_ID
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

        best, low, old, summarized, passed_later, judged_later = (
            item("best", 0.44),
            item("low", 0.30),
            item("old", 0.44, age_h=30),
            item("summarized", 0.43),
            item("passed_later", 0.44),
            item("judged_later", 0.445),
        )
        s.add_all([best, low, old, summarized, passed_later, judged_later])
        await s.flush()
        for it in (best, low, old, summarized, judged_later):
            s.add(Decision(item_id=it.id, stage="score", passed=False, score=it.score, details={}))
        s.add(Decision(item_id=passed_later.id, stage="score", passed=True, score=0.44, details={}))
        await s.flush()
        # 점수 탈락 뒤 다른 결정이 붙으면 마지막 결정이 score 탈락이 아니다. 최고점이어도 제외.
        s.add(Decision(item_id=judged_later.id, stage="llm", passed=False, score=0.445, details={}))
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
        ids = ([best.id, low.id, old.id, summarized.id, passed_later.id, judged_later.id], src.id)

    try:
        async with SessionLocal() as s:
            row = await _explore_candidate(s, rules, now)
        assert row is not None and row[0].id == ids[0][0]
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(ids[0])))
            await s.execute(delete(Source).where(Source.id == ids[1]))


async def test_explore_candidate_skips_cluster_sent_today():
    """오늘 이미 나간 클러스터의 항목은 점수가 높아도 후보가 아니다. 상한 0 이면 제외 없음."""
    now = datetime.now(UTC)
    async with SessionLocal() as s, s.begin():
        src = Source(name="test:explore-cluster", type="rss", config={})
        s.add(src)
        await s.flush()

        def item(key: str, score: float, status: str = "DROPPED") -> Item:
            return Item(
                source_id=src.id,
                external_id=key,
                url=f"https://t/{key}",
                url_normalized=f"https://t/{key}",
                url_hash=f"ex-cl-{key}",
                title=key,
                published_at=now - timedelta(hours=1),
                status=status,
                score=score,
            )

        sent, in_sent_cluster, other = item("sent", 0.9, "SENT"), item("in", 0.449), item("o", 0.40)
        s.add_all([sent, in_sent_cluster, other])
        await s.flush()
        sent.cluster_id = in_sent_cluster.cluster_id = sent.id
        for it in (in_sent_cluster, other):
            s.add(Decision(item_id=it.id, stage="score", passed=False, score=it.score, details={}))
        s.add(
            Notification(
                user_id=DEFAULT_USER_ID,
                item_id=sent.id,
                channel="discord",
                level="silent",
                message_id="m",
            )
        )
        ids = ([sent.id, in_sent_cluster.id, other.id], src.id)

    try:
        async with SessionLocal() as s:
            row = await _explore_candidate(s, Rules(), now)
        # dev DB 에 더 높은 후보가 있어도 이 클러스터 항목이 뽑히면 안 된다.
        assert row is None or row[0].id != ids[0][1]
        async with SessionLocal() as s:
            row = await _explore_candidate(s, Rules(notify=NotifyConfig(cluster_daily_cap=0)), now)
        assert row is not None and row[0].score >= 0.449
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(ids[0])))
            await s.execute(delete(Source).where(Source.id == ids[1]))
