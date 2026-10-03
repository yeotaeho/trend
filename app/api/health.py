# 헬스체크 — DB 왕복까지 확인한다

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.db.session import session_scope

router = APIRouter()


# 무료 가동 감시는 HEAD 가 기본이다. FastAPI 는 GET 에 HEAD 를 붙여 주지 않는다.
@router.api_route("/health", methods=["GET", "HEAD"])
async def health() -> dict[str, str]:
    async with session_scope() as session:
        await session.execute(select(1))
    return {"status": "ok"}
