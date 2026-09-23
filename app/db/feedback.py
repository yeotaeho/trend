# 피드백 저장 — (사용자, 항목)당 1건, 다시 누르면 판정·출처·시각을 덮어쓴다

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feedback


def feedback_upsert_stmt(user_id: int, item_id: int, verdict: str, source: str) -> Insert:
    """source 는 판정이 들어온 곳 — discord | telegram | app."""
    stmt = insert(Feedback).values(user_id=user_id, item_id=item_id, verdict=verdict, source=source)
    return stmt.on_conflict_do_update(
        index_elements=["user_id", "item_id"],  # uq_feedback_user_item
        set_={
            "verdict": stmt.excluded.verdict,
            "source": stmt.excluded.source,
            "created_at": func.now(),
        },
    )


async def upsert_feedback(
    session: AsyncSession, user_id: int, item_id: int, verdict: str, source: str
) -> None:
    await session.execute(feedback_upsert_stmt(user_id, item_id, verdict, source))
