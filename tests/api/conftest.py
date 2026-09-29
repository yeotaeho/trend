# 앱 API 테스트 공통 — 서버 토큰을 고정한 클라이언트, 인증 헤더, DB 없는 세션·user_prefs 가짜

from __future__ import annotations

import copy
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import deps
from app.db import prefs
from app.main import app

TOKEN = "test-app-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def server_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(app_api_token=TOKEN))
    return TOKEN


@pytest.fixture
def client(server_token: str) -> TestClient:
    # 컨텍스트 매니저로 열지 않는다 — lifespan(스케줄러·DB)을 띄우지 않는다.
    return TestClient(app)


class FakeSession:
    """라우터가 직접 부르는 세션 메서드는 commit 뿐이다. 조회는 쿼리 함수를 바꿔 끼운다."""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class PrefsStore:
    """user_prefs 한 행. fetch_prefs·upsert_prefs 자리에 끼운다 (save_prefs 는 진짜를 쓴다)."""

    def __init__(self) -> None:
        self.data: dict[str, Any] | None = None
        self.updated_at: datetime | None = None
        self.saves = 0

    async def fetch(self, _session: Any, _user_id: int, *, for_update: bool = False) -> Any:
        if self.data is None:
            return None
        return SimpleNamespace(data=copy.deepcopy(self.data), updated_at=self.updated_at)

    async def upsert(self, _session: Any, _user_id: int, data: dict[str, Any]) -> datetime:
        self.saves += 1
        self.data = copy.deepcopy(data)
        self.updated_at = datetime(2026, 9, 24, 2, 18, self.saves, tzinfo=UTC)
        return self.updated_at


@pytest.fixture
def session() -> Iterator[FakeSession]:
    fake = FakeSession()

    async def _get_session() -> AsyncIterator[FakeSession]:
        yield fake

    app.dependency_overrides[deps.get_session] = _get_session
    yield fake
    app.dependency_overrides.pop(deps.get_session, None)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, session: FakeSession) -> PrefsStore:
    fake = PrefsStore()
    monkeypatch.setattr(prefs, "fetch_prefs", fake.fetch)
    monkeypatch.setattr(prefs, "upsert_prefs", fake.upsert)
    return fake
