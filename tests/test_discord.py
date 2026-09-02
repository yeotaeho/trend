# 디스코드 발송·인터랙션 테스트 — 마크다운 이스케이프, 무음 플래그, 서명 검증, 오류 처리

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from nacl.signing import SigningKey

from app.api.discord import verify_signature
from app.db.models import Item, Summary
from app.notify.discord import (
    FLAG_SUPPRESS_NOTIFICATIONS,
    _call,
    build_payload,
    escape_md,
    render,
)
from app.schemas import Level

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)


def make_pair():
    item = Item(
        id=7,
        url="https://example.com/a",
        title="Next.js 16",
        published_at=NOW - timedelta(minutes=12),
    )
    summary = Summary(
        item_id=7,
        title_ko="[릴리즈] Next.js 16 *정식* 출시",
        summary_ko="주요 변경 3가지. @everyone 참고",
        tags=["nextjs", "release"],
        importance=4,
        worth_notifying=True,
        model="claude-haiku-4-5",
    )
    return item, summary


def test_escape_md_neutralizes_formatting():
    assert escape_md("a *b* _c_ ~d~ `e` |f| g\\h") == r"a \*b\* \_c\_ \~d\~ \`e\` \|f\| g\\h"


def test_render_escapes_and_includes_source():
    item, summary = make_pair()
    text = render(item, summary, "rss:vercel", now=NOW)

    assert r"\*정식\*" in text
    assert "출처: rss:vercel · 12분 전" in text
    assert r"\#nextjs \#release" in text  # \# 는 디스코드에서 # 로 보인다


def test_push_payload_has_buttons_and_no_mentions():
    item, summary = make_pair()
    payload = build_payload(item, summary, Level.PUSH, "rss:vercel")

    assert "flags" not in payload
    assert payload["allowed_mentions"] == {"parse": []}
    buttons = payload["components"][0]["components"]
    assert buttons[0]["url"] == "https://example.com/a"
    assert [b["custom_id"] for b in buttons[1:]] == ["fb:useful:7", "fb:useless:7"]


def test_silent_payload_sets_suppress_flag():
    item, summary = make_pair()
    payload = build_payload(item, summary, Level.SILENT, "rss:vercel")

    assert payload["flags"] == FLAG_SUPPRESS_NOTIFICATIONS


def test_signature_roundtrip_and_tamper():
    key = SigningKey.generate()
    public = key.verify_key.encode().hex()
    body = b'{"type":1}'
    timestamp = "1700000000"
    signature = key.sign(timestamp.encode() + body).signature.hex()

    assert verify_signature(public, signature, timestamp, body)
    assert not verify_signature(public, signature, timestamp, b'{"type":3}')
    assert not verify_signature(public, signature, "1700000001", body)
    assert not verify_signature(public, "zz", timestamp, body)
    assert not verify_signature("not-hex", signature, timestamp, body)


@respx.mock
async def test_api_error_keeps_status_and_body_but_not_token():
    respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        return_value=httpx.Response(403, json={"message": "Missing Access", "code": 50001})
    )

    with pytest.raises(RuntimeError) as exc:
        await _call("POST", "/channels/42/messages", {})

    assert "403" in str(exc.value)
    assert "Missing Access" in str(exc.value)
    assert "test-discord-token" not in str(exc.value)


def test_escape_md_covers_link_masking_and_line_markers():
    assert escape_md("[x](https://e.com) # h > q - l") == r"\[x\]\(https://e.com\) \# h \> q \- l"


def test_link_button_omitted_for_bad_scheme_or_long_url():
    item, summary = make_pair()
    item.url = "javascript:alert(1)"
    buttons = build_payload(item, summary, Level.PUSH, "rss:x")["components"][0]["components"]
    assert [b.get("custom_id") for b in buttons] == ["fb:useful:7", "fb:useless:7"]

    item.url = "https://example.com/" + "a" * 600
    buttons = build_payload(item, summary, Level.PUSH, "rss:x")["components"][0]["components"]
    assert all("url" not in b for b in buttons)


@pytest.fixture
def no_sleep(monkeypatch):
    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.notify.discord.asyncio.sleep", _instant)


@respx.mock
async def test_permanent_4xx_is_not_retried(no_sleep):
    route = respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        return_value=httpx.Response(401, json={"message": "401: Unauthorized"})
    )
    with pytest.raises(RuntimeError, match="401"):
        await _call("POST", "/channels/42/messages", {})
    assert route.call_count == 1


@respx.mock
async def test_5xx_is_retried_three_times(no_sleep):
    route = respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        return_value=httpx.Response(502, text="bad gateway")
    )
    with pytest.raises(RuntimeError, match="502.*3회"):
        await _call("POST", "/channels/42/messages", {})
    assert route.call_count == 3


@respx.mock
async def test_429_waits_retry_after_then_succeeds(no_sleep):
    route = respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        side_effect=[
            httpx.Response(429, json={"retry_after": 0.5, "global": False}),
            httpx.Response(200, json={"id": "999"}),
        ]
    )
    body = await _call("POST", "/channels/42/messages", {})
    assert body["id"] == "999"
    assert route.call_count == 2


@respx.mock
async def test_429_beyond_max_wait_fails_without_retry(no_sleep):
    route = respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        return_value=httpx.Response(429, json={"retry_after": 120.0, "global": True})
    )
    with pytest.raises(RuntimeError, match="retry_after 120"):
        await _call("POST", "/channels/42/messages", {})
    assert route.call_count == 1  # 디스코드가 준 시간보다 빨리 다시 보내지 않는다


@respx.mock
async def test_requests_carry_discord_user_agent():
    route = respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        return_value=httpx.Response(200, json={"id": "1"})
    )
    await _call("POST", "/channels/42/messages", {})
    ua = route.calls.last.request.headers["user-agent"]
    assert ua.startswith("DiscordBot (")


@pytest.fixture(autouse=True)
def reset_discord_gate(monkeypatch):
    """429 테스트가 세운 프로세스 전역 게이트가 다른 테스트로 새지 않게 한다."""
    monkeypatch.setattr("app.notify.discord._blocked_until", 0.0)


@respx.mock
async def test_long_429_raises_rate_limited_and_blocks_following_calls(no_sleep):
    from app.notify.base import RateLimited

    route = respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        return_value=httpx.Response(429, json={"retry_after": 120.0, "global": True})
    )
    with pytest.raises(RateLimited, match="retry_after 120"):
        await _call("POST", "/channels/42/messages", {})
    assert route.call_count == 1

    # 게이트가 열리기 전의 다른 요청은 네트워크에 닿지 않는다.
    with pytest.raises(RateLimited, match="대기 중"):
        await _call("POST", "/channels/42/messages", {"other": True})
    assert route.call_count == 1


@respx.mock
async def test_expired_gate_lets_requests_through(monkeypatch):
    import time

    monkeypatch.setattr("app.notify.discord._blocked_until", time.monotonic() - 1)
    route = respx.post("https://discord.com/api/v10/channels/42/messages").mock(
        return_value=httpx.Response(200, json={"id": "1"})
    )
    assert (await _call("POST", "/channels/42/messages", {}))["id"] == "1"
    assert route.call_count == 1
