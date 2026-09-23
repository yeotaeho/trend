# 피드 API 단위 테스트 — 필터·커서 검증, 첫 전달 행 SQL, 카드 필드 조립 (DB 없이)

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.v1.pagination import encode_cursor
from app.api.v1.queries.alerts import first_delivery, to_alert
from tests.api.conftest import AUTH


def _row(**kw: Any) -> Any:
    base = {
        "id": 18342,
        "item_title": "원문 제목",
        "url": "https://x/1",
        "summary_raw": None,
        "source_id": "github_release:watchlist",
        "source_type": "github_release",
        "source_config": {"display_name": "GitHub Releases"},
        "title_ko": "요약 제목",
        "summary_ko": "요약",
        "tags": ["mcp"],
        "importance": 4,
        "sent_at": datetime(2026, 9, 24, 2, 18, tzinfo=UTC),
        "level": "push",
        "sent_title": None,
        "verdict": None,
        "saved_item_id": None,
    }
    return SimpleNamespace(**(base | kw))


def test_feed_rejects_unknown_filter(client: TestClient):
    res = client.get("/api/v1/feed", params={"filter": "saved"}, headers=AUTH)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


def test_feed_cursor_with_wrong_shape_is_bad_request(client: TestClient):
    # base64 JSON 이지만 피드 커서 키가 아니다. DB 에 가기 전에 400.
    for key in ({"x": 1}, {"t": "어제", "id": 3}, {"t": "2026-09-24T02:18:00+00:00", "id": "a"}):
        res = client.get("/api/v1/feed", params={"cursor": encode_cursor(key)}, headers=AUTH)
        assert res.status_code == 400, key
        assert res.json()["error"]["code"] == "bad_request"


def test_first_delivery_excludes_errors_cluster_dup_and_other_users():
    sql = str(first_delivery(7).compile(dialect=postgresql.dialect()))
    assert "DISTINCT ON (notifications.item_id)" in sql
    assert "notifications.user_id = %(user_id_1)s" in sql
    assert "notifications.error IS NULL" in sql
    assert "notifications.level != %(level_1)s" in sql
    # 가장 이른 행이 카드 시각·강도·제목을 정한다.
    assert "ORDER BY notifications.item_id, notifications.sent_at, notifications.id" in sql


def test_card_fields_follow_contract():
    alert = to_alert(_row(sent_title="[릴리즈] 발송 제목 (v2.2.0 · v1.30.0)"), ["mcp-tooling"])
    assert alert.model_dump(mode="json") == {
        "id": "18342",
        "source_id": "github_release:watchlist",
        "source_name": "GitHub Releases",
        "source_type": "github_release",
        "delivered_at": "2026-09-24T02:18:00Z",
        "delivery_mode": "instant",
        "is_exploration": False,
        "title": "[릴리즈] 발송 제목 (v2.2.0 · v1.30.0)",
        "summary": "요약",
        "categories": ["mcp-tooling"],
        "tags": ["mcp"],
        "url": "https://x/1",
        "importance": 4,
        "is_saved": False,
        "feedback": None,
    }


def test_card_title_and_summary_fallbacks():
    no_summary = _row(
        title_ko=None, summary_ko=None, tags=None, importance=None, summary_raw="가" * 250
    )
    alert = to_alert(no_summary, [])
    assert alert.title == "원문 제목"
    assert alert.summary == "가" * 200
    assert (alert.tags, alert.importance) == ([], None)
    assert to_alert(_row(), []).title == "요약 제목"
    assert to_alert(_row(summary_ko=None), []).summary is None


def test_card_level_verdict_and_source_mapping():
    modes = {
        level: to_alert(_row(level=level), []).delivery_mode
        for level in ("push", "silent", "feed", "explore")
    }
    assert {k: v.value if v else None for k, v in modes.items()} == {
        "push": "instant",
        "silent": "quiet",
        "feed": "feed_only",
        "explore": "experiment",
    }
    assert to_alert(_row(level="explore"), []).is_exploration is True
    assert to_alert(_row(verdict="useless"), []).feedback == "not_useful"
    assert to_alert(_row(verdict="cleared"), []).feedback is None
    assert to_alert(_row(saved_item_id=18342), []).is_saved is True
    # display_name 이 없으면 소스 이름 그대로
    assert to_alert(_row(source_config={}), []).source_name == "github_release:watchlist"
    undelivered = to_alert(_row(level=None, sent_at=None), [])
    assert (undelivered.delivered_at, undelivered.delivery_mode) == (None, None)
