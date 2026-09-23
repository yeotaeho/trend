# 스케줄러 테스트 — 잡 즉시·밀린 회차 1회, 앱 on/off 재기동 보존, 비활성 소스도 잡 등록

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import SourceConfig
from app.db.models import Source
from app.jobs import collect
from app.jobs import scheduler as sched


@pytest.fixture
def one_source(monkeypatch):
    """DB 없이 소스 하나를 돌려준다."""

    async def _sources():
        return [SimpleNamespace(id=1, name="rss:test", poll_interval_sec=3600)]

    monkeypatch.setattr(sched, "sync_sources", _sources)


async def test_every_job_fires_once_right_after_start(one_source, monkeypatch):
    """interval 트리거 기본은 첫 실행이 등록 + 한 주기다. arXiv 는 한 시간을 기다렸다.

    start() 를 막지 않고 진짜 스케줄러를 띄워 잡 함수가 실제로 불리는지 본다.
    """
    expected = {"run_source", "run_pipeline", "run_notify", "run_feedback"}
    calls: list[str] = []
    all_called = asyncio.Event()

    def recorder(name: str):
        async def _job(*_args):
            calls.append(name)
            if set(calls) == expected:
                all_called.set()

        return _job

    for job in expected:
        monkeypatch.setattr(sched, job, recorder(job))

    scheduler = await sched.start_scheduler()
    try:
        # 고정 sleep 은 느린 CI 에서 흔들린다. 네 잡이 다 불릴 때까지만 기다린다.
        await asyncio.wait_for(all_called.wait(), timeout=5)
    finally:
        scheduler.shutdown(wait=False)

    assert sorted(calls) == sorted(expected)


async def test_missed_runs_collapse_into_one_late_run(one_source, monkeypatch):
    """절전에서 깨어나면 잡마다 한 번씩만 돈다. 기본 grace 1초면 그 회차를 통째로 버린다."""
    monkeypatch.setattr(AsyncIOScheduler, "start", lambda self: None)
    scheduler = await sched.start_scheduler()
    jobs = {job.id: job for job in scheduler.get_jobs()}

    assert set(jobs) == {"source:rss:test", "pipeline", "notify", "feedback"}
    for job in jobs.values():
        assert job.coalesce is True, job.id
        assert job.misfire_grace_time is None, job.id


class SourceTable:
    """sources 테이블 자리. sync_sources 가 쓰는 execute(select(Source))·add·flush 만 흉내 낸다."""

    def __init__(self) -> None:
        self.rows: dict[str, Source] = {}

    async def execute(self, _stmt: Any) -> Any:
        rows = list(self.rows.values())
        return SimpleNamespace(scalars=lambda: iter(rows))

    def add(self, source: Source) -> None:
        self.rows[source.name] = source

    async def flush(self) -> None:
        return None

    @asynccontextmanager
    async def scope(self):
        yield self


@pytest.fixture
def table(monkeypatch) -> SourceTable:
    table = SourceTable()
    monkeypatch.setattr(sched, "session_scope", table.scope)
    monkeypatch.setattr(
        sched,
        "get_source_configs",
        lambda: [
            SourceConfig(name="rss:a", type="rss"),
            SourceConfig(name="rss:b", type="rss"),
            SourceConfig(name="rss:yaml-off", type="rss", enabled=False),
        ],
    )
    return table


def _prefs(monkeypatch, data: dict[str, Any] | None) -> None:
    async def fetch(_session, _user_id):
        return None if data is None else SimpleNamespace(data=data)

    monkeypatch.setattr(sched, "fetch_prefs", fetch)


async def test_app_disabled_source_stays_off_across_restart(table, monkeypatch):
    _prefs(monkeypatch, None)
    table.add(Source(name="rss:gone", type="rss", enabled=True))
    first = await sched.sync_sources()
    assert [s.name for s in first] == ["rss:a", "rss:b", "rss:yaml-off"]
    assert table.rows["rss:gone"].enabled is False

    # PATCH /sources/rss:b {"enabled": false} 가 남기는 두 값. 재기동하면 sync_sources 가 다시 돈다.
    table.rows["rss:b"].enabled = False
    _prefs(monkeypatch, {"sources": {"rss:b": {"enabled": False}}})
    await sched.sync_sources()

    assert table.rows["rss:b"].enabled is False
    assert table.rows["rss:a"].enabled is True


async def test_app_override_can_enable_a_yaml_disabled_source(table, monkeypatch):
    _prefs(monkeypatch, {"sources": {"rss:yaml-off": {"enabled": True}, "rss:a": "틀린 모양"}})

    synced = {s.name: s.enabled for s in await sched.sync_sources()}

    assert synced == {"rss:a": True, "rss:b": True, "rss:yaml-off": True}


async def test_disabled_sources_still_get_a_job(monkeypatch):
    async def _sources():
        return [
            SimpleNamespace(id=1, name="rss:on", poll_interval_sec=900, enabled=True),
            SimpleNamespace(id=2, name="rss:off", poll_interval_sec=900, enabled=False),
        ]

    monkeypatch.setattr(sched, "sync_sources", _sources)
    monkeypatch.setattr(AsyncIOScheduler, "start", lambda self: None)
    scheduler = await sched.start_scheduler()

    assert {"source:rss:on", "source:rss:off"} <= {job.id for job in scheduler.get_jobs()}


async def test_run_source_skips_disabled_source(monkeypatch):
    class _Session:
        async def get(self, _model, _id):
            return Source(id=7, name="rss:off", type="rss", config={}, enabled=False)

    @asynccontextmanager
    async def scope():
        yield _Session()

    def must_not_build(_cfg):
        raise AssertionError("비활성 소스를 폴링했다")

    monkeypatch.setattr(collect, "session_scope", scope)
    monkeypatch.setattr(collect, "build_source", must_not_build)

    assert await collect.run_source(7) == 0
