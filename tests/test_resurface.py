# 재알림 잡 테스트 — FCM 꺼짐·미연결·무음 시간 건너뜀, 한 번만 보내고 기록, 실패 시 멈춤

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import AppConfig, ChannelsConfig, NotifyConfig
from app.jobs import resurface

NEVER_QUIET = {"quiet_start_hour": 0, "quiet_end_hour": 0}
ALWAYS_QUIET = {"quiet_start_hour": 0, "quiet_end_hour": 24}


class FakeFcm:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[tuple[int, str]] = []

    async def send_resurface(self, item: Any, title: str) -> str:
        if self.fail:
            raise RuntimeError("fcm 등록된 기기 없음")
        self.sent.append((item.id, title))
        return "msg-1"


class Bookmarks:
    """_claim 자리. 조건 SQL 은 통합 테스트가 보고, 여기는 아직 안 보낸 찜을 차례로 준다."""

    def __init__(self, count: int) -> None:
        self.rows = [
            SimpleNamespace(
                item_id=i, resurfaced_at=None, item=SimpleNamespace(id=i, title=f"찜 {i}")
            )
            for i in range(1, count + 1)
        ]
        self.claims = 0
        self.cutoffs: list[datetime] = []

    async def claim(self, _session: Any, _user_id: int, saved_before: datetime) -> Any:
        self.claims += 1
        self.cutoffs.append(saved_before)
        for row in self.rows:
            if row.resurfaced_at is None:
                return row, row.item
        return None


@asynccontextmanager
async def _scope() -> AsyncIterator[None]:
    yield None


async def _title(_session: Any, _user_id: int, item: Any) -> str:
    return str(item.title)


@pytest.fixture
def setup(monkeypatch: pytest.MonkeyPatch):
    def _setup(
        count: int = 1, *, fcm_on: bool = True, connected: bool = True, **notify: Any
    ) -> Bookmarks:
        cfg = NotifyConfig(channels=ChannelsConfig(fcm=fcm_on), **(notify or NEVER_QUIET))
        table = Bookmarks(count)
        monkeypatch.setattr(resurface, "get_rules", lambda: SimpleNamespace(notify=cfg))
        monkeypatch.setattr(resurface, "get_settings", lambda: None)
        monkeypatch.setattr(resurface, "channel_connected", lambda _s: {"fcm": connected})
        monkeypatch.setattr(resurface, "get_app_config", lambda: AppConfig())
        monkeypatch.setattr(resurface, "session_scope", _scope)
        monkeypatch.setattr(resurface, "_claim", table.claim)
        monkeypatch.setattr(resurface, "_title", _title)
        return table

    return _setup


async def test_sends_each_once_and_records(setup):
    table = setup(2)
    fcm = FakeFcm()

    assert await resurface.run_resurface(fcm) == 2
    assert fcm.sent == [(1, "찜 1"), (2, "찜 2")]
    assert all(row.resurfaced_at is not None for row in table.rows)

    # 다음 회차에는 다시 가지 않는다.
    assert await resurface.run_resurface(fcm) == 0
    assert len(fcm.sent) == 2


async def test_cutoff_is_seven_days_ago(setup):
    table = setup(0)
    before = datetime.now(UTC)
    await resurface.run_resurface(FakeFcm())
    after = datetime.now(UTC)
    assert before - timedelta(days=7) <= table.cutoffs[0] <= after - timedelta(days=7)


@pytest.mark.parametrize(
    "kw",
    [{"fcm_on": False}, {"connected": False}, ALWAYS_QUIET],
    ids=["fcm_off", "not_connected", "quiet_hours"],
)
async def test_gates_skip_everything(setup, kw: dict[str, Any]):
    table = setup(1, **kw)
    fcm = FakeFcm()

    assert await resurface.run_resurface(fcm) == 0
    assert fcm.sent == []
    assert table.claims == 0  # DB 도 읽지 않는다
    assert table.rows[0].resurfaced_at is None


async def test_failure_stops_run_without_recording(setup):
    table = setup(3)
    fcm = FakeFcm(fail=True)

    assert await resurface.run_resurface(fcm) == 0
    assert table.claims == 1  # 첫 실패에서 멈춘다
    assert all(row.resurfaced_at is None for row in table.rows)

    # 기기가 붙으면 다음 회차에 보낸다.
    fcm.fail = False
    assert await resurface.run_resurface(fcm) == 3
