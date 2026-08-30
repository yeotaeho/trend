# 점수화 (2단계 관문) — trust·keyword·hotness·multi·freshness 가중합

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from app.config import ScoringConfig

FRESH_HALF_LIFE_HOURS = 24.0
HOTNESS_SATURATION = 500.0  # points/stars 가 이 정도면 hotness 1.0 에 근접
HOTNESS_KEYS = ("points", "stars", "upvotes", "comments")


@dataclass(slots=True)
class ScoreResult:
    score: float
    passed: bool
    breakdown: dict[str, float]


def freshness(published_at: datetime, *, now: datetime | None = None) -> float:
    """24시간 이내 1.0, 이후 24시간마다 절반으로 감쇠."""
    now = now or datetime.now(UTC)
    hours = (now - published_at).total_seconds() / 3600
    if hours <= FRESH_HALF_LIFE_HOURS:
        return 1.0
    return float(0.5 ** ((hours - FRESH_HALF_LIFE_HOURS) / FRESH_HALF_LIFE_HOURS))


def hotness(metrics: dict[str, float]) -> float:
    """소스마다 단위가 달라 로그 스케일로 0~1 에 눌러 담는다."""
    raw = max((float(metrics.get(key, 0)) for key in HOTNESS_KEYS), default=0.0)
    if raw <= 0:
        return 0.0
    return min(1.0, math.log1p(raw) / math.log1p(HOTNESS_SATURATION))


def score_item(
    cfg: ScoringConfig,
    *,
    trust: float,
    keyword_hits: int,
    metrics: dict[str, float],
    mention_count: int,
    published_at: datetime,
    now: datetime | None = None,
) -> ScoreResult:
    breakdown = {
        "src": cfg.w_src * trust,
        "kw": cfg.w_kw * min(keyword_hits, 3) / 3,
        "hot": cfg.w_hot * hotness(metrics),
        "multi": cfg.w_multi * min(max(mention_count - 1, 0), 2) / 2,
        "fresh": cfg.w_fresh * freshness(published_at, now=now),
    }
    total = sum(breakdown.values())
    return ScoreResult(total, total >= cfg.threshold, breakdown)
