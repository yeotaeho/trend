# 호출 예산 테스트 — 서울 달력일 시작 시각, 예산·kind 대응, 오늘 사용량 집계

from datetime import UTC, datetime
from types import SimpleNamespace

from app.db.budget import BUDGETS, BudgetUsage, budget_for, today_start, usage_today


def test_today_start_is_seoul_midnight_in_utc():
    # KST 2026-09-06 00:30 = UTC 09-05 15:30. 그날의 시작은 UTC 09-05 15:00.
    now = datetime(2026, 9, 5, 15, 30, tzinfo=UTC)
    assert today_start("Asia/Seoul", now) == datetime(2026, 9, 5, 15, 0, tzinfo=UTC)


def test_before_seoul_midnight_belongs_to_previous_day():
    now = datetime(2026, 9, 5, 14, 30, tzinfo=UTC)  # KST 09-05 23:30
    assert today_start("Asia/Seoul", now) == datetime(2026, 9, 4, 15, 0, tzinfo=UTC)


def test_explore_shares_judge_budget():
    assert budget_for("explore") == ("judge", ("judge", "explore"))
    assert budget_for("triage") == ("triage", ("triage",))
    assert set(BUDGETS) == {"triage", "judge"}


class _UsageSession:
    """usage_today 의 두 쿼리(DB 시각, kind 별 집계) 결과를 차례로 돌려준다."""

    def __init__(self, counts: list[tuple[str, int]]) -> None:
        self.results = [
            SimpleNamespace(scalar_one=lambda: datetime(2026, 9, 24, 2, 0, tzinfo=UTC)),
            SimpleNamespace(tuples=lambda: counts),
        ]

    async def execute(self, _stmt):
        return self.results.pop(0)


async def test_usage_today_counts_like_reserve_call(monkeypatch):
    monkeypatch.setattr("app.db.budget._caps", lambda: {"triage": 60, "judge": 300, "explore": 3})
    session = _UsageSession([("triage", 41), ("judge", 17), ("explore", 1)])

    usage = await usage_today(session)

    # 판정 예산은 탐색 판정까지 센다 (reserve_call 과 같은 기준).
    assert usage == {
        "triage": BudgetUsage(41, 60),
        "judge": BudgetUsage(18, 300),
        "explore": BudgetUsage(1, 3),
    }


async def test_usage_today_is_zero_without_calls(monkeypatch):
    monkeypatch.setattr("app.db.budget._caps", lambda: {"triage": 60, "judge": 300, "explore": 3})

    usage = await usage_today(_UsageSession([]))

    assert {name: u.used for name, u in usage.items()} == {"triage": 0, "judge": 0, "explore": 0}
