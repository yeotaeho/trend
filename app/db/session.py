# DB 세션 — Neon pooled 엔드포인트용 async 엔진과 잡 단위 세션 컨텍스트

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

# asyncpg 가 모르는 libpq 전용 파라미터. sslmode 만 ssl 로 옮기고 나머지는 버린다.
_LIBPQ_ONLY = {"sslmode", "channel_binding", "options", "application_name", "target_session_attrs"}


def to_asyncpg_url(url: str) -> str:
    """psql 연결 문자열을 SQLAlchemy asyncpg 형식으로 바꾼다."""
    for prefix in ("postgresql+asyncpg://", "postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix) :]
            break
    else:
        return url

    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query))
    sslmode = params.get("sslmode")
    kept = {k: v for k, v in params.items() if k not in _LIBPQ_ONLY}
    if sslmode and sslmode not in ("disable", "allow", "prefer"):
        kept["ssl"] = "require"
    return urlunsplit(parts._replace(query=urlencode(kept)))


def _engine_kwargs(url: str) -> dict[str, Any]:
    if not url.startswith("postgresql+asyncpg://"):
        return {}
    # Neon pgbouncer 는 prepared statement 를 지원하지 않는다.
    return {"connect_args": {"statement_cache_size": 0, "prepared_statement_cache_size": 0}}


_url = to_asyncpg_url(get_settings().database_url)
engine = create_async_engine(_url, pool_pre_ping=True, **_engine_kwargs(_url))
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
