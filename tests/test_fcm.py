# FCM 발송 테스트 — 계약 4.9 페이로드, OAuth 재사용, 무효 토큰 비활성화, 채널 등록 (네트워크 없이)

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import jwt

from app.db.models import Item, Summary
from app.jobs import notify as job
from app.notify import fcm
from app.notify.base import channel_connected
from app.notify.fcm import FcmNotifier
from app.schemas import Level
from tests.test_notify_fanout import FakeSession, make_triple, rules_with, settings

PROJECT = "trend-test"
SEND = f"https://fcm.googleapis.com/v1/projects/{PROJECT}/messages:send"
TOKEN_URI = "https://oauth2.googleapis.com/token"
TITLE = "[릴리즈] MCP Python SDK v2.2.0"


def unregistered(status: int = 404, code: str = "UNREGISTERED") -> httpx.Response:
    return httpx.Response(
        status,
        json={
            "error": {
                "code": status,
                "status": "NOT_FOUND" if status == 404 else "INVALID_ARGUMENT",
                "details": [{"@type": fcm.FCM_ERROR_TYPE, "errorCode": code}],
            }
        },
    )


class Devices:
    """devices 테이블 대신. active_devices·disable_device 자리에 끼운다."""

    def __init__(self, *tokens: str) -> None:
        self.rows = {i: {"token": t, "disabled": None} for i, t in enumerate(tokens, start=1)}

    async def active(self, _user_id: int) -> list[tuple[int, str]]:
        return [(i, r["token"]) for i, r in self.rows.items() if r["disabled"] is None]

    async def disable(self, device_id: int, error: str) -> None:
        self.rows[device_id]["disabled"] = error


@pytest.fixture
def account(tmp_path: Path) -> Path:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    path = tmp_path / "sa.json"
    path.write_text(
        json.dumps(
            {
                "type": "service_account",
                "project_id": PROJECT,
                "private_key_id": "kid-1",
                "private_key": pem,
                "client_email": f"push@{PROJECT}.iam.gserviceaccount.com",
                "token_uri": TOKEN_URI,
            }
        )
    )
    return path


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, account: Path) -> SimpleNamespace:
    configured = settings(fcm_project_id=PROJECT, fcm_service_account_file=str(account))
    monkeypatch.setattr(fcm, "get_settings", lambda: configured)
    monkeypatch.setattr(fcm, "_cached_token", None)
    return configured


@pytest.fixture
def devices(monkeypatch: pytest.MonkeyPatch) -> Devices:
    store = Devices("tok-a", "tok-b")
    monkeypatch.setattr(fcm, "active_devices", store.active)
    monkeypatch.setattr(fcm, "disable_device", store.disable)
    return store


@pytest.fixture
def oauth(respx_mock: respx.MockRouter) -> respx.Route:
    return respx_mock.post(TOKEN_URI).mock(
        return_value=httpx.Response(200, json={"access_token": "ya29.x", "expires_in": 3599})
    )


def sent_bodies(route: respx.Route) -> list[dict[str, Any]]:
    return [json.loads(call.request.content) for call in route.calls]


def ok(name: str = "0:1") -> httpx.Response:
    return httpx.Response(200, json={"name": f"projects/{PROJECT}/messages/{name}"})


def triple() -> tuple[Item, Summary]:
    item, summary, _ = make_triple(18342)
    summary.summary_ko = "스트리밍 HTTP 클라이언트의 …"
    return item, summary


async def test_instant_payload_matches_contract(env, devices, oauth, respx_mock):
    route = respx_mock.post(SEND).mock(return_value=ok())
    item, summary = triple()

    message_id = await FcmNotifier().send(item, summary, Level.PUSH, "rss:mcp", title=TITLE)

    assert message_id == "0:1"
    first = sent_bodies(route)[0]
    assert first == {
        "message": {
            "token": "tok-a",
            "notification": {"title": TITLE, "body": "스트리밍 HTTP 클라이언트의 …"},
            "data": {"alert_id": "18342", "delivery_mode": "instant", "type": "alert"},
            "android": {"priority": "HIGH", "notification": {"channel_id": "instant"}},
            "apns": {"headers": {"apns-priority": "10"}, "payload": {"aps": {"sound": "default"}}},
        }
    }
    assert [b["message"]["token"] for b in sent_bodies(route)] == ["tok-a", "tok-b"]
    assert route.calls.last.request.headers["Authorization"] == "Bearer ya29.x"


@pytest.mark.parametrize(
    ("level", "mode", "title"),
    [(Level.SILENT, "quiet", TITLE), (Level.EXPLORE, "experiment", f"🧪 {TITLE}")],
)
async def test_quiet_and_experiment_payload(env, devices, oauth, respx_mock, level, mode, title):
    route = respx_mock.post(SEND).mock(return_value=ok())
    item, summary = triple()

    await FcmNotifier().send(item, summary, level, "rss:mcp", title=TITLE)

    message = sent_bodies(route)[0]["message"]
    assert message["notification"]["title"] == title
    assert message["data"] == {"alert_id": "18342", "delivery_mode": mode, "type": "alert"}
    assert message["android"] == {"priority": "NORMAL", "notification": {"channel_id": "quiet"}}
    assert message["apns"] == {"headers": {"apns-priority": "5"}, "payload": {"aps": {}}}


