# 최근접 피드백 통합 테스트 — 같은 벡터의 항목에 남긴 피드백이 사례로 나온다

from datetime import UTC, datetime

from sqlalchemy import delete, update

from app.db.models import Feedback, Item, Source, Summary
from app.db.session import SessionLocal
from app.pipeline.feedback import nearest_feedback

VEC_LIST = [0.03] * 1024


async def test_nearest_feedback_finds_identical_vector():
    now = datetime.now(UTC)
    async with SessionLocal() as s, s.begin():
        src = Source(name="test:fb", type="rss", config={})
        s.add(src)
        await s.flush()
        a = Item(
            source_id=src.id,
            external_id="a",
            url="https://t/a",
            url_normalized="https://t/a",
            url_hash="fb-a",
            title="A",
            published_at=now,
        )
        b = Item(
            source_id=src.id,
            external_id="b",
            url="https://t/b",
            url_normalized="https://t/b",
            url_hash="fb-b",
            title="B",
            published_at=now,
        )
        c = Item(
            source_id=src.id,
            external_id="c",
            url="https://t/c",
            url_normalized="https://t/c",
            url_hash="fb-c",
            title="C",
            published_at=now,
        )
        s.add_all([a, b, c])
        await s.flush()
        await s.execute(
            update(Item)
            .where(Item.id.in_([a.id, b.id]))
            .values(embedding=VEC_LIST, embedding_model="t")
        )
        # c 는 a 와 직교에 가까운 벡터. min_sim 0.75 아래라 사례에서 빠져야 한다.
        far = [0.03] * 512 + [-0.03] * 512
        await s.execute(
            update(Item).where(Item.id == c.id).values(embedding=far, embedding_model="t")
        )
        for it, title in ((b, "[릴리즈] B"), (c, "[영상] C")):
            s.add(
                Summary(
                    item_id=it.id,
                    title_ko=title,
                    summary_ko="",
                    importance=3,
                    worth_notifying=True,
                    model="m",
                )
            )
        s.add_all(
            [Feedback(item_id=b.id, verdict="useful"), Feedback(item_id=c.id, verdict="useless")]
        )
        # a 자신에게도 피드백을 달아 자기 제외를 확인한다.
        s.add(Feedback(item_id=a.id, verdict="useless"))
        ids = (a.id, b.id, c.id, src.id)

    try:
        async with SessionLocal() as s:
            examples = await nearest_feedback(s, ids[0], k=3)
            limited = await nearest_feedback(s, ids[0], k=3, min_sim=-1.0)
            capped = await nearest_feedback(s, ids[0], k=1, min_sim=-1.0)
        # 자기 자신(a) 제외, 먼 c 는 min_sim 에 걸려 제외
        assert [(e.verdict, e.title_ko) for e in examples] == [("useful", "[릴리즈] B")]
        # 임계값을 풀면 거리순으로 b, c. k 로 자르면 가장 가까운 b 만
        assert [e.title_ko for e in limited] == ["[릴리즈] B", "[영상] C"]
        assert [e.title_ko for e in capped] == ["[릴리즈] B"]
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(ids[:3])))
            await s.execute(delete(Source).where(Source.id == ids[3]))
