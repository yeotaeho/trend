# 수집 잡 순수 함수 테스트 — 첫 폴링은 신선도 창만 본다

from datetime import UTC, datetime, timedelta

from app.jobs.collect import poll_since

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def test_returns_last_polled_at_when_present():
    last = NOW - timedelta(minutes=15)
    assert poll_since(last, 72, now=NOW) == last


def test_first_poll_uses_freshness_window():
    """새 RSS 를 붙일 때 피드 전체(수백 건)를 임베딩하고 stale 로 버리는 낭비를 막는다."""
    assert poll_since(None, 72, now=NOW) == NOW - timedelta(hours=72)
