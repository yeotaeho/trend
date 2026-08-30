# DB 세션 — Neon pooled 엔드포인트용 async 엔진과 잡 단위 세션 컨텍스트

from __future__ import annotations

import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

# asyncpg 가 모르는 libpq 전용 파라미터. TLS 는 아래에서 컨텍스트로 직접 준다.
_LIBPQ_ONLY = {"sslmode", "channel_binding", "options", "application_name", "target_session_attrs"}
_TLS_SSLMODES = {"require", "verify-ca", "verify-full"}
_ASYNCPG_PREFIX = "postgresql+asyncpg://"


def to_asyncpg_url(url: str) -> str:
    """psql 연결 문자열을 SQLAlchemy asyncpg 형식으로 바꾸고 libpq 전용 파라미터를 버린다."""
    for prefix in (_ASYNCPG_PREFIX, "postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = _ASYNCPG_PREFIX + url[len(prefix) :]
            break
    else:
        return url

    parts = urlsplit(url)
    kept = {k: v for k, v in parse_qsl(parts.query) if k not in _LIBPQ_ONLY}
    return urlunsplit(parts._replace(query=urlencode(kept)))


def requires_tls(url: str) -> bool:
    return dict(parse_qsl(urlsplit(url).query)).get("sslmode", "") in _TLS_SSLMODES


def connect_args(url: str) -> dict[str, Any]:
    """asyncpg 에 넘길 연결 인자."""
    if not to_asyncpg_url(url).startswith(_ASYNCPG_PREFIX):
        return {}
    # Neon pgbouncer 는 prepared statement 를 지원하지 않는다.
    args: dict[str, Any] = {"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    if requires_tls(url):
        # sslmode 문자열을 그대로 넘기면 asyncpg 가 ~/.postgresql/root.crt 를 읽는데,
        # 홈 경로에 비ASCII 문자가 있으면 OSError 로 죽는다(asyncpg 가 잡지 않는 예외).
        # 컨텍스트를 직접 만들면 그 경로를 아예 타지 않고, 인증서 검증도 켜진다.
        args["ssl"] = ssl.create_default_context()
    return args


_raw_url = get_settings().database_url
engine = create_async_engine(
    to_asyncpg_url(_raw_url), pool_pre_ping=True, connect_args=connect_args(_raw_url)
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """잡 하나 = 세션 하나. 성공 시 커밋, 예외 시 롤백."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
