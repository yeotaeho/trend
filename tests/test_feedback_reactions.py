# 디스코드 리액션 피드백 테스트 — 👍/👎 시드, 리액션 → 판정, 사용자 1 동기화, 앱 판정 제외

from types import SimpleNamespace

import httpx
import pytest
import respx
from sqlalchemy.dialects import postgresql

from app.jobs import feedback as fb
from app.notify import discord as d
from app.notify.discord import DiscordNotifier, fetch_recent_messages, reaction_verdicts
from app.schemas import Level
from tests.fakes import UpsertRecorder
from tests.test_discord import make_pair

API = "https://discord.com/api/v10"
UP, DOWN = "%F0%9F%91%8D", "%F0%9F%91%8E"


def msg(mid: str, reactions: list[tuple[str, int, bool]]) -> dict:
    return {
        "id": mid,
        "reactions": [
            {"emoji": {"name": name}, "count": count, "me": me} for name, count, me in reactions
        ],
    }


def test_reaction_verdicts_ignores_bot_seed_and_prefers_thumbs_down():
    messages = [
        msg("1", [("👍", 1, True), ("👎", 1, True)]),  # 시드만. 사용자 반응 없음
        msg("2", [("👍", 2, True), ("👎", 1, True)]),  # 사용자 👍
        msg("3", [("👍", 2, True), ("👎", 2, True)]),  # 둘 다 → 👎
        msg("4", [("👍", 1, False)]),  # 시드가 없는 메시지에 사용자 👍
        msg("5", [("🔥", 3, False)]),  # 무관한 이모지
        {"id": "6"},  # reactions 키 자체가 없음
    ]
    assert reaction_verdicts(messages) == {"2": "useful", "3": "useless", "4": "useful"}


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setattr(
        d, "get_settings", lambda: SimpleNamespace(discord_channel_id="42", discord_bot_token="t")
    )


@respx.mock
async def test_send_seeds_thumbs_reactions(settings):
    respx.post(f"{API}/channels/42/messages").mock(
        return_value=httpx.Response(200, json={"id": "99"})
    )
    up = respx.put(f"{API}/channels/42/messages/99/reactions/{UP}/@me").mock(
        return_value=httpx.Response(204)
    )
    down = respx.put(f"{API}/channels/42/messages/99/reactions/{DOWN}/@me").mock(
        return_value=httpx.Response(204)
    )
    item, summary = make_pair()
    assert (
        await DiscordNotifier().send(
            item, summary, Level.PUSH, "rss:vercel", title=summary.title_ko
        )
        == "99"
    )
    assert up.called and down.called


@respx.mock
async def test_seed_failure_does_not_fail_send(settings):
    # 메시지는 이미 나갔다. 시드 실패로 항목을 FAILED 로 만들면 다음 잡이 같은 카드를 또 보낸다.
    respx.post(f"{API}/channels/42/messages").mock(
        return_value=httpx.Response(200, json={"id": "99"})
    )
    respx.put(url__regex=r".*/reactions/.*").mock(
        return_value=httpx.Response(403, json={"message": "Missing Permissions"})
    )
    item, summary = make_pair()
    assert (
        await DiscordNotifier().send(
            item, summary, Level.PUSH, "rss:vercel", title=summary.title_ko
        )
        == "99"
    )


@respx.mock
async def test_fetch_recent_messages_returns_list(settings):
    respx.get(f"{API}/channels/42/messages", params={"limit": "100"}).mock(
        return_value=httpx.Response(200, json=[{"id": "1"}, {"id": "2"}])
    )
    assert [m["id"] for m in await fetch_recent_messages("42")] == ["1", "2"]


class _RowsSession:
    """execute 가 받은 문장을 기록하고 (message_id, item_id, 현재 판정) 행을 돌려준다."""

    def __init__(self, rows: list[tuple[str, int, str | None]]) -> None:
        self.rows = rows
        self.statements: list[object] = []

    async def execute(self, stmt: object) -> SimpleNamespace:
        self.statements.append(stmt)
        return SimpleNamespace(all=lambda: self.rows)


async def test_sync_feedback_upserts_changes_for_default_user(monkeypatch):
    recorder = UpsertRecorder()
    monkeypatch.setattr(fb, "upsert_feedback", recorder)
    session = _RowsSession([("m1", 7, None), ("m2", 8, "useful"), ("m3", 9, "useful")])

    changed = await fb.sync_feedback(
        session,  # type: ignore[arg-type]
        {"m1": "useful", "m2": "useful", "m3": "useless"},
    )

    assert changed == 2
    assert recorder.calls == [
        (1, 7, "useful", {"source": "discord"}),
        (1, 9, "useless", {"source": "discord"}),
    ]
    # 현재 판정은 사용자 1 의 것과 비교한다.
    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]
    assert "feedback.user_id = %(user_id_1)s" in sql


async def test_sync_feedback_skips_app_verdicts():
    """앱에서 정하거나 해제한 판정은 리액션 폴링 대상에서 뺀다. 판정이 없는 항목은 대상이다."""
    session = _RowsSession([])

    await fb.sync_feedback(session, {"m1": "useful"})  # type: ignore[arg-type]

    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]
    assert "feedback.source IS NULL OR feedback.source != %(source_1)s" in sql
