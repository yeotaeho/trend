# FCM 기기 등록 모델 — POST /devices 요청·응답

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.api.v1.schemas.common import StrictIn, UtcDateTime

TOKEN_MAX = 4096  # FCM 등록 토큰은 200자 안팎이다. 한도는 넉넉히 둔다


class Platform(StrEnum):
    ANDROID = "android"
    IOS = "ios"


class DeviceIn(StrictIn):
    token: str = Field(min_length=1, max_length=TOKEN_MAX)
    platform: Platform
    app_version: str | None = Field(default=None, max_length=30)


class DeviceOut(BaseModel):
    id: str
    platform: Platform
    registered_at: UtcDateTime
