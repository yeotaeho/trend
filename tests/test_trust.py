# 신뢰도 보정·리포트 집계 테스트 — 라벨 0건이면 원값, 10건이면 반반, 클램프, 정밀도, 구간, 구간 합산

from app.pipeline.trust import adjust_trust, band_table, precision, score_band


def test_no_labels_keeps_base():
    assert adjust_trust(0.7, 0, 0) == 0.7


def test_ten_labels_split_evenly_with_prior():
    # (10*0.5 + 10) / (10 + 10) = 0.75
    assert adjust_trust(0.5, 10, 0) == 0.75


def test_clamped_to_range():
    assert adjust_trust(0.2, 0, 50) == 0.2
    assert adjust_trust(1.0, 50, 0) == 1.0


def test_precision_none_without_labels():
    assert precision(0, 0) is None
    assert precision(3, 1) == 0.75


def test_score_band_floors_to_width():
    assert score_band(0.449) == 0.40
    assert score_band(0.45) == 0.45
    assert score_band(0.999) == 0.95


def test_band_table_sums_rows_per_band():
    rows = [(0.46, "useful"), (0.47, "useless"), (0.49, None), (0.51, "useful"), (0.44, None)]
    assert band_table(rows) == [
        (0.40, 1, 0, 0, None),
        (0.45, 3, 1, 1, 0.5),
        (0.50, 1, 1, 0, 1.0),
    ]
