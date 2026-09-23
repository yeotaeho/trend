# 앱 API 인증 테스트 — 토큰 없음·틀림·서버 토큰 미설정은 401 봉투, /health·웹훅은 인증 밖

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.api import health
from app.api.v1 import deps
from app.main import app
from tests.api.conftest import AUTH
from tests.fakes import fake_session_scope


def _assert_unauthorized(res: Response) -> None:
    assert res.status_code == 401
    body = res.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"]
    assert body["error"]["details"] == {}


def test_missing_token_is_401(client: TestClient):
    _assert_unauthorized(client.get("/api/v1/meta"))


@pytest.mark.parametrize(
    "header",
    ["Bearer wrong-token", "Basic dGVzdA==", "test-app-token", "Bearer 토큰".encode()],
)
def test_wrong_token_is_401(client: TestClient, header: str | bytes):
    _assert_unauthorized(client.get("/api/v1/meta", headers={"Authorization": header}))


def test_empty_server_token_rejects_everything(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(app_api_token=""))
    client = TestClient(app)
    _assert_unauthorized(client.get("/api/v1/meta", headers={"Authorization": "Bearer "}))
    _assert_unauthorized(client.get("/api/v1/meta", headers={"Authorization": "Bearer x"}))


def test_correct_token_passes(client: TestClient):
    assert client.get("/api/v1/meta", headers=AUTH).status_code == 200


def test_current_user_is_default_user():
    assert deps.current_user_id() == 1


def test_unknown_api_path_is_404_envelope(client: TestClient):
    res = client.get("/api/v1/nope", headers=AUTH)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_health_needs_no_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(health, "session_scope", fake_session_scope)
    res = TestClient(app).get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
