# 주간 리포트 테스트 — 지난주 기간·제목, 셀 변환, 표 여덟 개 조립, upsert 문, 스크립트 출력 형식

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import postgresql

from app.jobs import report
from app.jobs.report import (
    SECTION_KEYS,
    build_sections,
    cell,
    last_week,
    report_title,
    report_upsert_stmt,
    save_report,
)
from scripts import weekly_report as script

SEOUL = ZoneInfo("Asia/Seoul")


class Result:
    def __init__(self, keys: list[str], rows: list[Any]) -> None:
        self._keys = keys
        self._rows = rows

    def keys(self) -> list[str]:
        return self._keys

    def all(self) -> list[Any]:
        return self._rows


class FakeSession:
    """문장마다 정해 둔 결과를 돌려준다. 정해 두지 않은 문장(upsert·UPDATE)은 기록만 한다."""

    def __init__(self) -> None:
        src = SimpleNamespace(
            name="rss:a", trust_score=0.5, trust_adjusted=None, sent=3, useful=2, useless=1
        )
        label = SimpleNamespace(id=7, name="rss:a", trust_score=0.5, useful=2, useless=1)
        self.results: dict[Any, Result] = {
            report.FUNNEL: Result(
                ["stage", "passed", "reason", "n"],
                [("rule", False, "dup", 4), ("triage", True, None, 9)],
            ),
            report.DROP_REASONS: Result(
                ["stage", "reason", "n"], [("score", "below_threshold", 5)]
            ),
            report.BY_SOURCE: Result([], [src]),
            report.BY_IMPORTANCE: Result(["importance", "sent", "useful", "useless"], []),
            report.BY_SCORE_ROWS: Result(
                [],
                [
                    SimpleNamespace(score=0.47, verdict="useful"),
                    SimpleNamespace(score=0.52, verdict=None),
                ],
            ),
            report.TRIAGE_VS_JUDGE: Result(
                ["band", "triaged", "judged_true", "judged_false"], [(Decimal("0.6"), 8, 3, 1)]
            ),
            report.LOW_RELEVANCE_SAMPLES: Result(
                ["source", "title", "relevance", "reason"], [("rss:a", "제목", 0.2, "무관")]
            ),
            report.TRUST_LABELS: Result([], [label]),
        }
        self.calls: list[tuple[Any, dict[str, Any] | None]] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> Result:
        self.calls.append((stmt, params))
        return self.results.get(stmt, Result([], []))


def test_last_week_is_previous_monday_to_sunday():
    monday = date(2026, 9, 21)
    for today in (monday + timedelta(days=d) for d in range(7)):
        assert last_week(today) == (date(2026, 9, 14), date(2026, 9, 20)), today
    assert last_week(date(2026, 9, 20)) == (date(2026, 9, 7), date(2026, 9, 13))


@pytest.mark.parametrize(
    ("start", "title"),
    [
        (date(2026, 9, 8), "9월 2주차 리포트"),  # 계약 예시
        (date(2026, 9, 1), "9월 1주차 리포트"),
        (date(2026, 9, 6), "9월 1주차 리포트"),
        (date(2026, 9, 7), "9월 2주차 리포트"),
        (date(2026, 9, 28), "9월 5주차 리포트"),
        (date(2026, 6, 1), "6월 1주차 리포트"),  # 1일이 월요일
        (date(2026, 11, 2), "11월 2주차 리포트"),  # 1일이 일요일
        (date(2026, 8, 31), "8월 6주차 리포트"),
    ],
)
def test_title_is_calendar_row_of_start(start: date, title: str):
    assert report_title(start) == title


def test_cell_keeps_json_values():
    assert [cell(v) for v in ("a", True, 3, 0.5, None)] == ["a", True, 3, 0.5, None]
    assert cell(Decimal("0.6")) == 0.6 and isinstance(cell(Decimal("0.6")), float)
    assert cell(date(2026, 9, 8)) == "2026-09-08"


async def test_build_sections_has_eight_tables_in_order():
    session = FakeSession()
    until = datetime(2026, 9, 21, tzinfo=SEOUL)
    since = until - timedelta(days=7)
    sections = await build_sections(session, since, until)  # type: ignore[arg-type]

    assert tuple(sections) == SECTION_KEYS and len(sections) == 8
    assert sections["funnel"]["rows"] == [["rule", False, "dup", 4], ["triage", True, None, 9]]
    assert sections["by_source"]["rows"] == [["rss:a", 0.5, None, 3, 2, 1, 0.67]]
    assert sections["by_importance"] == {
        "title": "importance 별 발송·👍·👎",
        "columns": ["importance", "sent", "useful", "useless"],
        "rows": [],
    }
    assert sections["by_score_band"]["rows"] == [[0.45, 1, 1, 0, 1.0], [0.5, 1, 0, 0, None]]
    assert sections["triage_vs_judge"]["rows"] == [[0.6, 8, 3, 1]]
    assert sections["trust_adjust"]["rows"] == [["rss:a", 0.5, 2, 1, 0.5385]]

    params = {id(stmt): p for stmt, p in session.calls}
    assert params[id(report.FUNNEL)] == {"since": since, "until": until}
    # 신뢰도 보정만 until 까지 최근 30일 라벨이다.
    assert params[id(report.TRUST_LABELS)] == {"since": until - timedelta(days=30), "until": until}


