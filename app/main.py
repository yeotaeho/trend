# FastAPI 엔트리 — 웹훅·헬스체크·앱 API(/api/v1) 라우터를 붙이고 같은 프로세스에서 스케줄러를 띄운다

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import discord, github, health, telegram, v1
from app.api.v1.errors import install_error_handlers
from app.api.v1.meta import warn_missing_taxonomy_labels
from app.config import get_settings
from app.db.prefs import load_prefs_overlay
from app.db.session import engine
from app.jobs.scheduler import start_scheduler
from app.log import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    warn_missing_taxonomy_labels()
    await load_prefs_overlay()
    scheduler = await start_scheduler() if get_settings().scheduler_enabled else None
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        await engine.dispose()


app = FastAPI(title="기술 파악", lifespan=lifespan)
app.include_router(health.router)
app.include_router(github.router)
app.include_router(telegram.router)
app.include_router(discord.router)
app.include_router(v1.router)
install_error_handlers(app)
