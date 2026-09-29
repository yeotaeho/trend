# 걸러진 항목 API 단위 테스트 — 관문 분류, 요약·그룹·목록 조립, 걸러짐 집합 SQL, 복원 행 (DB 없이)

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.v1.pagination import PageParams, encode_cursor
from app.api.v1.queries import filtered as queries
from app.api.v1.queries.filtered import (
    UNCLASSIFIED,
    build_groups,
    classify,
    filtered_set,
    page_items,
    summarize,
    to_dropped,
)
from app.api.v1.schemas.filtered import DroppedItem, FilteredView, Gate, GroupSort, KindFeedback
from app.db.models import Decision, Notification
from app.jobs.notify import explore_candidate
from app.schemas import Kind
from tests.api.conftest import AUTH

FLOOR = 0.5
THRESHOLD = 0.45
T0 = datetime(2026, 9, 24, 0, 0, tzinfo=UTC)
BREAKDOWN = {"src": 0.1, "rel": 0.24, "hot": 0.0, "fresh": 0.1, "kind": -0.15}


def _row(**kw: Any) -> Any:
    base = {
        "id": 18107,
        "title": "Survey of Agentic Software Engineering",
        "url": "https://arxiv.org/abs/2609.01234",
        "source_id": "rss:arxiv-cs-se",
        "source_type": "rss",
        "source_config": {"display_name": "arXiv cs.SE"},
        "dropped_at": T0,
        "gate_stage": "score",
        "gate_details": {"breakdown": BREAKDOWN},
        "triage_details": {"relevance": 0.62, "kind": "survey", "reason": "서베이", "topics": []},
        "score_details": {"breakdown": BREAKDOWN},
        "exploration_candidate": False,
        "restored": False,
    }
    return SimpleNamespace(**(base | kw))


def _dropped(**kw: Any) -> DroppedItem:
    return to_dropped(_row(**kw), floor=FLOOR, threshold=THRESHOLD)


def _triage(kind: str, relevance: float = 0.7) -> dict[str, Any]:
    return {"relevance": relevance, "kind": kind, "reason": "r", "topics": ["agent"]}


def _seven() -> list[DroppedItem]:
    """관문마다 한 건. dropped_at 내림차순 (load_dropped 와 같은 순서)."""
    pre = {"triage_details": None, "score_details": None}
    rows = [
        # exclude — 선별 전이라 kind·relevance 가 없다.
        dict(
            gate_stage="rule",
            gate_details={"reason": "exclude_keyword", "matched": ["sponsored"]},
            **pre,
        ),
        dict(gate_stage="rule", gate_details={"reason": "dup", "cluster_id": 3}, **pre),
        dict(gate_stage="score", gate_details={"reason": "stale", "age_hours": 80}, **pre),
        dict(triage_details=_triage("survey", 0.3)),
        dict(triage_details=_triage("survey"), exploration_candidate=True),
        dict(gate_stage="llm", gate_details={"importance": 2}, triage_details=_triage("news")),
        # cluster_dup — 결정이 아니라 알림 행으로 판별. 선별·점수 결정은 채워진다.
        dict(
            gate_stage=None,
            gate_details=None,
            triage_details=_triage("release_patch"),
            source_id="github_release:watchlist",
            source_type="github_release",
            source_config={"display_name": "GitHub Releases"},
        ),
    ]
    return [
        _dropped(id=100 + i, dropped_at=T0 - timedelta(minutes=i), **r) for i, r in enumerate(rows)
    ]


# ---------- 관문 분류 ----------