def test_window_sql_is_bounded_on_both_sides():
    for stmt in (
        report.FUNNEL,
        report.DROP_REASONS,
        report.BY_SOURCE,
        report.BY_IMPORTANCE,
        report.BY_SCORE_ROWS,
        report.TRIAGE_VS_JUDGE,
        report.LOW_RELEVANCE_SAMPLES,
        report.TRUST_LABELS,
    ):
        sql = str(stmt)
        assert ">= :since" in sql and "< :until" in sql
        assert "now()" not in sql


def test_upsert_overwrites_same_week():
    stmt = report_upsert_stmt(1, date(2026, 9, 14), date(2026, 9, 20), {"funnel": {}})  # type: ignore[dict-item]
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT ON CONSTRAINT uq_weekly_reports_user_period DO UPDATE" in sql
    for col in ("period_end", "title", "subtitle", "sections", "created_at"):
        assert f"{col} = " in sql.split("DO UPDATE")[1], col
    params = stmt.compile(dialect=postgresql.dialect()).params
    assert params["title"] == "9월 3주차 리포트"
    assert params["subtitle"] == report.SUBTITLE


async def test_save_report_uses_local_midnights():
    session = FakeSession()
    start = await save_report(session, 1, date(2026, 9, 21), "Asia/Seoul")  # type: ignore[arg-type]

    assert start == date(2026, 9, 14)
    params = {id(stmt): p for stmt, p in session.calls}
    assert params[id(report.FUNNEL)] == {
        "since": datetime(2026, 9, 14, tzinfo=SEOUL),
        "until": datetime(2026, 9, 21, tzinfo=SEOUL),
    }
    upsert, _ = session.calls[-1]
    compiled = upsert.compile(dialect=postgresql.dialect()).params
    assert (compiled["period_start"], compiled["period_end"]) == (
        date(2026, 9, 14),
        date(2026, 9, 20),
    )
    assert set(compiled["sections"]) == set(SECTION_KEYS)


async def test_script_prints_same_tables(monkeypatch: pytest.MonkeyPatch, capsys: Any):
    """리팩터 전 스크립트와 같은 표 모양: '## 제목', 'a | b' 머리줄, str() 셀, 빈 표는 (없음)."""
    session = FakeSession()

    @asynccontextmanager
    async def scope() -> Any:
        yield session

    async def dispose() -> None:
        return None

    monkeypatch.setattr(script, "session_scope", scope)
    monkeypatch.setattr(script, "engine", SimpleNamespace(dispose=dispose))
    await script.main(7, apply=False)

    assert capsys.readouterr().out == (
        "# 최근 7일 발송 코호트 (피드백은 도착 시점 무관)\n"
        "\n## 관문별 깔때기\nstage | passed | reason | n\nrule | False | dup | 4\n"
        "triage | True | None | 9\n"
        "\n## 탈락 사유 상위 10\nstage | reason | n\nscore | below_threshold | 5\n"
        "\n## 소스별 발송·👍·👎·정밀도\n"
        "source | trust | adjusted | sent | useful | useless | precision\n"
        "rss:a | 0.5 | None | 3 | 2 | 1 | 0.67\n"
        "\n## importance 별 발송·👍·👎\n(없음)\n"
        "\n## 점수 구간별 발송·👍·👎·정밀도 (탐색 포함)\n"
        "band | sent | useful | useless | precision\n"
        "0.45 | 1 | 1 | 0 | 1.0\n0.5 | 1 | 0 | 0 | None\n"
        "\n## 선별 relevance 구간 vs 판정\nband | triaged | judged_true | judged_false\n"
        "0.6 | 8 | 3 | 1\n"
        "\n## 저관련도 선별 이유 표본 10\nsource | title | relevance | reason\n"
        "rss:a | 제목 | 0.2 | 무관\n"
        "\n## 신뢰도 보정 (최근 30일 라벨, 활성 소스)\n"
        "source | base | useful | useless | adjusted\nrss:a | 0.5 | 2 | 1 | 0.5385\n"
        "\n(드라이런. --apply 로 sources.trust_adjusted 에 씀)\n"
    )
    # 드라이런은 저장하지 않는다.
    assert all(stmt in session.results for stmt, _ in session.calls)


async def test_script_apply_writes_trust_only(monkeypatch: pytest.MonkeyPatch, capsys: Any):
    session = FakeSession()

    @asynccontextmanager
    async def scope() -> Any:
        yield session

    async def dispose() -> None:
        return None

    monkeypatch.setattr(script, "session_scope", scope)
    monkeypatch.setattr(script, "engine", SimpleNamespace(dispose=dispose))
    await script.main(7, apply=True)

    writes = [(str(stmt), p) for stmt, p in session.calls if stmt not in session.results]
    assert writes == [
        ("UPDATE sources SET trust_adjusted = :v WHERE id = :id", {"v": 0.5385, "id": 7})
    ]
    assert "(--apply: 1개 소스의 trust_adjusted 를 커밋함)" in capsys.readouterr().out


async def test_run_weekly_report_uses_rules_timezone(monkeypatch: pytest.MonkeyPatch):
    seen: dict[str, Any] = {}

    @asynccontextmanager
    async def scope() -> Any:
        yield "session"

    async def save(session: Any, user_id: int, today: date, tz: str) -> date:
        seen.update(session=session, user_id=user_id, today=today, tz=tz)
        return today

    monkeypatch.setattr(report, "session_scope", scope)
    monkeypatch.setattr(report, "save_report", save)
    await report.run_weekly_report()

    assert seen["tz"] == "Asia/Seoul" and seen["user_id"] == 1
    assert seen["today"] == datetime.now(UTC).astimezone(SEOUL).date()
