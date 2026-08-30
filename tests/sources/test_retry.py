# HTTP 재시도 판정 테스트 — 네트워크 오류·429·5xx 만 재시도한다

import httpx

from app.sources.base import retryable


def status_error(code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com")
    return httpx.HTTPStatusError(
        "", request=request, response=httpx.Response(code, request=request)
    )


def test_transport_error_is_retried():
    assert retryable(httpx.ConnectError("boom"))


def test_server_error_and_rate_limit_are_retried():
    assert retryable(status_error(500))
    assert retryable(status_error(503))
    assert retryable(status_error(429))


def test_permanent_client_errors_are_not_retried():
    assert not retryable(status_error(401))
    assert not retryable(status_error(404))


def test_unrelated_exception_is_not_retried():
    assert not retryable(ValueError("nope"))
