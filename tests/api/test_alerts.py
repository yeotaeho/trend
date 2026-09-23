# 알림 상세·피드백 API 단위 테스트 — 404·422 경로, routing 도출, 근거 조각 조립 (DB 없이)

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.queries.alerts import (
    _judgment,
    _score,
    _screening,
    routing_for,
    to_alert,
)
from app.api.v1.schemas.alerts import Routing
from app.db.models import Decision
from tests.api.conftest import AUTH
from tests.api.test_feed import _row


def _d(stage: str, passed: bool = True, **details: Any) -> Decision:
    return Decision(item_id=1, stage=stage, passed=passed, details=details)


@pytest.mark.parametrize("alert_id", ["abc", "0", "-1", "2147483648", "１２"])
def test_invalid_alert_id_is_not_found_without_db(client: TestClient, alert_id: str):
    for method, path, kw in (
        ("GET", f"/api/v1/alerts/{alert_id}", {}),
        ("PUT", f"/api/v1/alerts/{alert_id}/feedback", {"json": {"verdict": "useful"}}),
        ("DELETE", f"/api/v1/alerts/{alert_id}/feedback", {}),
    ):
        res = client.request(method, path, headers=AUTH, **kw)
        assert res.status_code == 404, (method, alert_id)
        assert res.json()["error"]["code"] == "not_found"


def test_feedback_verdict_uses_api_values(client: TestClient):
    # DB 값(useless)이 아니라 API 값(not_useful)만 받는다.
    res = client.put("/api/v1/alerts/1/feedback", json={"verdict": "useless"}, headers=AUTH)
    assert res.status_code == 422


def test_recent_feedback_limit_bounds(client: TestClient):
    for limit in (0, 21):
        res = client.get("/api/v1/feedback/recent", params={"limit": limit}, headers=AUTH)
        assert res.status_code == 422


def test_routing_derivation():
    delivered = to_alert(_row(level="push"), [])
    explored = to_alert(_row(level="explore"), [])
    undelivered = to_alert(_row(level=None, sent_at=None), [])
    restore = _d("user", user_id=1)

    assert routing_for(delivered, [], user_id=1, cluster_dup=False) is Routing.PASSED
    assert routing_for(explored, [], user_id=1, cluster_dup=False) is Routing.EXPLORE_SLOT
    assert routing_for(undelivered, [], user_id=1, cluster_dup=False) is Routing.DROPPED
    assert routing_for(undelivered, [], user_id=1, cluster_dup=True) is Routing.CLUSTER_DUP
    assert routing_for(delivered, [restore], user_id=1, cluster_dup=True) is Routing.RESTORED
    # 다른 사용자의 복원, 취소된 복원은 복원이 아니다.
    assert routing_for(delivered, [restore], user_id=2, cluster_dup=False) is Routing.PASSED
    cancelled = [restore, _d("user", passed=False, user_id=1)]
    assert routing_for(delivered, cancelled, user_id=1, cluster_dup=False) is Routing.PASSED


def test_score_needs_breakdown():
    assert _score(None, 0.45) is None
    assert _score(_d("score", False, reason="stale", age_hours=80), 0.45) is None
    score = _score(_d("score", breakdown={"src": 0.1, "rel": 0.24, "kind": -0.15}), 0.45)
    assert score is not None
    assert score.total == pytest.approx(0.19)
    assert score.components == {"src": 0.1, "rel": 0.24, "kind": -0.15}


def test_screening_tolerates_old_rows():
    assert _screening(None) is None
    old = _screening(_d("triage", relevance=0.3, reason="무관", kind="survey"))
    assert old is not None and old.topics == []
    odd = _screening(_d("triage", relevance="high", kind="gossip", topics=["agent", 3]))
    assert odd is not None
    assert (odd.relevance, odd.kind, odd.topics, odd.reason) == (None, None, ["agent"], None)


def test_judgment_examples():
    assert _judgment(None) is None
    j = _judgment(
        _d(
            "llm",
            False,
            importance=2,
            examples=[
                {"item_id": 17220, "verdict": "useful", "title": "PagedAttention v2"},
                {"item_id": 5, "verdict": "cleared", "title": "해제"},
                "문자열 사례",
            ],
        )
    )
    assert j is not None
    assert (j.importance, j.worth_notifying) == (2, False)
    assert [s.model_dump(mode="json") for s in j.similar_feedback] == [
        {"alert_id": "17220", "feedback": "useful", "title": "PagedAttention v2"}
    ]
    # 사례를 남기기 전의 판정 행
    before = _judgment(_d("llm", importance=4))
    assert before is not None and before.similar_feedback == []
