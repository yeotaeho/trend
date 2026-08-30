# 수동 실행 스크립트 — 스케줄러 없이 수집·파이프라인·발송 잡을 한 번씩 돌린다

from __future__ import annotations

import argparse
import asyncio

from app.db.session import engine
from app.jobs.collect import run_all_sources
from app.jobs.notify import run_notify
from app.jobs.pipeline import run_pipeline
from app.jobs.scheduler import sync_sources
from app.log import configure_logging

JOBS = {
    "sync": lambda: sync_sources(),
    "collect": run_all_sources,
    "pipeline": run_pipeline,
    "notify": run_notify,
}


async def main(names: list[str]) -> None:
    configure_logging()
    try:
        for name in names:
            result = await JOBS[name]()
            print(f"{name}: {len(result) if isinstance(result, list) else result}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="기술 파악 잡 수동 실행")
    parser.add_argument("jobs", nargs="+", choices=list(JOBS), help="실행할 잡 (순서대로)")
    asyncio.run(main(parser.parse_args().jobs))