@pytest.mark.parametrize(
    ("stage", "details", "relevance", "gate"),
    [
        ("rule", {"reason": "exclude_keyword", "matched": ["sponsored"]}, None, Gate.EXCLUDE),
        ("rule", {"reason": "exclude_domain"}, None, Gate.EXCLUDE),
        ("rule", {"reason": "dup"}, None, Gate.DEDUP),
        ("score", {"reason": "stale", "age_hours": 80}, None, Gate.STALE),
        ("triage", {"reason": "triage_error"}, None, Gate.SCREENING),
        ("score", {"breakdown": BREAKDOWN}, 0.49, Gate.SCREENING),
        ("score", {"breakdown": BREAKDOWN}, 0.5, Gate.SCORE),
        # 선별 결과가 없는 점수 탈락(옛 행)은 점수 관문이다.
        ("score", {"breakdown": BREAKDOWN}, None, Gate.SCORE),
        ("llm", {"importance": 2}, 0.9, Gate.JUDGMENT),
        (None, None, 0.9, Gate.CLUSTER_DUP),
    ],
)
def test_classify_follows_gate_table(
    stage: str | None, details: dict[str, Any] | None, relevance: float | None, gate: Gate
):
    assert classify(stage, details, relevance, floor=FLOOR) is gate


def test_dropped_item_follows_contract():
    item = _dropped()
    assert item.model_dump(mode="json") == {
        "id": "18107",
        "title": "Survey of Agentic Software Engineering",
        "url": "https://arxiv.org/abs/2609.01234",
        "source_id": "rss:arxiv-cs-se",
        "source_name": "arXiv cs.SE",
        "source_type": "rss",
        "dropped_gate": "score",
        "dropped_at": "2026-09-24T00:00:00Z",
        "relevance": 0.62,
        "kind": "survey",
        "topics": [],
        "reason": "서베이",
        "score": {"total": pytest.approx(0.29), "threshold": 0.45, "components": BREAKDOWN},
        "matched_keywords": [],
        "exploration_candidate": False,
        "restored": False,
    }


def test_pre_screening_drop_has_no_screening_fields():
    item = _dropped(
        gate_stage="rule",
        gate_details={"reason": "exclude_keyword", "matched": ["sponsored", 3]},
        triage_details=None,
        score_details=None,
    )
    assert item.dropped_gate is Gate.EXCLUDE
    assert (item.relevance, item.kind, item.topics, item.reason, item.score) == (
        None,
        None,
        [],
        None,
        None,
    )
    assert item.matched_keywords == ["sponsored"]


def test_matched_keywords_only_for_exclude():
    # 규칙 통과 행에도 matched 가 남지만 exclude 가 아니면 보이지 않는다.
    item = _dropped(gate_details={"breakdown": BREAKDOWN, "matched": ["x"]})
    assert item.matched_keywords == []


def test_cluster_dup_item_keeps_screening_and_score():
    item = _seven()[-1]
    assert item.dropped_gate is Gate.CLUSTER_DUP
    assert item.kind is Kind.RELEASE_PATCH
    assert item.topics == ["agent"]
    assert item.score is not None


# ---------- 요약 · 그룹 ----------


def test_summary_counts_add_up():
    items = _seven()
    summary = summarize(items, hours=24, collected=612, threshold=THRESHOLD)
    assert summary.filtered_total == 7
    assert summary.gate_counts == dict.fromkeys(Gate, 1)
    assert sum(summary.gate_counts.values()) == summary.filtered_total
    assert summary.borderline.count == 1
    # 0.45 − 0.10 의 부동소수 오차를 자른다.
    assert summary.model_dump(mode="json")["borderline"]["range"] == [0.35, 0.45]
    assert summary.unclassified_count == 3


def _groups(view: FilteredView, sort: GroupSort = GroupSort.COUNT_DESC, **kw: Any) -> Any:
    args = {"floor": FLOOR, "kind_weights": {}, "feedback": {}} | kw
    return build_groups(_seven(), view, sort, **args)


def test_kind_groups_sum_to_total_and_keep_cluster_dup():
    groups = _groups(FilteredView.KIND)
    assert sum(g.count for g in groups) == 7
    by_key = {g.key: g for g in groups}
    assert by_key["release_patch"].gate_counts[Gate.CLUSTER_DUP] == 1
    assert by_key[UNCLASSIFIED].count == 3
    assert by_key[UNCLASSIFIED].kind is None
    assert by_key[UNCLASSIFIED].exclude_keyword_hits == 1
    # cluster_dup 항목은 관문별 보기에서도 제 그룹이 있다.
    gate_groups = {g.key: g for g in _groups(FilteredView.GATE)}
    assert gate_groups["cluster_dup"].gate is Gate.CLUSTER_DUP
    assert gate_groups["cluster_dup"].preview[0].id == "106"


