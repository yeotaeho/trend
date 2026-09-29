# 테스트용 가짜 — DB 없이 웹훅·잡의 upsert_feedback 호출 인자를 기록한다

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class UpsertRecorder:
    """upsert_feedback 자리에 끼운다. 호출 인자를 순서대로 모은다."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((*args[1:], kwargs))  # 세션은 빼고 기록


class NullSession:
    async def execute(self, *_: Any) -> None:
        return None


@asynccontextmanager
async def fake_session_scope() -> AsyncIterator[NullSession]:
    yield NullSession()
