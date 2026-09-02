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
    assert "#nextjs #release" in text


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
