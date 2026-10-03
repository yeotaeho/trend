# 앱 API 오류 봉투 테스트 — ApiError·DB 장애·500 은 /api/v1 에서만 봉투로 바뀐다

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

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

    @app.get("/api/v1/pool-timeout")
    async def pool_timeout() -> None:
        raise PoolTimeoutError("QueuePool limit of size 5 overflow 10 reached")

    @app.get("/api/v1/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    @app.get("/webhook/boom")
    async def webhook_boom() -> None:
        raise RuntimeError("boom")

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


def test_pool_timeout_is_503_on_api():
    res = TestClient(_app()).get("/api/v1/pool-timeout")
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "unavailable"


def test_unhandled_error_is_json_500_on_api():
    # 서버 오류는 응답 뒤 다시 던져져 서버 로그에도 남는다. 응답만 보려고 끈다.
    res = TestClient(_app(), raise_server_exceptions=False).get("/api/v1/boom")
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "internal"


def test_unhandled_error_outside_api_keeps_plain_500():
    res = TestClient(_app(), raise_server_exceptions=False).get("/webhook/boom")
    assert res.status_code == 500
    assert res.text == "Internal Server Error"
