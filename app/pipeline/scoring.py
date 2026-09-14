# 점수화 — trust·relevance·hotness·multi·freshness 가중합, 전역 신선도 가드

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import ScoringConfig
from app.schemas import Kind

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


def revive_gain(
    cfg: ScoringConfig,
    old_metrics: dict[str, float],
    new_metrics: dict[str, float],
    old_mentions: int,
    new_mentions: int,
) -> float:
    """재관측으로 점수가 최대 얼마나 오를 수 있나. hot·multi 항의 변화량만 더한다.

    되살림은 이 값이 임계값까지의 거리 이상일 때만 한다. 몇 점 오른 재관측(HN 10분 폴링)은
    거의 0 이라 결정 행을 쌓지 않고, 포화된 hotness 는 0 이라 영원히 되살아나지 않는다.
    mentions 는 자기 소스를 뺀 개수다. score_item 의 multi 항과 같은 눈금이다.
    """
    hot = cfg.w_hot * (hotness(new_metrics) - hotness(old_metrics))
    multi = cfg.w_multi * (min(new_mentions, 2) - min(old_mentions, 2)) / 2
    return hot + multi


def is_stale(published_at: datetime, max_age_hours: int, *, now: datetime | None = None) -> bool:
    """전역 신선도 가드. 선별 호출 앞에 둬서 백필·오래된 항목이 예산을 쓰지 않게 한다."""
    return (now or datetime.now(UTC)) - published_at > timedelta(hours=max_age_hours)


def merged_mentions(embedding_mentions: int, raw: object) -> int:
    """벡터 관련 소스 수와 적재 병합이 기록한 raw.mentions 중 큰 쪽.

    둘 다 자기 소스 1 을 포함한 값으로 맞춘다. mentions 는 자기 소스를 뺀 목록이라 1 을 더한다.
    """
    mentions = raw.get("mentions") if isinstance(raw, dict) else None
    extra = len(mentions) if isinstance(mentions, list) else 0
    return max(embedding_mentions, 1 + extra)


def score_item(
    cfg: ScoringConfig,
    *,
    trust: float,
    relevance: float,
    kind: Kind,
    metrics: dict[str, float],
    mention_count: int,
    published_at: datetime,
    now: datetime | None = None,
) -> ScoreResult:
    breakdown = {
        "src": cfg.w_src * trust,
        "rel": cfg.w_rel * relevance,
        "hot": cfg.w_hot * hotness(metrics),
        "multi": cfg.w_multi * min(max(mention_count - 1, 0), 2) / 2,
        "fresh": cfg.w_fresh * freshness(published_at, now=now),
        # 가중치 곱이 아니라 덧셈. 설정에 없는 kind 는 영향 없음.
        "kind": cfg.kind_weights.get(kind, 0.0),
    }
    total = sum(breakdown.values())
    # 부동소수 합이 0.4499999 로 떨어져 경계 케이스가 어긋나지 않게 소수 6자리에서 비교한다.
    return ScoreResult(total, round(total, 6) >= cfg.threshold, breakdown)
