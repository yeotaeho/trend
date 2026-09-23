# 프로필·리포트 API 단위 테스트 — 유용 비율, 카테고리 반응, kind 감점, 기간·이름 검증, 리포트 조회

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.pagination import encode_cursor
from app.api.v1.queries import profile as queries
from app.api.v1.queries.profile import category_reactions, kind_penalties, useful_ratio
from app.api.v1.queries.reports import to_sections
from app.api.v1.schemas.filtered import KindFeedback
from app.api.v1.schemas.profile import SourceTrustChange
from app.api.v1.schemas.reports import ReportRef
from app.jobs.report import SECTION_KEYS
from app.schemas import Kind
from tests.api.conftest import AUTH


@pytest.mark.parametrize(
    ("useful", "not_useful", "expected"),
    [(27, 15, 64), (1, 7, 13), (1, 1, 50), (0, 3, 0), (3, 0, 100), (2, 1, 67), (0, 0, None)],
)
def test_useful_ratio_rounds_half_up(useful: int, not_useful: int, expected: int | None):
    assert useful_ratio(useful, not_useful) == expected


def test_category_reactions_top_six_by_total():
    topics = ["a", "b", "c", "d", "e", "f", "g"]
    # 토픽 i 는 i+1 건 (👎 1 + 👍 i). 7개 중 가장 적은 a 가 빠진다.
    verdicts: list[tuple[int, str]] = []
    triage: dict[int, dict[str, Any]] = {}
    item = 0
    for i, topic in enumerate(topics):
        for j in range(i + 1):
            item += 1
            verdicts.append((item, "useless" if j == 0 else "useful"))
            triage[item] = {"topics": [topic]}
    rows = category_reactions(verdicts, triage)

    assert [r.category for r in rows] == ["g", "f", "e", "d", "c", "b"]
    assert (rows[0].useful, rows[0].not_useful, rows[0].total) == (6, 1, 7)


def test_category_reactions_skip_items_without_topics():
    verdicts = [(1, "useful"), (2, "useless"), (3, "useful"), (4, "useful")]
    triage: dict[int, dict[str, Any]] = {
        1: {"topics": ["agent", "mcp-tooling"]},
        2: {"topics": ["agent"]},
        3: {"relevance": 0.7},  # topics 를 내기 전의 옛 선별 행
        # 4 — 선별 결정이 없다 (선별 전 탈락 뒤 복원 등)
    }
    rows = {
        r.category: (r.useful, r.not_useful, r.total) for r in category_reactions(verdicts, triage)
    }
    assert rows == {"agent": (1, 1, 2), "mcp-tooling": (1, 0, 1)}


def test_category_reactions_tie_breaks_by_name():
    triage: dict[int, dict[str, Any]] = {1: {"topics": ["video"]}, 2: {"topics": ["agent"]}}
    rows = category_reactions([(1, "useful"), (2, "useful")], triage)
    assert [r.category for r in rows] == ["agent", "video"]


def test_kind_penalties_only_negative_weights_and_zero_counts():
    weights = {Kind.SURVEY: -0.15, Kind.TECHNIQUE: 0.1, Kind.PROMO: -0.3, Kind.NEWS: 0.0}
    feedback = {Kind.SURVEY: KindFeedback(not_useful=4, total=4)}
    rows = kind_penalties(weights, feedback)
    assert [(r.kind, r.weight, r.not_useful, r.total, r.active) for r in rows] == [
        (Kind.SURVEY, -0.15, 4, 4, True),
        (Kind.PROMO, -0.3, 0, 0, True),
    ]


def test_sections_follow_contract_order():
    stored = {k: {"title": k, "columns": ["c"], "rows": [[1]]} for k in reversed(SECTION_KEYS)}
    assert [s.key for s in to_sections(stored)] == list(SECTION_KEYS)


# ---------- 엔드포인트 ----------


