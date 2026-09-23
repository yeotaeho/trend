# 커서 페이지네이션 — limit·cursor 쿼리, 불투명 커서(base64url JSON) 인코딩, 다음 커서 계산

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query

from app.api.v1.errors import ApiError

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def encode_cursor(key: dict[str, Any]) -> str:
    raw = json.dumps(key, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    """클라이언트가 건드린 커서는 400 bad_request 다."""
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        key = json.loads(raw)
    except (binascii.Error, ValueError) as exc:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.") from exc
    if not isinstance(key, dict):
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.")
    return key


@dataclass(frozen=True, slots=True)
class PageParams:
    limit: int
    # 직전 페이지 마지막 행의 정렬 키. 첫 페이지면 None.
    after: dict[str, Any] | None


def page_params(
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query()] = None,
) -> PageParams:
    return PageParams(limit=limit, after=decode_cursor(cursor) if cursor else None)


Paging = Annotated[PageParams, Depends(page_params)]


def paginate[T](
    rows: Sequence[T], limit: int, key: Callable[[T], dict[str, Any]]
) -> tuple[list[T], str | None]:
    """limit + 1 건을 읽어 넘긴다. 남는 행이 있으면 이 페이지 마지막 행의 키가 다음 커서다."""
    page = list(rows[:limit])
    if len(rows) <= limit:
        return page, None
    return page, encode_cursor(key(page[-1]))