async def test_resurface_is_quiet_with_pin(env, devices, oauth, respx_mock):
    route = respx_mock.post(SEND).mock(return_value=ok())
    item, _ = triple()

    await FcmNotifier().send_resurface(item, TITLE)

    message = sent_bodies(route)[0]["message"]
    assert message["notification"]["title"] == f"📌 {TITLE}"
    assert message["data"] == {"alert_id": "18342", "delivery_mode": "quiet", "type": "resurface"}
    assert message["android"]["notification"] == {"channel_id": "quiet"}
    assert message["apns"]["headers"] == {"apns-priority": "5"}


async def test_oauth_assertion_and_token_reuse(env, devices, oauth, respx_mock, account):
    respx_mock.post(SEND).mock(return_value=ok())
    item, summary = triple()

    for _ in range(2):
        await FcmNotifier().send(item, summary, Level.PUSH, "rss:mcp", title=TITLE)

    # 기기 2대 × 2회 발송에도 토큰은 한 번만 받는다.
    assert oauth.call_count == 1
    form = dict(httpx.QueryParams(oauth.calls.last.request.content.decode()))
    assert form["grant_type"] == fcm.GRANT_TYPE
    claims = jwt.decode(form["assertion"], verify=False)
    info = json.loads(account.read_text())
    assert claims["iss"] == info["client_email"]
    assert claims["aud"] == TOKEN_URI
    assert claims["scope"] == fcm.SCOPE


async def test_expiring_token_is_refreshed(env, devices, oauth, respx_mock, monkeypatch):
    respx_mock.post(SEND).mock(return_value=ok())
    monkeypatch.setattr(fcm, "_cached_token", ("old", fcm.time.monotonic() + 60))
    item, summary = triple()

    await FcmNotifier().send(item, summary, Level.PUSH, "rss:mcp", title=TITLE)

    assert oauth.call_count == 1  # 만료 5분 전 안쪽이라 새로 받았다


@pytest.mark.parametrize(
    "rejection", [unregistered(), unregistered(400, "INVALID_ARGUMENT")], ids=["404", "400"]
)
async def test_rejected_token_is_disabled_and_skipped_next_time(
    env, devices, oauth, respx_mock, rejection
):
    route = respx_mock.post(SEND).mock(side_effect=[rejection, ok("m-b"), ok("m-b2")])
    item, summary = triple()

    assert await FcmNotifier().send(item, summary, Level.PUSH, "s", title=TITLE) == "m-b"
    assert devices.rows[1]["disabled"] is not None
    assert devices.rows[2]["disabled"] is None

    await FcmNotifier().send(item, summary, Level.PUSH, "s", title=TITLE)
    assert [b["message"]["token"] for b in sent_bodies(route)] == ["tok-a", "tok-b", "tok-b"]


async def test_other_errors_do_not_disable(env, devices, oauth, respx_mock):
    respx_mock.post(SEND).mock(side_effect=[httpx.Response(403, json={}), ok()])
    item, summary = triple()

    await FcmNotifier().send(item, summary, Level.PUSH, "s", title=TITLE)

    assert all(r["disabled"] is None for r in devices.rows.values())


async def test_no_devices_raises(env, monkeypatch, oauth):
    monkeypatch.setattr(fcm, "active_devices", Devices().active)
    item, summary = triple()

    with pytest.raises(RuntimeError, match="기기 없음"):
        await FcmNotifier().send(item, summary, Level.PUSH, "s", title=TITLE)


async def test_all_devices_failing_raises_into_channel_row(env, devices, oauth, respx_mock):
    respx_mock.post(SEND).mock(return_value=unregistered())
    item, summary, _ = make_triple()
    session = FakeSession()

    delivered = await job.deliver(
        session,  # type: ignore[arg-type]
        [FcmNotifier()],
        item,
        summary,
        Level.PUSH,
        "s",
        title=TITLE,
    )

    assert delivered is False
    [row] = session.rows
    assert row.channel == "fcm"
    assert row.error is not None and "전부 실패" in row.error
    assert all(r["disabled"] for r in devices.rows.values())


def test_body_is_truncated_under_fcm_limit():
    message = fcm.build_message("t", title="가" * 1000, body="나" * 5000, data={}, loud=True)
    assert len(json.dumps(message, ensure_ascii=False).encode()) < 4096


def test_fcm_connected_needs_project_and_existing_file(account: Path, tmp_path: Path):
    assert channel_connected(
        settings(fcm_project_id=PROJECT, fcm_service_account_file=str(account))  # type: ignore[arg-type]
    )["fcm"]
    missing = settings(fcm_project_id=PROJECT, fcm_service_account_file=str(tmp_path / "x.json"))
    assert not channel_connected(missing)["fcm"]  # type: ignore[arg-type]
    assert not channel_connected(settings(fcm_service_account_file=str(account)))["fcm"]  # type: ignore[arg-type]


def test_enabled_notifiers_registers_fcm_first(monkeypatch, account: Path):
    connected = settings(
        fcm_project_id=PROJECT,
        fcm_service_account_file=str(account),
        discord_bot_token="t",
        discord_channel_id="1",
    )
    monkeypatch.setattr(job, "get_settings", lambda: connected)
    assert [n.channel for n in job.enabled_notifiers(rules_with())] == ["fcm", "discord"]
    assert [n.channel for n in job.enabled_notifiers(rules_with(fcm=False))] == ["discord"]
