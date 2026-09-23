# 앱 API 오류 — ApiError 와 /api/v1 경로의 오류 봉투 {"error": {code, message, details}} 핸들러

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.log import get_logger

API_PREFIX = "/api/v1"
log = get_logger(__name__)

# 라우팅이 내는 HTTPException(없는 경로·메서드)의 code. 나머지 상태는 bad_request.
_HTTP_CODES = {401: "unauthorized", 404: "not_found"}
_HTTP_MESSAGES = {401: "인증이 필요합니다.", 404: "요청한 경로가 없습니다."}


class ApiError(Exception):
    """라우터·의존성이 던지면 핸들러가 계약의 오류 봉투로 바꾼다."""

    def __init__(
        self, status: int, code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def error_response(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details or {}}}
    return JSONResponse(status_code=status, content=body)


def _is_api(request: Request) -> bool:
    # 웹훅·헬스체크는 FastAPI 기본 형식을 그대로 둔다.
    return request.url.path.startswith(API_PREFIX)


async def _api_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, ApiError)
    return error_response(exc.status, exc.code, exc.message, exc.details)


async def _http_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, StarletteHTTPException)
    if not _is_api(request):
        return await http_exception_handler(request, exc)
    code = _HTTP_CODES.get(exc.status_code, "bad_request")
    message = _HTTP_MESSAGES.get(exc.status_code, "잘못된 요청입니다.")
    return error_response(exc.status_code, code, message)


async def _validation_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RequestValidationError)
    if not _is_api(request):
        return await request_validation_exception_handler(request, exc)
    # 입력값·ctx 는 되돌려 주지 않는다. 위치·메시지·종류면 클라이언트가 분기할 수 있다.
    errors = [
        {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
        for e in exc.errors()
    ]
    return error_response(
        422, "validation_error", "요청 값이 올바르지 않습니다.", {"errors": errors}
    )


async def _db_unavailable(request: Request, exc: Exception) -> Response:
    if not _is_api(request):
        raise exc
    log.warning("api.db_unavailable", path=request.url.path, error=str(exc))
    return error_response(
        503, "unavailable", "DB 에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    # asyncpg 연결 실패는 OSError(ConnectionRefusedError·TimeoutError)로 그대로 올라온다.
    for exc_type in (OperationalError, InterfaceError, OSError):
        app.add_exception_handler(exc_type, _db_unavailable)
