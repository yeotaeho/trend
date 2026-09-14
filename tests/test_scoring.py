# 점수화 테스트 — freshness 감쇠, hotness 포화, 신뢰도별 통과 관련도, stale 경계, 되살림 변화량

import math
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.config import ScoringConfig
from app.pipeline.scoring import (
    freshness,
    hotness,
    is_stale,
    merged_mentions,
    revive_gain,
    score_item,
    score_terms,
)
from app.schemas import Kind

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
        kind=Kind.NEWS,
        metrics={},
        mention_count=1,
        published_at=NOW - timedelta(hours=1),
        now=NOW,
    )
    assert result.passed
    assert result.score == CFG.w_src + CFG.w_rel + CFG.w_fresh


@pytest.mark.parametrize(
    ("trust", "needed"),
    [(1.0, 0.5), (0.9, 0.6), (0.8, 0.65), (0.7, 0.7), (0.6, 0.8), (0.5, 0.85)],
)
def test_relevance_needed_to_pass_alone_within_a_day(trust, needed):
    """hot·multi 없이 24시간 이내면 rel ≥ (0.35 − 0.2·trust) / 0.3.

    2026-09-10 조정 (w_src 0.20 · w_rel 0.30). arXiv(0.5) 는 0.85 부터 통과해
    관련도 0.8 대 논문만 판정으로 간다 — 실측 2.5일에 28건.
    """

    def score(rel):
        return score_item(
            CFG,
            trust=trust,
            relevance=rel,
            kind=Kind.NEWS,
            metrics={},
            mention_count=1,
            published_at=NOW,
            now=NOW,
        )

    assert score(needed).passed
    assert not score(needed - 0.05).passed


def test_weak_item_drops():
    result = score_item(
        CFG,
        trust=0.3,
        relevance=0.3,
        kind=Kind.NEWS,
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
        "kind": Kind.NEWS,
        "metrics": {},
        "published_at": NOW,
        "now": NOW,
    }
    one = score_item(CFG, mention_count=1, **kwargs).score
    three = score_item(CFG, mention_count=3, **kwargs).score
    assert three == pytest.approx(one + CFG.w_multi)


def test_stale_boundary():
    assert not is_stale(NOW - timedelta(hours=71), 72, now=NOW)
    assert is_stale(NOW - timedelta(hours=73), 72, now=NOW)


def _arxiv(kind: Kind):
    return score_item(
        CFG,
        trust=0.5,
        relevance=0.9,
        kind=kind,
        metrics={},
        mention_count=1,
        published_at=NOW,
        now=NOW,
    )


def test_kind_weight_is_added_not_multiplied():
    base, survey = _arxiv(Kind.NEWS), _arxiv(Kind.SURVEY)
    assert survey.breakdown["kind"] == CFG.kind_weights[Kind.SURVEY]
    assert survey.score == pytest.approx(base.score + CFG.kind_weights[Kind.SURVEY])


def test_arxiv_survey_drops_where_news_passes():
    """2026-09-08 SDLC 서베이 사례. trust 0.5 · rel 0.9 · 24h 이내: news 통과, survey 탈락."""
    assert _arxiv(Kind.NEWS).passed
    assert not _arxiv(Kind.SURVEY).passed


def test_kind_without_weight_is_neutral():
    assert _arxiv(Kind.OTHER).breakdown["kind"] == 0.0


def test_unknown_kind_in_weights_is_rejected():
    with pytest.raises(ValidationError):
        ScoringConfig(kind_weights={"nope": 0.1})


def test_merged_mentions_takes_larger_side_and_tolerates_missing():
    """벡터 관련 소스 수(자기 포함)와 적재 병합의 raw.mentions(자기 제외) 중 큰 쪽."""
    assert merged_mentions(1, {"mentions": ["a", "b"]}) == 3
    assert merged_mentions(3, {"mentions": ["a"]}) == 3
    assert merged_mentions(2, {}) == 2
    assert merged_mentions(1, None) == 1
    assert merged_mentions(1, {"mentions": "bad"}) == 1


def test_score_terms_matches_score_item_breakdown():
    """score_terms 는 score_item 의 hot·multi 항과 같은 눈금이어야 한다."""
    hot, multi = score_terms(CFG, {"points": 50.0}, 2)
    result = score_item(
        CFG,
        trust=0.5,
        relevance=0.5,
        kind=Kind.NEWS,
        metrics={"points": 50.0},
        mention_count=3,  # score_terms 의 mentions=2 는 자기 소스를 뺀 값
        published_at=NOW,
        now=NOW,
    )
    assert hot == pytest.approx(result.breakdown["hot"])
    assert multi == pytest.approx(result.breakdown["multi"])


def test_revive_gain_is_zero_without_change():
    base_hot, base_multi = score_terms(CFG, {"points": 10.0}, 0)
    gain = revive_gain(CFG, {"points": 10.0}, 0, base_hot=base_hot, base_multi=base_multi)
    assert gain == 0.0


def test_revive_gain_is_zero_once_hotness_is_saturated():
    """1000 도 1075 도 로그 스케일에서 이미 1.0 이라 hot 항이 오르지 않는다."""
    base_hot, base_multi = score_terms(CFG, {"points": 1000.0}, 0)
    gain = revive_gain(CFG, {"points": 1075.0}, 0, base_hot=base_hot, base_multi=base_multi)
    assert gain == pytest.approx(0.0)


def test_revive_gain_from_hotness_climb():
    base_hot, base_multi = score_terms(CFG, {"points": 10.0}, 0)
    gain = revive_gain(CFG, {"points": 400.0}, 0, base_hot=base_hot, base_multi=base_multi)
    expected = CFG.w_hot * (math.log1p(400) - math.log1p(10)) / math.log1p(500)
    assert gain == pytest.approx(expected)


def test_revive_gain_from_new_mention():
    base_hot, base_multi = score_terms(CFG, {"points": 10.0}, 0)
    gain = revive_gain(CFG, {"points": 10.0}, 1, base_hot=base_hot, base_multi=base_multi)
    assert gain == pytest.approx(0.1)


def test_revive_gain_from_mentions_is_capped_at_two():
    base_hot, base_multi = score_terms(CFG, {"points": 10.0}, 2)
    gain = revive_gain(CFG, {"points": 10.0}, 3, base_hot=base_hot, base_multi=base_multi)
    assert gain == pytest.approx(0.0)


def test_revive_gain_accumulates_regardless_of_intermediate_observation():
    """기준이 마지막 점수 결정의 breakdown 이라, 중간 관측(30→200 등)과 무관하게 누적된다.

    HN 점수가 폴링마다 조금씩(30 → 500) 올라도 매번 직전 관측과 비교하면 각 이득이 작아
    임계값을 못 넘는다. 기준을 마지막 점수 결정에 고정해야 총 누적분(약 0.0895)이 온전히 잡힌다.
    """
    base_hot, base_multi = score_terms(CFG, {"points": 30.0}, 0)
    gain = revive_gain(CFG, {"points": 500.0}, 0, base_hot=base_hot, base_multi=base_multi)
    expected = CFG.w_hot * (math.log1p(500) - math.log1p(30)) / math.log1p(500)
    assert gain == pytest.approx(expected)
