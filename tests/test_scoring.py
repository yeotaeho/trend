# 점수화 테스트 — freshness 감쇠, hotness 포화, 신뢰도별 통과 관련도, stale 경계

from datetime import UTC, datetime, timedelta

import pytest

from app.config import ScoringConfig
from app.pipeline.scoring import freshness, hotness, is_stale, score_item

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
CFG = ScoringConfig()


def test_freshness_full_within_a_day():
    assert freshness(NOW - timedelta(hours=5), now=NOW) == 1.0


def test_freshness_halves_after_two_days():
    assert freshness(NOW - timedelta(hours=48), now=NOW) == 0.5


def test_hotness_zero_without_metrics():
    assert hotness({}) == 0.0


def test_hotness_monotonic_and_bounded():
    assert 0 < hotness({"points": 30}) < hotness({"points": 300}) <= 1.0


def test_trusted_fresh_relevant_item_passes():
    result = score_item(
        CFG,
        trust=1.0,
        relevance=1.0,
        metrics={},
        mention_count=1,
        published_at=NOW - timedelta(hours=1),
        now=NOW,
    )
    assert result.passed
    assert result.score == CFG.w_src + CFG.w_rel + CFG.w_fresh


@pytest.mark.parametrize(
    ("trust", "needed"),
    [(1.0, 0.4), (0.9, 0.5), (0.8, 0.6), (0.7, 0.7), (0.6, 0.8), (0.5, 0.9)],
)
def test_relevance_needed_to_pass_alone_within_a_day(trust, needed):
    """설계서 §8 의 표. hot·multi 없이 24시간 이내면 rel ≥ 1.4 − trust."""

    def score(rel):
        return score_item(
            CFG, trust=trust, relevance=rel, metrics={}, mention_count=1, published_at=NOW, now=NOW
        )

    assert score(needed).passed
    assert not score(needed - 0.05).passed


def test_weak_item_drops():
    result = score_item(
        CFG,
        trust=0.3,
        relevance=0.3,
        metrics={},
        mention_count=1,
        published_at=NOW - timedelta(days=6),
        now=NOW,
    )
    assert not result.passed


def test_multi_source_mentions_lift_score():
    kwargs = {
        "trust": 0.5,
        "relevance": 0.3,
        "metrics": {},
        "published_at": NOW,
        "now": NOW,
    }
    one = score_item(CFG, mention_count=1, **kwargs).score
    three = score_item(CFG, mention_count=3, **kwargs).score
    assert three == one + CFG.w_multi


def test_stale_boundary():
    assert not is_stale(NOW - timedelta(hours=71), 72, now=NOW)
    assert is_stale(NOW - timedelta(hours=73), 72, now=NOW)
