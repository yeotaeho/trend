# 앱 API 의존성 — 베어러 토큰 인증, 요청 사용자(DEFAULT_USER_ID), 요청 단위 DB 세션

from __future__ import annotations

import hmac
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import ApiError
from app.config import get_settings
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID

_bearer = HTTPBearer(auto_error=False)


async def require_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """서버 토큰이 비어 있으면 모든 요청이 401 이다 (디스코드 공개키와 같은 방식)."""
    expected = get_settings().app_api_token
    given = credentials.credentials if credentials else ""
    if not expected or not hmac.compare_digest(expected.encode(), given.encode()):
        raise ApiError(401, "unauthorized", "인증 토큰이 없거나 올바르지 않습니다.")


def current_user_id() -> int:
    """토큰은 하나이고 단일 사용자에 매핑된다. 사용자별 토큰은 다중 사용자 설계 때 붙인다."""
    return DEFAULT_USER_ID


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_scope() as session:
        yield session


UserId = Annotated[int, Depends(current_user_id)]
# scope="function" — 응답을 보내기 전에 커밋한다. 커밋 실패가 200 뒤에 숨지 않는다.
Session = Annotated[AsyncSession, Depends(get_session, scope="function")]
