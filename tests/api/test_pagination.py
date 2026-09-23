# 커서 페이지네이션 테스트 — 커서 왕복, 깨진 커서 400, limit 범위 밖 422 봉투, 다음 커서 계산

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.errors import ApiError, install_error_handlers
from app.api.v1.pagination import Paging, decode_cursor, encode_cursor, paginate


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/api/v1/_list")
    async def _list(paging: Paging) -> dict[str, Any]:
        return {"limit": paging.limit, "after": paging.after}

    return app


def test_cursor_roundtrip():
    key = {"sent_at": "2026-09-24T02:18:00Z", "id": 18342, "note": "한글"}
    cursor = encode_cursor(key)
    assert "=" not in cursor and "+" not in cursor and "/" not in cursor
    assert decode_cursor(cursor) == key


# 해석 불가 · JSON 아님("not-json") · UTF-8 아님 · dict 아님("[1,2]")
@pytest.mark.parametrize("bad", ["%%%", "bm90LWpzb24", "gA", "WzEsMl0"])
def test_broken_cursor_is_bad_request(bad: str):
    with pytest.raises(ApiError) as exc:
        decode_cursor(bad)
    assert (exc.value.status, exc.value.code) == (400, "bad_request")


def test_query_defaults_and_cursor_through_route():
    client = TestClient(_app())
    assert client.get("/api/v1/_list").json() == {"limit": 20, "after": None}

    cursor = encode_cursor({"id": 5})
    res = client.get("/api/v1/_list", params={"limit": 100, "cursor": cursor})
    assert res.json() == {"limit": 100, "after": {"id": 5}}


def test_broken_cursor_through_route_is_400_envelope():
    res = TestClient(_app()).get("/api/v1/_list", params={"cursor": "%%%"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "bad_request"


@pytest.mark.parametrize("limit", ["0", "101", "abc"])
def test_bad_limit_is_422_envelope(limit: str):
    res = TestClient(_app()).get("/api/v1/_list", params={"limit": limit})

    assert res.status_code == 422
    error = res.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]["errors"][0]["loc"] == ["query", "limit"]


def test_paginate_sets_next_cursor_only_when_more_rows():
    rows = [{"id": i} for i in (9, 8, 7)]

    page, cursor = paginate(rows, 2, key=lambda r: {"id": r["id"]})
    assert page == rows[:2]
    assert cursor is not None and decode_cursor(cursor) == {"id": 8}

    page, cursor = paginate(rows, 3, key=lambda r: {"id": r["id"]})
    assert page == rows and cursor is None
