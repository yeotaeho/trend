# 텔레그램 API 호출·웹훅 테스트 — 예외 메시지에 봇 토큰이 새지 않고, 콜백은 사용자 1 로 기록한다

from types import SimpleNamespace

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api import telegram as tg
from app.config import get_settings
from app.main import app
from app.notify.telegram import _call
from tests.fakes import UpsertRecorder, fake_session_scope

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


def test_callback_upserts_feedback_for_default_user(monkeypatch):
    recorder = UpsertRecorder()
    monkeypatch.setattr(tg, "get_settings", lambda: SimpleNamespace(telegram_webhook_secret="s"))
    monkeypatch.setattr(tg, "upsert_feedback", recorder)
    monkeypatch.setattr(tg, "session_scope", fake_session_scope)

    async def no_answer(*_: object) -> None:
        return None

    monkeypatch.setattr(tg, "answer_callback", no_answer)

    res = TestClient(app).post(
        "/webhook/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "s"},
        json={"callback_query": {"id": "q1", "data": "fb:useless:7"}},
    )

    assert res.status_code == 200
    assert recorder.calls == [(1, 7, "useless", {"source": "telegram"})]


def test_webhook_keeps_default_error_format(monkeypatch):
    # 앱 API 오류 봉투는 /api/v1 에만. 웹훅은 FastAPI 기본 {"detail": ...} 그대로다.
    monkeypatch.setattr(tg, "get_settings", lambda: SimpleNamespace(telegram_webhook_secret="s"))
    res = TestClient(app).post("/webhook/telegram", json={})
    assert res.status_code == 401
    assert res.json() == {"detail": "secret token mismatch"}
