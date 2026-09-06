# 소스 신뢰도 보정과 리포트 집계 — 베이즈 평활(사전 가중치 10), 정밀도, 점수 구간

from __future__ import annotations

import math


def adjust_trust(base: float, useful: int, useless: int, *, prior_weight: int = 10) -> float:
    """라벨 0건이면 base 그대로, 10건이면 원래 값과 데이터가 반반. [0.2, 1.0] 으로 자른다."""
    value = (prior_weight * base + useful) / (prior_weight + useful + useless)
    return round(min(1.0, max(0.2, value)), 4)


def precision(useful: int, useless: int) -> float | None:
    """라벨이 하나도 없으면 None. 0 으로 나누지 않는다."""
    total = useful + useless
    return round(useful / total, 2) if total else None


def score_band(score: float, width: float = 0.05) -> float:
    # 0.45 / 0.05 = 8.999… 로 떨어지는 부동소수 오차를 막기 위해 소수 9자리에서 자른다.
    return round(math.floor(round(score / width, 9)) * width, 2)
