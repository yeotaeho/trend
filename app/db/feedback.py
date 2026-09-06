# 피드백 저장 — 항목당 1건, 다시 누르면 판정과 시각을 덮어쓴다

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feedback


def feedback_upsert_stmt(item_id: int, verdict: str) -> Insert:
    stmt = insert(Feedback).values(item_id=item_id, verdict=verdict)
    return stmt.on_conflict_do_update(
        constraint="uq_feedback_item_id",
        set_={"verdict": stmt.excluded.verdict, "created_at": func.now()},
    )


async def upsert_feedback(session: AsyncSession, item_id: int, verdict: str) -> None:
    await session.execute(feedback_upsert_stmt(item_id, verdict))
