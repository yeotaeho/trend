# 호출 예산 테스트 — 서울 달력일 시작 시각과 예산·kind 대응

from datetime import UTC, datetime

from app.db.budget import BUDGETS, budget_for, today_start


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
