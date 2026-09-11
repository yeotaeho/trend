# 스케줄러 등록 테스트 — 모든 잡이 기동 직후 1회 돌고, 밀린 회차는 늦어도 한 번은 돈다

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.jobs import scheduler as sched


@pytest.fixture
def offline_scheduler(monkeypatch):
    """DB 없이 소스 하나를 돌려주고, start() 는 막는다. 진짜 시작하면 잡이 즉시 돈다."""

    async def _sources():
        return [SimpleNamespace(id=1, name="rss:test", poll_interval_sec=3600)]

    monkeypatch.setattr(sched, "sync_sources", _sources)
    monkeypatch.setattr(AsyncIOScheduler, "start", lambda self: None)


async def test_every_job_fires_once_at_boot(offline_scheduler):
    """interval 트리거 기본은 첫 실행이 등록 + 한 주기다. arXiv 는 한 시간을 기다렸다."""
    before = datetime.now(UTC)
    scheduler = await sched.start_scheduler()
    jobs = {job.id: job for job in scheduler.get_jobs()}

    assert set(jobs) == {"source:rss:test", "pipeline", "notify", "feedback"}
    for job in jobs.values():
        assert job.next_run_time is not None, job.id
        assert before <= job.next_run_time <= datetime.now(UTC), job.id


async def test_missed_runs_collapse_into_one_late_run(offline_scheduler):
    """절전에서 깨어나면 잡마다 한 번씩만 돈다. 기본 grace 1초면 그 회차를 통째로 버린다."""
    scheduler = await sched.start_scheduler()
    for job in scheduler.get_jobs():
        assert job.coalesce is True, job.id
        assert job.misfire_grace_time is None, job.id
