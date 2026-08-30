# 헬스체크 — DB 왕복까지 확인한다

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.db.session import session_scope

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    async with session_scope() as session:
        await session.execute(select(1))
    return {"status": "ok"}
