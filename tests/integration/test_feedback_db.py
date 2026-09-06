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
        s.add_all([a, b])
        await s.flush()
        await s.execute(
            update(Item)
            .where(Item.id.in_([a.id, b.id]))
            .values(embedding=VEC_LIST, embedding_model="t")
        )
        s.add(
            Summary(
                item_id=b.id,
                title_ko="[릴리즈] B",
                summary_ko="",
                importance=3,
                worth_notifying=True,
                model="m",
            )
        )
        s.add(Feedback(item_id=b.id, verdict="useful"))
        ids = (a.id, b.id, src.id)

    try:
        async with SessionLocal() as s:
            examples = await nearest_feedback(s, ids[0], k=3)
        assert [(e.verdict, e.title_ko) for e in examples] == [("useful", "[릴리즈] B")]
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(ids[:2])))
            await s.execute(delete(Source).where(Source.id == ids[2]))
