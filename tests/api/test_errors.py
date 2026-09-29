# 앱 API 오류 봉투 테스트 — ApiError·DB 연결 실패는 /api/v1 에서만 봉투로 바뀐다

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.errors import ApiError, install_error_handlers


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/api/v1/conflict")
    async def conflict() -> None:
        raise ApiError(409, "conflict", "같은 이름의 폴더가 있습니다.", {"field": "name"})

    @app.get("/api/v1/db-down")
    async def db_down() -> None:
        raise ConnectionRefusedError("connect call failed")

    @app.get("/webhook/db-down")
    async def webhook_db_down() -> None:
        raise ConnectionRefusedError("connect call failed")

    return app


def test_api_error_becomes_envelope():
    res = TestClient(_app()).get("/api/v1/conflict")
    assert res.status_code == 409
    assert res.json() == {
        "error": {
            "code": "conflict",
            "message": "같은 이름의 폴더가 있습니다.",
            "details": {"field": "name"},
        }
    }


def test_db_connection_failure_is_503_on_api():
    res = TestClient(_app()).get("/api/v1/db-down")
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "unavailable"


def test_db_connection_failure_outside_api_is_not_masked():
    with pytest.raises(ConnectionRefusedError):
        TestClient(_app()).get("/webhook/db-down")
