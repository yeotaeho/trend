# 발송 정책 테스트 — 중요도별 강도·자정을 넘기는 무음 시간·push 상한·클러스터 상한·제목 병기

from datetime import UTC, datetime

import pytest

from app.config import DeliveryByImportanceConfig, NotifyConfig
from app.notify import policy
from app.notify.policy import decide, decorate_title, delivery_for, in_quiet_hours, sibling_versions
from app.schemas import Level

CFG = NotifyConfig()  # 23:00~08:00 KST


def kst(hour: int) -> datetime:
    """KST 기준 시각을 UTC datetime 으로 (KST = UTC+9)."""
    return datetime(2026, 8, 30, (hour - 9) % 24, 0, tzinfo=UTC)


def test_default_delivery_by_importance():
    assert [delivery_for(CFG, i) for i in (5, 4, 3, 2, 1)] == [
        "instant",
        "instant",
        "quiet",
        "feed_only",
        "feed_only",
    ]


def test_quiet_hours_wraps_midnight():
    assert in_quiet_hours(CFG, kst(23))
    assert in_quiet_hours(CFG, kst(3))
    assert in_quiet_hours(CFG, kst(7))


def test_daytime_is_not_quiet():
    assert not in_quiet_hours(CFG, kst(8))
    assert not in_quiet_hours(CFG, kst(14))
    assert not in_quiet_hours(CFG, kst(22))


def test_disabled_when_start_equals_end():
    cfg = NotifyConfig(quiet_start_hour=0, quiet_end_hour=0)
    assert not in_quiet_hours(cfg, kst(3))


# ---------- decide ----------


class Counts:
    """decide 가 부르는 DB 집계 두 개를 대신한다. 불린 횟수를 센다."""

    def __init__(self, push: int = 0, cluster: int = 0) -> None:
        self.push, self.cluster = push, cluster
        self.push_calls = self.cluster_calls = 0

    async def push_count_today(self, *_):
        self.push_calls += 1
        return self.push

    async def cluster_sent_today(self, *_):
        self.cluster_calls += 1
        return self.cluster


@pytest.fixture
def counts(monkeypatch):
    c = Counts()
    monkeypatch.setattr(policy, "push_count_today", c.push_count_today)
    monkeypatch.setattr(policy, "cluster_sent_today", c.cluster_sent_today)
    return c


async def run(cfg: NotifyConfig, importance: int, hour: int = 14, cluster_id: int | None = 1):
    return await decide(
        None, cfg, importance=importance, cluster_id=cluster_id, user_id=1, now=kst(hour)
    )


async def test_mapping_change_is_applied(counts):
    cfg = NotifyConfig(delivery_by_importance=DeliveryByImportanceConfig(mid="feed_only"))
    verdict = await run(cfg, 3)
    assert (verdict.level, verdict.reason) == (Level.FEED, "feed_only")
    assert counts.cluster_calls == 0

    verdict = await run(NotifyConfig(), 3)
    assert verdict.level is Level.SILENT


async def test_quiet_hours_push_is_feed_only_without_cluster_check(counts):
    counts.cluster = 5
    verdict = await run(CFG, 5, hour=2)
    assert (verdict.level, verdict.reason) == (Level.FEED, "quiet_hours")
    assert counts.cluster_calls == 0 and counts.push_calls == 0


async def test_daily_cap_demotes_push_to_silent(counts):
    counts.push = CFG.daily_push_cap
    verdict = await run(CFG, 4)
    assert (verdict.level, verdict.reason) == (Level.SILENT, "daily_cap")


async def test_cluster_cap_suppresses_push_and_silent(counts):
    counts.cluster = 1
    for importance in (5, 3):
        verdict = await run(CFG, importance)
        assert (verdict.level, verdict.reason) == (Level.CLUSTER_DUP, "cluster_dup")


async def test_cluster_below_cap_sends(counts):
    counts.cluster = 1
    verdict = await run(NotifyConfig(cluster_daily_cap=2), 4)
    assert (verdict.level, verdict.reason) == (Level.PUSH, "ok")


async def test_cluster_cap_zero_or_no_cluster_skips_check(counts):
    counts.cluster = 9
    assert (await run(NotifyConfig(cluster_daily_cap=0), 4)).level is Level.PUSH
    assert (await run(CFG, 4, cluster_id=None)).level is Level.PUSH
    assert counts.cluster_calls == 0


# ---------- 제목 병기 ----------


def test_sibling_versions_collects_distinct_tokens_in_order():
    vs = sibling_versions(
        "MCP Python SDK v2.2.0 released", ["MCP Python SDK v1.30.0 released", "v2.2.0 notes"]
    )
    assert vs == ["v2.2.0", "v1.30.0"]


def test_decorate_title_appends_versions_once():
    t = decorate_title(
        "[릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경", ["v2.2.0", "v1.30.0"]
    )
    assert t.endswith("(v2.2.0 · v1.30.0)")
    assert t.count("(v2.2.0 · v1.30.0)") == 1


def test_decorate_title_noop_for_single_version():
    assert decorate_title("x", ["v1"]) == "x"
    assert decorate_title("x", []) == "x"