@pytest.mark.parametrize("sort", list(GroupSort))
def test_unclassified_is_always_last(sort: GroupSort):
    groups = _groups(FilteredView.KIND, sort)
    assert groups[-1].key == UNCLASSIFIED
    if sort is GroupSort.COUNT_DESC:
        # survey 3건이 unclassified 3건과 같아도 unclassified 가 뒤다.
        assert groups[0].key == "survey"
    else:
        assert [g.key for g in groups[:-1]] == ["news", "release_patch", "survey"]


def test_kind_group_stats():
    feedback = {Kind.SURVEY: KindFeedback(not_useful=4, total=4)}
    groups = _groups(
        FilteredView.KIND, kind_weights={Kind.SURVEY: -0.15, Kind.NEWS: 0.1}, feedback=feedback
    )
    by_key = {g.key: g for g in groups}
    survey = by_key["survey"]
    assert (survey.count, survey.kind_weight, survey.penalty_active) == (2, -0.15, True)
    assert survey.kind_feedback == feedback[Kind.SURVEY]
    assert survey.borderline_count == 1
    assert survey.low_relevance_ratio == 0.5
    news = by_key["news"]
    assert (news.kind_weight, news.penalty_active, news.kind_feedback) == (0.1, False, None)
    # 가중치 설정이 없는 kind 는 0.
    assert by_key["release_patch"].kind_weight == 0.0
    unclassified = by_key[UNCLASSIFIED]
    assert (unclassified.kind_weight, unclassified.low_relevance_ratio) == (None, None)


def test_source_groups_sort_and_preview():
    groups = _groups(FilteredView.SOURCE)
    assert [g.key for g in groups] == ["rss:arxiv-cs-se", "github_release:watchlist"]
    arxiv = groups[0]
    assert arxiv.source is not None and arxiv.source.display_name == "arXiv cs.SE"
    assert (arxiv.kind, arxiv.gate, arxiv.kind_weight, arxiv.kind_feedback) == (
        None,
        None,
        None,
        None,
    )
    # 최신 3건. items 가 dropped_at 내림차순이다.
    assert [p.id for p in arxiv.preview] == ["100", "101", "102"]
    by_name = _groups(FilteredView.SOURCE, GroupSort.NAME_ASC)
    assert [g.source.display_name for g in by_name] == ["arXiv cs.SE", "GitHub Releases"]


# ---------- 목록 ----------


def test_items_page_through_group():
    key = "rss:arxiv-cs-se"
    first, cursor = page_items(_seven(), FilteredView.SOURCE, key, PageParams(4, None))
    assert [it.id for it in first] == ["100", "101", "102", "103"]
    assert cursor is not None
    last = first[-1]
    after = {"t": last.dropped_at.isoformat(), "id": int(last.id)}
    rest, end = page_items(_seven(), FilteredView.SOURCE, key, PageParams(4, after))
    assert [it.id for it in rest] == ["104", "105"]
    assert end is None


def test_items_unknown_key_is_empty():
    assert page_items(_seven(), FilteredView.KIND, "nope", PageParams(20, None)) == ([], None)


# ---------- SQL ----------


def _sql(stmt: Any) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_filtered_set_sql():
    sql = _sql(filtered_set(7, since=T0).select())
    # 마지막 비사용자 결정. 복원 결정이 관문을 가리지 않는다.
    assert "DISTINCT ON (decisions.item_id)" in sql
    assert "decisions.stage != %(stage_1)s" in sql
    assert "items.status IN (__[POSTCOMPILE_status_1])" in sql
    # cluster_dup 행뿐인 SENT 항목. 복원 피드 행이 있어도 남는다.
    assert "notifications.level = %(level_1)s" in sql
    assert "notifications_1.error IS NULL" in sql
    assert "decisions.details @> %(details_1)s" in sql
    assert "HAVING max(notifications.sent_at) >= %(max_1)s" in sql
    assert "UNION ALL" in sql


