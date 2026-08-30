# 수집기 공통 계층 — Source 프로토콜, 타입별 레지스트리, 재시도 HTTP 헬퍼

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol, runtime_checkable

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import SourceConfig
from app.schemas import NormalizedItem

USER_AGENT = "tech-radar/0.1 (personal dev-trend notifier)"
TIMEOUT = httpx.Timeout(15.0)


@runtime_checkable
class Source(Protocol):
    """소스 하나 = 이 프로토콜을 만족하는 객체 하나."""

    name: str

    async def fetch(self, since: datetime | None) -> list[NormalizedItem]: ...


SourceFactory = Callable[[SourceConfig], Source]
_REGISTRY: dict[str, SourceFactory] = {}


def register(type_name: str) -> Callable[[SourceFactory], SourceFactory]:
    def decorator(factory: SourceFactory) -> SourceFactory:
        _REGISTRY[type_name] = factory
        return factory

    return decorator


def build_source(cfg: SourceConfig) -> Source:
    if cfg.type not in _REGISTRY:
        raise KeyError(f"등록되지 않은 소스 타입: {cfg.type}")
    return _REGISTRY[cfg.type](cfg)


def registered_types() -> list[str]:
    return sorted(_REGISTRY)


def retryable(exc: BaseException) -> bool:
    """네트워크 오류·429·5xx 만 재시도한다. 401·404 는 다시 해도 결과가 같다."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


@retry(
    retry=retry_if_exception(retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    reraise=True,
)
async def fetch_url(url: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
    """GET 한 번 + 지수 백오프 재시도."""
    merged = {"User-Agent": USER_AGENT, **(headers or {})}
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url, headers=merged)
        response.raise_for_status()
        return response
