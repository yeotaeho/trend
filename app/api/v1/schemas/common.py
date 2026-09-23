# 앱 API 공통 모델 — UTC 시각 직렬화, 목록 봉투, 오류 봉투, 입력 한도

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, PlainSerializer

# 계약 1.2 — ISO-8601 UTC, 초 단위, Z 접미.
UtcDateTime = Annotated[
    datetime,
    PlainSerializer(lambda v: v.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), return_type=str),
]

# 입력 한도. GET /meta 로 앱에 알려 주고, 쓰기 API 가 같은 값으로 검증한다.
KIND_WEIGHT_MIN = -0.5
KIND_WEIGHT_MAX = 0.5
KIND_WEIGHT_STEP = 0.05
DAILY_PUSH_CAP_MIN = 1
DAILY_PUSH_CAP_MAX = 50
WATCH_KEYWORDS_MAX = 50
FOLDER_NAME_MAX = 30
MEMO_MAX = 500


class Page[T](BaseModel):
    """목록 응답 봉투. next_cursor 가 null 이면 끝이다."""

    items: list[T]
    next_cursor: str | None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any]


class ErrorEnvelope(BaseModel):
    error: ErrorBody
