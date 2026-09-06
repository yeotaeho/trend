# 벡터 중복 쿼리 통합 테스트 — 더 비슷한 탈락 항목이 있어도 생존 항목이 중복 기준이 된다

from datetime import UTC, datetime

from sqlalchemy import delete, update

from app.config import DedupeConfig
from app.db.models import Item, Source
from app.db.session import SessionLocal
from app.pipeline.dedupe import find_candidates


def vec(a: float, b: float) -> list[float]:
    # 앞 두 성분만 다르고 나머지는 같은 벡터. a·b 로 코사인을 조절한다.
    return [a, b] + [0.01] * 1022


async def test_query_a_prefers_survivor_over_more_similar_dropped():
    now = datetime.now(UTC)
    async with SessionLocal() as s, s.begin():
        src = Source(name="test:dedupe", type="rss", config={})
        s.add(src)
        await s.flush()

        def item(key: str, status: str) -> Item:
            return Item(
                source_id=src.id,
                external_id=key,
                url=f"https://t/{key}",
                url_normalized=f"https://t/{key}",
                url_hash=f"dd-{key}",
                title=key,
                published_at=now,
                status=status,
            )

        target, dropped, survivor = (
            item("target", "NEW"),
            item("dropped", "DROPPED"),
            item("survivor", "SENT"),
        )
        s.add_all([target, dropped, survivor])
        await s.flush()
        for it, v in (
            (target, vec(1.0, 0.0)),
            (dropped, vec(1.0, 0.01)),
            (survivor, vec(1.0, 0.2)),
        ):
            await s.execute(
                update(Item).where(Item.id == it.id).values(embedding=v, embedding_model="t")
            )
        ids = (target.id, dropped.id, survivor.id, src.id)

    try:
        async with SessionLocal() as s:
            dup, related = await find_candidates(s, ids[0], DedupeConfig(related_threshold=0.5))
        assert dup is not None and dup.id == ids[2]  # 더 비슷한 dropped 가 아니라 survivor
        assert {c.id for c in related} == {ids[1], ids[2]}
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(ids[:3])))
            await s.execute(delete(Source).where(Source.id == ids[3]))