def test_explore_candidate_sql_looks_at_last_decision():
    sql = _sql(explore_candidate(THRESHOLD, T0))
    assert "ORDER BY decisions_1.created_at DESC, decisions_1.id DESC" in sql
    assert "LIMIT %(param_1)s" in sql
    assert "items.score < %(score_2)s" in sql
    assert "NOT (EXISTS (SELECT summaries.item_id" in sql


# ---------- 라우터 ----------


@pytest.fixture
def window(monkeypatch: pytest.MonkeyPatch, session: Any) -> list[Any]:
    """load_dropped·collected_total 을 고정한다. 받은 인자를 남긴다."""
    calls: list[Any] = []

    async def load(_s: Any, user_id: int, since: datetime, **kw: Any) -> list[DroppedItem]:
        calls.append((user_id, kw["now"] - since, kw["floor"], kw["threshold"]))
        return _seven()

    async def collected(_s: Any, _since: datetime) -> int:
        return 612

    monkeypatch.setattr(queries, "load_dropped", load)
    monkeypatch.setattr(queries, "collected_total", collected)
    return calls


def test_summary_endpoint(client: TestClient, window: list[Any]):
    res = client.get("/api/v1/filtered/summary", params={"hours": 48}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert (body["window_hours"], body["filtered_total"], body["collected_total"]) == (48, 7, 612)
    assert body["gate_counts"]["cluster_dup"] == 1
    assert window == [(1, timedelta(hours=48), 0.5, 0.45)]


@pytest.mark.parametrize("hours", [0, 169])
def test_hours_out_of_range(client: TestClient, window: list[Any], hours: int):
    res = client.get("/api/v1/filtered/summary", params={"hours": hours}, headers=AUTH)
    assert res.status_code == 422


def test_groups_endpoint_defaults_to_source(client: TestClient, window: list[Any]):
    res = client.get("/api/v1/filtered/groups", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["view"] == "source"
    assert [g["key"] for g in body["groups"]] == ["rss:arxiv-cs-se", "github_release:watchlist"]


def test_items_endpoint(client: TestClient, window: list[Any]):
    params = {"view": "gate", "key": "cluster_dup"}
    res = client.get("/api/v1/filtered/items", params=params, headers=AUTH)
    assert res.status_code == 200
    assert [it["id"] for it in res.json()["items"]] == ["106"]
    assert client.get("/api/v1/filtered/items", headers=AUTH).status_code == 422
    bad = encode_cursor({"t": "2026-09-24T00:00:00", "id": 1})  # 시간대 없음
    res = client.get("/api/v1/filtered/items", params=params | {"cursor": bad}, headers=AUTH)
    assert res.status_code == 400


# ---------- 복원 ----------


class RestoreSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add_all(self, rows: list[Any]) -> None:
        self.added.extend(rows)

    async def flush(self) -> None:
        pass


async def test_restore_writes_feedback_decision_and_app_feed_row(monkeypatch: pytest.MonkeyPatch):
    verdicts: list[Any] = []

    async def locked(_s: Any, _u: int, _i: int) -> bool:
        return False

    async def feedback(_s: Any, user_id: int, item_id: int, verdict: str) -> None:
        verdicts.append((user_id, item_id, verdict))

    monkeypatch.setattr(queries, "_lock_filtered", locked)
    monkeypatch.setattr(queries, "set_app_feedback", feedback)
    s = RestoreSession()
    await queries.restore(s, 1, 18107)  # type: ignore[arg-type]
    assert verdicts == [(1, 18107, "useful")]
    decision, note = s.added
    assert isinstance(decision, Decision)
    assert (decision.stage, decision.passed, decision.details) == (
        "user",
        True,
        {"reason": "restored", "user_id": 1},
    )
    # 앱 피드 행 하나뿐이다. 어느 채널로도 보내지 않는다.
    assert isinstance(note, Notification)
    assert (note.user_id, note.item_id, note.channel, note.level) == (1, 18107, "app", "feed")


async def test_restore_again_changes_nothing(monkeypatch: pytest.MonkeyPatch):
    async def locked(_s: Any, _u: int, _i: int) -> bool:
        return True

    monkeypatch.setattr(queries, "_lock_filtered", locked)
    s = RestoreSession()
    await queries.restore(s, 1, 18107)  # type: ignore[arg-type]
    assert s.added == []
