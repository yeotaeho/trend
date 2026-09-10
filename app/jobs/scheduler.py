# 스케줄러 — config/sources.yaml 을 DB 에 동기화하고 소스별·파이프라인·발송 잡을 등록

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_source_configs
from app.db.models import Source
from app.db.session import session_scope
from app.jobs.collect import run_source
from app.jobs.feedback import run_feedback
from app.jobs.notify import run_notify
from app.jobs.pipeline import run_pipeline
from app.log import get_logger

PIPELINE_INTERVAL_SEC = 120
NOTIFY_INTERVAL_SEC = 180
FEEDBACK_INTERVAL_SEC = 600  # 디스코드 GET 1회. 리액션은 몇 분 늦게 반영돼도 된다
log = get_logger(__name__)


async def sync_sources() -> list[Source]:
    """YAML 이 진실. 이름이 같으면 갱신하고, YAML 에서 빠진 소스는 비활성화한다."""
    configs = {cfg.name: cfg for cfg in get_source_configs()}
    async with session_scope() as session:
        existing = {s.name: s for s in (await session.execute(select(Source))).scalars()}

        for name, cfg in configs.items():
            source = existing.get(name)
            if source is None:
                source = Source(name=name)
                session.add(source)
            source.type = cfg.type
            source.config = cfg.config
            source.poll_interval_sec = cfg.poll_interval_sec
            source.trust_score = cfg.trust_score
            source.enabled = cfg.enabled

        for name, source in existing.items():
            if name not in configs:
                source.enabled = False

        await session.flush()
        return [s for s in (await session.execute(select(Source))).scalars() if s.enabled]


async def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    for source in await sync_sources():
        scheduler.add_job(
            run_source,
            "interval",
            seconds=source.poll_interval_sec,
            args=[source.id],
            id=f"source:{source.name}",
            max_instances=1,
            coalesce=True,
        )
    scheduler.add_job(
        run_pipeline, "interval", seconds=PIPELINE_INTERVAL_SEC, id="pipeline", max_instances=1
    )
    scheduler.add_job(
        run_notify, "interval", seconds=NOTIFY_INTERVAL_SEC, id="notify", max_instances=1
    )
    scheduler.add_job(
        run_feedback, "interval", seconds=FEEDBACK_INTERVAL_SEC, id="feedback", max_instances=1
    )
    scheduler.start()
    log.info("scheduler.started", jobs=[job.id for job in scheduler.get_jobs()])
    return scheduler
