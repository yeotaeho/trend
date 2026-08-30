# 점수화 테스트 — freshness 감쇠, hotness 포화, 임계값 통과 판정

from datetime import UTC, datetime, timedelta

from app.config import ScoringConfig
from app.pipeline.scoring import freshness, hotness, score_item

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


def test_trusted_fresh_keyworded_item_passes():
    result = score_item(
        CFG,
        trust=1.0,
        keyword_hits=3,
        metrics={},
        mention_count=1,
        published_at=NOW - timedelta(hours=1),
        now=NOW,
    )
    assert result.passed
    assert result.score == CFG.w_src + CFG.w_kw + CFG.w_fresh


def test_weak_item_drops():
    result = score_item(
        CFG,
        trust=0.3,
        keyword_hits=1,
        metrics={},
        mention_count=1,
        published_at=NOW - timedelta(days=6),
        now=NOW,
    )
    assert not result.passed


def test_multi_source_mentions_lift_score():
    kwargs = {
        "trust": 0.5,
        "keyword_hits": 1,
        "metrics": {},
        "published_at": NOW,
        "now": NOW,
    }
    one = score_item(CFG, mention_count=1, **kwargs).score
    three = score_item(CFG, mention_count=3, **kwargs).score
    assert three == one + CFG.w_multi
