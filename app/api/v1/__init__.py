# 앱 API v1 — 모든 하위 라우터를 /api/v1 아래에 베어러 인증으로 묶는다

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.v1 import (
    alerts,
    devices,
    feed,
    filtered,
    meta,
    profile,
    reports,
    saved,
    settings,
    sources,
)
from app.api.v1.deps import require_token
from app.api.v1.errors import API_PREFIX
from app.api.v1.schemas.common import ErrorEnvelope

_ERRORS: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorEnvelope} for status in (401, 422, 503)
}

router = APIRouter(prefix=API_PREFIX, dependencies=[Depends(require_token)], responses=_ERRORS)
for _module in (meta, feed, alerts, settings, sources, filtered, saved, profile, reports, devices):
    router.include_router(_module.router)
