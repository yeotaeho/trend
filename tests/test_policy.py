# 발송 정책 테스트 — 중요도별 강도와 자정을 넘기는 무음 시간

from datetime import UTC, datetime

from app.config import NotifyConfig
from app.notify.policy import in_quiet_hours, level_for
from app.schemas import Level

CFG = NotifyConfig()  # 23:00~08:00 KST


def kst(hour: int) -> datetime:
    """KST 기준 시각을 UTC datetime 으로 (KST = UTC+9)."""
    return datetime(2026, 8, 30, (hour - 9) % 24, 0, tzinfo=UTC)


def test_levels():
    assert level_for(5) is Level.PUSH
    assert level_for(4) is Level.PUSH
    assert level_for(3) is Level.SILENT
    assert level_for(2) is Level.FEED


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
