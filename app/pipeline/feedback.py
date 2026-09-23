# 최근접 피드백 사례 — 임베딩이 가까운 👍/👎 항목을 찾아 프롬프트 한 줄과 판정 행 사례로 쓴다

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.users import DEFAULT_USER_ID

MARK = {"useful": "👍", "useless": "👎"}
# 피드백은 (사용자, 항목)당 1건이라 조인이 곧 그 사용자의 최신 판정이다.
# 앱 해제(cleared)는 사례가 아니다.
# 요약이 없는 항목(걸러짐에서 복원)은 원문 제목을 쓴다. 항목의 embedding 이 NULL 이면 빈 결과.
_SQL = text(
    """
    WITH q AS (SELECT embedding FROM items WHERE id = :item_id)
    SELECT f.item_id, f.verdict, COALESCE(s.title_ko, i.title) AS title
    FROM feedback f
    JOIN items i ON i.id = f.item_id
    CROSS JOIN q
    LEFT JOIN summaries s ON s.item_id = f.item_id
    WHERE f.user_id = :user_id
      AND f.verdict IN ('useful', 'useless')
      AND f.item_id <> :item_id
      AND i.embedding IS NOT NULL
      AND 1 - (i.embedding <=> q.embedding) >= :min_sim
    ORDER BY i.embedding <=> q.embedding
    LIMIT :k
    """
)


@dataclass(slots=True, frozen=True)
class FeedbackExample:
    item_id: int
    verdict: str
    title: str


def format_examples(examples: list[FeedbackExample]) -> str:
    return " · ".join(f'{MARK[e.verdict]} "{e.title}"' for e in examples)


def examples_details(examples: list[FeedbackExample]) -> list[dict[str, object]]:
    """판정 결정 행 details.examples — 앱 상세 화면의 '유사 피드백' 이 읽는다."""
    return [{"item_id": e.item_id, "verdict": e.verdict, "title": e.title} for e in examples]


async def nearest_feedback(
    session: AsyncSession,
    item_id: int,
    *,
    k: int,
    min_sim: float = 0.75,
    user_id: int = DEFAULT_USER_ID,
) -> list[FeedbackExample]:
    params = {"item_id": item_id, "user_id": user_id, "min_sim": min_sim, "k": k}
    rows = (await session.execute(_SQL, params)).all()
    return [FeedbackExample(r.item_id, r.verdict, r.title) for r in rows]
