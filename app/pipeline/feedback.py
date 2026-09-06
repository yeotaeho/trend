# 최근접 피드백 사례 — 항목과 임베딩이 가까운 👍/👎 항목을 찾아 프롬프트에 붙일 한 줄을 만든다

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MARK = {"useful": "👍", "useless": "👎"}
# 피드백은 항목당 1건이라 조인이 곧 최신 판정이다. 항목의 embedding 이 NULL 이면 빈 결과.
_SQL = text(
    """
    WITH q AS (SELECT embedding FROM items WHERE id = :item_id)
    SELECT f.verdict, s.title_ko
    FROM feedback f
    JOIN items i ON i.id = f.item_id
    JOIN summaries s ON s.item_id = f.item_id, q
    WHERE f.item_id <> :item_id
      AND i.embedding IS NOT NULL
      AND 1 - (i.embedding <=> q.embedding) >= :min_sim
    ORDER BY i.embedding <=> q.embedding
    LIMIT :k
    """
)


@dataclass(slots=True, frozen=True)
class FeedbackExample:
    verdict: str
    title_ko: str


def format_examples(examples: list[FeedbackExample]) -> str:
    return " · ".join(f'{MARK[e.verdict]} "{e.title_ko}"' for e in examples)


async def nearest_feedback(
    session: AsyncSession, item_id: int, *, k: int, min_sim: float = 0.75
) -> list[FeedbackExample]:
    rows = (await session.execute(_SQL, {"item_id": item_id, "min_sim": min_sim, "k": k})).all()
    return [FeedbackExample(r.verdict, r.title_ko) for r in rows]