class Users:
    """users 한 행. display_name·rename 자리에 끼운다."""

    def __init__(self) -> None:
        self.name = "owner"

    async def get(self, _session: Any, _user_id: int) -> str:
        return self.name

    async def set(self, _session: Any, _user_id: int, name: str) -> None:
        self.name = name


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, session: Any) -> dict[str, Any]:
    """조회 함수를 전부 가짜로. state 를 바꾸면 응답이 따라 바뀐다."""
    users = Users()
    state: dict[str, Any] = {
        "users": users,
        "verdicts": [(1, "useful"), (2, "useless"), (3, "useful")],
        "latest": None,
        "since": [],
    }

    async def delivery(_s: Any, _u: int, since: datetime) -> tuple[int, int, int]:
        state["since"].append(since)
        return 61, 38, 9

    async def verdicts(_s: Any, _u: int, _since: datetime) -> list[tuple[int, str]]:
        return state["verdicts"]

    async def triage(_s: Any, ids: list[int]) -> dict[int, dict[str, Any]]:
        return {i: {"topics": ["agent"]} for i in ids}

    async def count(*_a: Any) -> int:
        return 1

    async def kinds(*_a: Any) -> dict[Kind, KindFeedback]:
        return {Kind.SURVEY: KindFeedback(not_useful=4, total=4)}

    async def trust(_s: Any) -> list[Any]:
        return [
            SourceTrustChange(
                source_id="rss:arxiv-cs-cl", source_name="arXiv cs.CL", from_=0.5, to=0.58
            )
        ]

    async def labels(_s: Any, _u: int) -> int:
        return 42

    async def latest(_s: Any, _u: int) -> ReportRef | None:
        return state["latest"]

    for name, fake in {
        "delivery_counts": delivery,
        "period_verdicts": verdicts,
        "last_triage": triage,
        "restored_count": count,
        "kind_feedback": kinds,
        "trust_changes": trust,
        "label_count": labels,
        "display_name": users.get,
        "rename": users.set,
    }.items():
        monkeypatch.setattr(queries, name, fake)
    monkeypatch.setattr(queries.reports, "latest_report", latest)
    return state


