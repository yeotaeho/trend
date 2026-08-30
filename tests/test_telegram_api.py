# 텔레그램 API 호출 테스트 — 예외 메시지에 봇 토큰이 새지 않아야 한다

import httpx
import pytest
import respx

from app.config import get_settings
from app.notify.telegram import _call

TOKEN = get_settings().telegram_bot_token
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


@respx.mock
async def test_http_error_does_not_leak_token():
    respx.post(URL).mock(return_value=httpx.Response(403))

    with pytest.raises(RuntimeError) as exc:
        await _call("sendMessage", {})

    assert TOKEN not in str(exc.value)
    assert "403" in str(exc.value)


@respx.mock
async def test_transport_error_does_not_leak_token():
    respx.post(URL).mock(side_effect=httpx.ConnectError)

    with pytest.raises(RuntimeError) as exc:
        await _call("sendMessage", {})

    assert TOKEN not in str(exc.value)


@respx.mock
async def test_api_level_error_is_reported():
    respx.post(URL).mock(
        return_value=httpx.Response(200, json={"ok": False, "description": "chat not found"})
    )

    with pytest.raises(RuntimeError, match="chat not found"):
        await _call("sendMessage", {})
