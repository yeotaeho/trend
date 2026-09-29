# 수집 소스 API 테스트 — GET /sources 는 계약 4.5 예시 모양, PATCH 는 행과 user_prefs 를 같이 쓴다

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import sources as sources_api
from app.api.v1.queries import sources as queries
from app.config import SourceConfig
from app.db import budget
from app.db.budget import BudgetUsage
from app.db.models import Source
from tests.api.conftest import AUTH, PrefsStore
from tests.conftest import fixture

REPOS = [f"org/repo{i}" for i in range(10)]


def _rows() -> dict[str, Source]:
    """계약 4.5 예시의 세 소스와 같은 DB 행."""
    return {
        "rss:anthropic": Source(
            name="rss:anthropic",
            type="rss",
            config={"display_name": "Anthropic", "error_hint": "미러 확인 필요", "url": "u"},
            enabled=True,
            poll_interval_sec=900,
            trust_score=1.0,
            trust_adjusted=None,
            fail_count=5,
            last_error="HTTPStatusError: 404",
            last_polled_at=datetime(2026, 9, 23, 20, 0, tzinfo=UTC),
        ),
        "github_release:watchlist": Source(
            name="github_release:watchlist",
            type="github_release",
            config={"display_name": "GitHub Releases", "repos": REPOS},
            enabled=True,
            poll_interval_sec=1800,
            trust_score=1.0,
            trust_adjusted=None,
            fail_count=0,
            last_error=None,
            last_polled_at=datetime(2026, 9, 24, 2, 30, tzinfo=UTC),
        ),
        "youtube:codingapple": Source(
            name="youtube:codingapple",
            type="youtube",
            config={"display_name": "코딩애플", "channel_id": "c"},
            enabled=False,
            poll_interval_sec=900,
            trust_score=0.6,
            trust_adjusted=0.52,
            fail_count=0,
            last_error=None,
            last_polled_at=datetime(2026, 9, 22, 10, 0, tzinfo=UTC),
        ),
    }


@pytest.fixture
def rows(monkeypatch: pytest.MonkeyPatch, store: PrefsStore) -> dict[str, Source]:
    table = _rows()
    names = [*table, "rss:not-synced-yet"]
    monkeypatch.setattr(
        sources_api,
        "get_source_configs",
        lambda: [SourceConfig(name=n, type="rss") for n in names],
    )

    async def by_name(_session: Any, wanted: list[str]) -> dict[str, Source]:
        # YAML 에서 빠져 비활성화된 과거 행도 테이블에 있다. 조회 조건이 걸러야 한다.
        return {n: table[n] for n in wanted if n in table}

    async def collected(_session: Any, window_hours: int) -> int:
        assert window_hours == 24
        return 612

    async def usage(_session: Any) -> dict[str, BudgetUsage]:
        return {
            "triage": BudgetUsage(41, 60),
            "judge": BudgetUsage(18, 300),
            "explore": BudgetUsage(1, 3),
        }

    monkeypatch.setattr(queries, "sources_by_name", by_name)
    monkeypatch.setattr(queries, "items_collected", collected)
    monkeypatch.setattr(budget, "usage_today", usage)
    return table


def test_get_sources_matches_contract_example(client: TestClient, rows):
    expected = json.loads(fixture("app_api/sources.json"))

    res = client.get("/api/v1/sources", headers=AUTH)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["sources"] == expected["sources"]
    assert body["stats"] == expected["stats"] | {"enabled_count": 2, "total": 3}
    assert body["planned_sources"] == expected["planned_sources"]


def test_source_group_rules():
    assert sources_api.source_group("rss", {}) == "blog_rss"
    assert sources_api.source_group("rss", {"family": "arxiv"}) == "paper_release_video"
    assert sources_api.source_group("hf_papers", {}) == "paper_release_video"
    assert sources_api.source_group("hackernews", {}) == "community"


def test_display_name_falls_back_to_id():
    row = Source(name="rss:x", type="rss", config={}, poll_interval_sec=900, trust_score=0.5)
    row.enabled, row.fail_count = True, 0

    assert sources_api.to_view(row).display_name == "rss:x"


def test_patch_source_writes_row_and_prefs(client: TestClient, rows, store: PrefsStore, session):
    store.data = {"notify": {"daily_push_cap": 20}}

    res = client.patch("/api/v1/sources/rss%3Aanthropic", headers=AUTH, json={"enabled": False})

    assert res.status_code == 200, res.text
    assert res.json()["enabled"] is False
    assert res.json()["id"] == "rss:anthropic"
    assert rows["rss:anthropic"].enabled is False
    assert store.data == {
        "notify": {"daily_push_cap": 20},
        "sources": {"rss:anthropic": {"enabled": False}},
    }
    assert session.commits == 1


@pytest.mark.parametrize("source_id", ["rss:unknown", "rss:not-synced-yet"])
def test_patch_unknown_source_is_404(client: TestClient, rows, store: PrefsStore, source_id):
    res = client.patch(f"/api/v1/sources/{source_id}", headers=AUTH, json={"enabled": False})

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"
    assert store.saves == 0


@pytest.mark.parametrize("body", [{}, {"enabled": "maybe"}, {"enabled": True, "trust": 1.0}])
def test_patch_source_rejects_invalid_body(client: TestClient, rows, store: PrefsStore, body):
    res = client.patch("/api/v1/sources/rss:anthropic", headers=AUTH, json=body)

    assert res.status_code == 422
    assert store.saves == 0
