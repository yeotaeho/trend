# 피드백 저장 — (사용자, 항목)당 1건, 다시 누르면 덮어쓴다. 앱 해제는 cleared 로 남긴다

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feedback

CLEARED = "cleared"
# 앱에서 정한 판정. 디스코드 리액션 폴링이 덮어쓰지 않는다.
APP_SOURCE = "app"


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


async def set_app_feedback(
    session: AsyncSession, user_id: int, item_id: int, verdict: str
) -> datetime:
    """앱의 판정 설정. 돌려주는 값은 판정 시각.

    같은 판정을 다시 보내면(재시도) 시각을 밀지 않고 출처만 app 으로 가져온다. 시각이 밀리면
    옛 판정이 오늘 판정 수와 최근 판정 맨 위로 올라온다 (리액션 폴링과 같은 이유).
    """
    mine = (Feedback.user_id == user_id, Feedback.item_id == item_id)
    current = (await session.execute(select(Feedback).where(*mine))).scalar_one_or_none()
    if current is not None and current.verdict == verdict:
        current.source = APP_SOURCE
        return current.created_at
    stmt = feedback_upsert_stmt(user_id, item_id, verdict, APP_SOURCE).returning(
        Feedback.created_at
    )
    created_at: datetime = (await session.execute(stmt)).scalar_one()
    return created_at


async def clear_feedback(session: AsyncSession, user_id: int, item_id: int) -> None:
    """앱의 판정 해제. 행을 지우지 않고 cleared·app 으로 바꿔 리액션 폴링이 되살리지 못하게 한다.

    판정이 없던 항목은 아무것도 하지 않는다.
    """
    await session.execute(
        update(Feedback)
        .where(Feedback.user_id == user_id, Feedback.item_id == item_id)
        .values(verdict=CLEARED, source=APP_SOURCE, created_at=func.now())
    )
