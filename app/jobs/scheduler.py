# 스케줄러 — sources.yaml + 앱 on/off 를 DB 에 동기화하고 소스별·파이프라인·발송·재알림 잡을 등록

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_source_configs
from app.db.models import Source
from app.db.prefs import fetch_prefs, source_overrides
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.jobs.collect import run_source
from app.jobs.feedback import run_feedback
from app.jobs.notify import run_notify
from app.jobs.pipeline import run_pipeline
from app.jobs.resurface import run_resurface
from app.log import get_logger

PIPELINE_INTERVAL_SEC = 120
NOTIFY_INTERVAL_SEC = 180
FEEDBACK_INTERVAL_SEC = 600  # 디스코드 GET 1회. 리액션은 몇 분 늦게 반영돼도 된다
RESURFACE_INTERVAL_SEC = 3600  # 7일 지난 찜을 다시 알린다. 한 시간 늦어도 된다
log = get_logger(__name__)


async def sync_sources() -> list[Source]:
    """YAML 이 진실이고 앱이 바꾼 on/off(user_prefs.data.sources)만 그 위에 얹는다.

    이름이 같으면 갱신하고, YAML 에서 빠진 소스는 비활성화한다. 돌려주는 목록은 YAML 순서의
    모든 소스다 (비활성 포함). 잡은 전부 등록하고 run_source 가 비활성 소스를 건너뛰므로
    앱에서 켜고 끌 때 잡을 다시 등록하지 않는다.
    """
    configs = get_source_configs()
    async with session_scope() as session:
        prefs = await fetch_prefs(session, DEFAULT_USER_ID)
        overrides = source_overrides(prefs.data if prefs else {})
        existing = {s.name: s for s in (await session.execute(select(Source))).scalars()}

        synced: list[Source] = []
        for cfg in configs:
            source = existing.pop(cfg.name, None)
            if source is None:
                source = Source(name=cfg.name)
                session.add(source)
            source.type = cfg.type
            source.config = cfg.config
            source.poll_interval_sec = cfg.poll_interval_sec
            source.trust_score = cfg.trust_score
            source.enabled = overrides.get(cfg.name, cfg.enabled)
            synced.append(source)

        for source in existing.values():
            source.enabled = False

        await session.flush()
        return synced


def _interval(seconds: int) -> dict[str, Any]:
    """모든 잡 공통 옵션.

    - next_run_time=now: interval 트리거 기본은 첫 실행이 등록 + 한 주기라, 기동 뒤 arXiv 는
      한 시간을 기다렸다. 기동 직후 한 번 돌고 그 뒤 주기대로 간다.
    - coalesce + grace 무제한: 절전에서 깨어나거나 루프가 밀려도 그 잡은 늦게라도 한 번은 돈다.
      기본 grace 1초는 밀린 회차를 통째로 버렸다. 밀린 회차가 여럿이면 한 번으로 합친다.
      단 절전 직전에 시작한 실행이 아직 안 끝났으면 max_instances=1 에 걸려 그 회차는 건너뛰고
      다음 주기에 돈다. 동시 실행을 허용하는 것보다 한 주기 늦는 쪽이 낫다.
    """
    return {
        "trigger": "interval",
        "seconds": seconds,
        "next_run_time": datetime.now(UTC),
        "coalesce": True,
        "misfire_grace_time": None,
        "max_instances": 1,
    }


async def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    for source in await sync_sources():
        scheduler.add_job(
            run_source,
            args=[source.id],
            id=f"source:{source.name}",
            **_interval(source.poll_interval_sec),
        )
    scheduler.add_job(run_pipeline, id="pipeline", **_interval(PIPELINE_INTERVAL_SEC))
    scheduler.add_job(run_notify, id="notify", **_interval(NOTIFY_INTERVAL_SEC))
    scheduler.add_job(run_feedback, id="feedback", **_interval(FEEDBACK_INTERVAL_SEC))
    scheduler.add_job(run_resurface, id="resurface", **_interval(RESURFACE_INTERVAL_SEC))
    scheduler.start()
    log.info("scheduler.started", jobs=[job.id for job in scheduler.get_jobs()])
    return scheduler
