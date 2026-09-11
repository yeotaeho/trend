# 스케줄러 등록 테스트 — 모든 잡이 기동 직후 1회 돌고, 밀린 회차는 늦어도 한 번은 돈다

import asyncio
from types import SimpleNamespace

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
