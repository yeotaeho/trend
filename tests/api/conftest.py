# 앱 API 테스트 공통 — 서버 토큰을 고정한 클라이언트와 인증 헤더

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import deps
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
