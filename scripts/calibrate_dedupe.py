# 중복 임계값 보정 — 최근 7일 항목 쌍을 유사도 구간별로 10개씩 보여준다. 보고 rules.yaml 을 정한다

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.db.session import engine, session_scope

BANDS = [(0.95, 1.01), (0.90, 0.95), (0.85, 0.90), (0.80, 0.85), (0.75, 0.80)]
SQL = text(
    """
    SELECT a.title AS ta, b.title AS tb, sa.name AS sa, sb.name AS sb,
           1 - (a.embedding <=> b.embedding) AS sim
    FROM items a
    JOIN items b ON a.id < b.id
    JOIN sources sa ON sa.id = a.source_id
    JOIN sources sb ON sb.id = b.source_id
    WHERE a.published_at >= now() - interval '7 days'
      AND b.published_at >= now() - interval '7 days'
      AND a.embedding IS NOT NULL AND b.embedding IS NOT NULL
      AND 1 - (a.embedding <=> b.embedding) >= :lo
      AND 1 - (a.embedding <=> b.embedding) < :hi
    ORDER BY random()
    LIMIT 10
    """
)


async def main() -> None:
    try:
        async with session_scope() as session:
            for lo, hi in BANDS:
                rows = (await session.execute(SQL, {"lo": lo, "hi": hi})).all()
                print(f"\n=== {lo:.2f} ~ {min(hi, 1.0):.2f}  ({len(rows)}쌍 표본) ===")
                for r in rows:
                    print(f"{r.sim:.3f} | {r.sa} | {r.ta[:70]}")
                    print(f"      | {r.sb} | {r.tb[:70]}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