def test_profile_follows_contract(client: TestClient, world: dict[str, Any]):
    res = client.get("/api/v1/profile", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["period_days"] == 14
    assert set(body["user"]) == {
        "display_name",
        "discord_connected",
        "onboarding_done",
        "onboarding_total",
    }
    assert body["user"]["display_name"] == "owner"
    assert (body["user"]["onboarding_done"], body["user"]["onboarding_total"]) == (8, 8)
    assert body["stats"] == {
        "alerts_received": 61,
        "push_count": 38,
        "experiment_count": 9,
        "useful_count": 2,
        "not_useful_count": 1,
        "useful_ratio": 67,
        "missed_issues": 1,
    }
    assert body["category_reactions"] == [
        {"category": "agent", "useful": 2, "not_useful": 1, "total": 3}
    ]
    learned = body["learned"]
    assert learned["source_trust_changes"] == [
        {"source_id": "rss:arxiv-cs-cl", "source_name": "arXiv cs.CL", "from": 0.5, "to": 0.58}
    ]
    survey = next(k for k in learned["kind_penalties"] if k["kind"] == "survey")
    assert (survey["not_useful"], survey["total"], survey["active"]) == (4, 4, True)
    assert all(k["weight"] < 0 for k in learned["kind_penalties"])
    assert (learned["profile_vector_labels"], learned["personal_model_threshold"]) == (42, 50)
    assert body["weekly_report_latest"] is None


def test_profile_without_verdicts_has_null_ratio(client: TestClient, world: dict[str, Any]):
    world["verdicts"] = []
    body = client.get("/api/v1/profile", headers=AUTH).json()
    assert body["stats"]["useful_ratio"] is None
    assert (body["stats"]["useful_count"], body["stats"]["not_useful_count"]) == (0, 0)
    assert body["category_reactions"] == []


def test_profile_latest_report(client: TestClient, world: dict[str, Any]):
    world["latest"] = ReportRef(
        id="12",
        title="9월 2주차 리포트",
        subtitle="깔때기",
        period_start=date(2026, 9, 7),
        period_end=date(2026, 9, 13),
    )
    body = client.get("/api/v1/profile", headers=AUTH).json()
    assert body["weekly_report_latest"] == {
        "id": "12",
        "title": "9월 2주차 리포트",
        "subtitle": "깔때기",
        "period_start": "2026-09-07",
        "period_end": "2026-09-13",
    }


@pytest.mark.parametrize("days", [7, 14, 30])
def test_period_days_allowed(client: TestClient, world: dict[str, Any], days: int):
    res = client.get("/api/v1/profile", params={"period_days": days}, headers=AUTH)
    assert res.status_code == 200
    assert res.json()["period_days"] == days
    [since] = world["since"]
    assert abs((datetime.now(UTC) - since).total_seconds() - days * 86400) < 60


@pytest.mark.parametrize("days", ["0", "8", "15", "31", "abc"])
def test_period_days_rejected(client: TestClient, world: dict[str, Any], days: str):
    res = client.get("/api/v1/profile", params={"period_days": days}, headers=AUTH)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


def test_patch_renames_and_get_reflects(client: TestClient, world: dict[str, Any], session: Any):
    res = client.patch("/api/v1/profile", json={"display_name": "  여태호 "}, headers=AUTH)
    assert res.status_code == 200
    assert res.json()["user"]["display_name"] == "여태호"
    assert res.json()["period_days"] == 14
    assert world["users"].name == "여태호"
    assert client.get("/api/v1/profile", headers=AUTH).json()["user"]["display_name"] == "여태호"


@pytest.mark.parametrize(
    "body",
    [{"display_name": ""}, {"display_name": "   "}, {"display_name": "가" * 21}, {}, {"name": "x"}],
)
def test_patch_rejects_bad_name(client: TestClient, world: dict[str, Any], body: dict[str, Any]):
    res = client.patch("/api/v1/profile", json=body, headers=AUTH)
    assert res.status_code == 422
    assert world["users"].name == "owner"


def test_patch_accepts_twenty_chars(client: TestClient, world: dict[str, Any]):
    res = client.patch("/api/v1/profile", json={"display_name": "가" * 20}, headers=AUTH)
    assert res.status_code == 200


# ---------- 리포트 ----------


class RowSession:
    """execute 가 미리 넣은 행을 돌려주는 세션."""

    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows
        self.statements: list[Any] = []

    async def execute(self, stmt: Any) -> Any:
        self.statements.append(stmt)
        rows = self.rows
        return SimpleNamespace(all=lambda: rows, one_or_none=lambda: rows[0] if rows else None)


def _report_row(rid: int, start: date, **kw: Any) -> Any:
    base = {
        "id": rid,
        "title": "9월 2주차 리포트",
        "subtitle": "깔때기",
        "period_start": start,
        "period_end": date(start.year, start.month, start.day + 6),
        "created_at": datetime(2026, 9, 15, 0, 0, 5, tzinfo=UTC),
    }
    return SimpleNamespace(**(base | kw))


@pytest.fixture
def rows_session() -> Any:
    from app.api.v1 import deps
    from app.main import app

    fake = RowSession([])

    async def _get_session() -> Any:
        yield fake

    app.dependency_overrides[deps.get_session] = _get_session
    yield fake
    app.dependency_overrides.pop(deps.get_session, None)


def test_report_detail(client: TestClient, rows_session: RowSession):
    sections = {
        "trust_adjust": {"title": "신뢰도", "columns": ["source"], "rows": [["rss:a"]]},
        "funnel": {
            "title": "관문별 깔때기",
            "columns": ["stage", "passed", "reason", "n"],
            "rows": [["rule", False, "dup", 3]],
        },
    }
    rows_session.rows = [_report_row(12, date(2026, 9, 8), sections=sections)]
    res = client.get("/api/v1/reports/12", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "12"
    assert body["created_at"] == "2026-09-15T00:00:05Z"
    assert (body["period_start"], body["period_end"]) == ("2026-09-08", "2026-09-14")
    assert [s["key"] for s in body["sections"]] == ["funnel", "trust_adjust"]
    assert body["sections"][0]["rows"] == [["rule", False, "dup", 3]]
    # 다른 사용자의 리포트는 없는 리포트와 같다.
    assert "weekly_reports.user_id = " in str(rows_session.statements[-1])


@pytest.mark.parametrize("rid", ["404", "abc", "0", "-1", "99999999999", "１２"])
def test_report_not_found(client: TestClient, rows_session: RowSession, rid: str):
    res = client.get(f"/api/v1/reports/{rid}", headers=AUTH)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_report_list_pages(client: TestClient, rows_session: RowSession):
    rows_session.rows = [_report_row(3, date(2026, 9, 14)), _report_row(2, date(2026, 9, 7))]
    res = client.get("/api/v1/reports", params={"limit": 1}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert [i["id"] for i in body["items"]] == ["3"]
    assert set(body["items"][0]) == {
        "id",
        "title",
        "subtitle",
        "period_start",
        "period_end",
        "created_at",
    }
    assert body["next_cursor"] == encode_cursor({"d": "2026-09-14", "id": 3})

    rows_session.rows = [_report_row(2, date(2026, 9, 7))]
    res = client.get(
        "/api/v1/reports", params={"limit": 1, "cursor": body["next_cursor"]}, headers=AUTH
    )
    assert res.json()["next_cursor"] is None
    sql = str(rows_session.statements[-1])
    assert "(weekly_reports.period_start, weekly_reports.id) <" in sql
    assert "weekly_reports.user_id = " in sql


@pytest.mark.parametrize("key", [{"d": "x", "id": 1}, {"id": 1}, {"d": "2026-09-07", "id": 0}])
def test_report_list_bad_cursor(client: TestClient, rows_session: RowSession, key: dict[str, Any]):
    res = client.get("/api/v1/reports", params={"cursor": encode_cursor(key)}, headers=AUTH)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "bad_request"
