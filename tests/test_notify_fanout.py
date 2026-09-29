# 채널 팬아웃 테스트 — 채널별 기록·부분 실패·RateLimited 중단·피드 전용·클러스터 억제·탐색 토글

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import respx
from sqlalchemy.dialects import postgresql

from app.config import ChannelsConfig, NotifyConfig, Rules
from app.db.models import Item, Notification, Source, Summary
from app.jobs import notify as job
from app.notify import policy
from app.notify.base import APP_CHANNEL, RateLimited
from app.notify.policy import Verdict
from app.notify.telegram import TelegramNotifier
from app.schemas import ItemStatus, Level

NOW = datetime(2026, 9, 24, 3, 0, tzinfo=UTC)  # KST 12시, 무음 시간 밖
TITLE = "[릴리즈] MCP Python SDK v2.2.0 (v2.2.0 · v1.30.0)"


class FakeNotifier:
    def __init__(self, channel: str, error: Exception | None = None) -> None:
        self.channel = channel
        self.error = error
        self.calls: list[tuple[int, Level, str]] = []

    async def send(
        self, item: Item, summary: Summary, level: Level, source_name: str, *, title: str
    ) -> str:
        self.calls.append((item.id, level, title))
        if self.error:
            raise self.error
        return f"{self.channel}-{item.id}"


class FakeSession:
    def __init__(self) -> None:
        self.rows: list[Notification] = []
        self.commits = 0

    def add(self, row: Notification) -> None:
        self.rows.append(row)

    def add_all(self, rows: list[Notification]) -> None:
        self.rows.extend(rows)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass


def make_triple(item_id: int = 7) -> tuple[Item, Summary, Source]:
    item = Item(
        id=item_id,
        url="https://example.com/a",
        title="MCP Python SDK v2.2.0 released",
        published_at=NOW - timedelta(minutes=12),
        status=ItemStatus.SCORED.value,
        cluster_id=1,
    )
    summary = Summary(
        item_id=item_id,
        title_ko="[릴리즈] MCP Python SDK v2.2.0",
        summary_ko="요약",
        tags=[],
        importance=5,
        worth_notifying=True,
        model="m",
    )
    return item, summary, Source(id=1, name="rss:mcp", type="rss", config={})


async def deliver(session: FakeSession, notifiers: list[Any], item: Item, summary: Summary):
    return await job.deliver(
        session,  # type: ignore[arg-type]
        notifiers,
        item,
        summary,
        Level.PUSH,
        "rss:mcp",
        title=TITLE,
    )


# ---------- deliver ----------


async def test_both_channels_get_same_title_and_rows():
    session, (item, summary, _) = FakeSession(), make_triple()
    a, b = FakeNotifier("discord"), FakeNotifier("telegram")

    assert await deliver(session, [a, b], item, summary) is True

    assert a.calls == b.calls == [(7, Level.PUSH, TITLE)]
    assert [(r.channel, r.message_id, r.error, r.title) for r in session.rows] == [
        ("discord", "discord-7", None, TITLE),
        ("telegram", "telegram-7", None, TITLE),
    ]
    assert item.status == ItemStatus.SENT.value


async def test_one_channel_failing_still_sent():
    session, (item, summary, _) = FakeSession(), make_triple()
    notifiers = [FakeNotifier("discord", RuntimeError("boom")), FakeNotifier("telegram")]

    assert await deliver(session, notifiers, item, summary) is True

    assert [r.error for r in session.rows] == ["RuntimeError: boom", None]
    assert item.status == ItemStatus.SENT.value


async def test_all_channels_failing_is_failed():
    session, (item, summary, _) = FakeSession(), make_triple()
    notifiers = [FakeNotifier("discord", RuntimeError("a")), FakeNotifier("telegram", ValueError())]

    assert await deliver(session, notifiers, item, summary) is False

    assert len(session.rows) == 2 and all(r.error for r in session.rows)
    assert item.status == ItemStatus.FAILED.value


async def test_first_channel_rate_limited_records_nothing():
    session, (item, summary, _) = FakeSession(), make_triple()
    second = FakeNotifier("telegram")

    assert (
        await deliver(session, [FakeNotifier("discord", RateLimited()), second], item, summary)
        is None
    )

    assert session.rows == [] and second.calls == []
    assert item.status == ItemStatus.SCORED.value


async def test_rate_limited_after_success_marks_that_channel():
    session, (item, summary, _) = FakeSession(), make_triple()
    notifiers = [FakeNotifier("discord"), FakeNotifier("telegram", RateLimited())]

    assert await deliver(session, notifiers, item, summary) is True

    assert [(r.channel, r.error) for r in session.rows] == [
        ("discord", None),
        ("telegram", "rate_limited"),
    ]


# ---------- run_notify 루프 ----------


@pytest.fixture
def loop(monkeypatch):
    """DB 없이 발송 루프를 돌린다. 대기 항목·정책 판정·발송 제목을 갈아끼운다."""
    state = SimpleNamespace(
        session=FakeSession(), queue=[], verdict=Verdict(Level.PUSH, "ok"), explore_calls=0
    )

    @asynccontextmanager
    async def scope():
        yield state.session

    async def claim_one(_session):
        return state.queue.pop(0) if state.queue else None

    async def decide(*_, **__):
        return state.verdict

    async def send_title(*_):
        return TITLE

    async def explore(*_, **__):
        state.explore_calls += 1
        return False

    monkeypatch.setattr(job, "session_scope", scope)
    monkeypatch.setattr(job, "_claim_one", claim_one)
    monkeypatch.setattr(job, "decide", decide)
    monkeypatch.setattr(job, "_send_title", send_title)
    monkeypatch.setattr(job, "_explore", explore)
    monkeypatch.setattr(job, "get_rules", lambda: Rules())
    return state


async def test_loop_stops_batch_on_first_channel_rate_limit(loop):
    loop.queue = [make_triple(1), make_triple(2)]
    notifier = FakeNotifier("discord", RateLimited())

    assert await job.run_notify([notifier]) == 0

    assert loop.session.rows == [] and len(notifier.calls) == 1  # 두 번째 항목은 시도하지 않음
    assert loop.explore_calls == 0  # 대기 중인 채널로 탐색 판정 예산을 태우지 않는다


async def test_loop_counts_items_not_channel_rows(loop):
    loop.queue = [make_triple(1), make_triple(2)]
    assert await job.run_notify([FakeNotifier("discord"), FakeNotifier("telegram")]) == 2
    assert len(loop.session.rows) == 4
    assert loop.explore_calls == 1


async def test_cluster_dup_records_app_row_without_adapter_call(loop):
    loop.queue = [make_triple()]
    loop.verdict = Verdict(Level.CLUSTER_DUP, "cluster_dup")
    notifier = FakeNotifier("discord")

    assert await job.run_notify([notifier]) == 0

    assert notifier.calls == []
    [row] = loop.session.rows
    assert (row.channel, row.level, row.message_id) == (APP_CHANNEL, "cluster_dup", None)


async def test_no_enabled_channel_keeps_cluster_dup(loop):
    loop.queue = [make_triple()]
    loop.verdict = Verdict(Level.CLUSTER_DUP, "cluster_dup")
    assert await job.run_notify([]) == 0
    assert [r.level for r in loop.session.rows] == ["cluster_dup"]


async def test_no_enabled_channel_records_feed_only(loop):
    loop.queue = [make_triple()]
    item = loop.queue[0][0]

    assert await job.run_notify([]) == 0

    [row] = loop.session.rows
    assert (row.channel, row.level) == (APP_CHANNEL, Level.FEED.value)
    assert item.status == ItemStatus.SENT.value


# ---------- 채널 목록 ----------


def settings(**kw: str) -> SimpleNamespace:
    base = dict.fromkeys(
        (
            "fcm_project_id",
            "fcm_service_account_file",
            "discord_bot_token",
            "discord_channel_id",
            "telegram_bot_token",
            "telegram_chat_id",
        ),
        "",
    )
    return SimpleNamespace(**{**base, **kw})


def rules_with(**channels: bool) -> Rules:
    return Rules(notify=NotifyConfig(channels=ChannelsConfig(**channels)))


def test_enabled_notifiers_needs_both_toggle_and_connection(monkeypatch):
    monkeypatch.setattr(
        job, "get_settings", lambda: settings(discord_bot_token="t", discord_channel_id="1")
    )
    assert [n.channel for n in job.enabled_notifiers(rules_with(telegram=True))] == ["discord"]
    assert job.enabled_notifiers(rules_with(discord=False)) == []


@respx.mock
async def test_telegram_enabled_and_connected_is_called(monkeypatch):
    from app.notify import telegram

    connected = settings(telegram_bot_token="tok", telegram_chat_id="99")
    monkeypatch.setattr(job, "get_settings", lambda: connected)
    monkeypatch.setattr(telegram, "get_settings", lambda: connected)
    route = respx.post("https://api.telegram.org/bottok/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 5}})
    )

    notifiers = job.enabled_notifiers(rules_with(discord=False, telegram=True))
    assert [type(n) for n in notifiers] == [TelegramNotifier]

    session, (item, summary, _) = FakeSession(), make_triple()
    assert await deliver(session, notifiers, item, summary) is True
    assert route.called
    assert TITLE in route.calls.last.request.content.decode()
    assert session.rows[0].message_id == "5"


# ---------- push 상한 집계 ----------


async def test_push_count_counts_distinct_items():
    captured = []

    class Capture:
        async def execute(self, stmt):
            captured.append(str(stmt.compile(dialect=postgresql.dialect())))
            return SimpleNamespace(scalar_one=lambda: 0)

    await policy.push_count_today(Capture(), NotifyConfig(), NOW)  # type: ignore[arg-type]
    await policy.cluster_sent_today(Capture(), NotifyConfig(), 1, 1, NOW)  # type: ignore[arg-type]
    assert all("count(DISTINCT notifications.item_id)" in sql for sql in captured)


# ---------- 탐색 토글 ----------


async def test_explore_disabled_reserves_no_llm_call(monkeypatch):
    calls = []

    async def record(*args, **_):
        calls.append(args)

    monkeypatch.setattr(job, "reserve_call", record)
    monkeypatch.setattr(job.llm, "body_for_judge", record)
    monkeypatch.setattr(job, "_explore_sent_today", record)
    rules = Rules(notify=NotifyConfig(explore_enabled=False))

    assert await job._explore(None, rules, [FakeNotifier("discord")], now=NOW) is False  # type: ignore[arg-type]
    assert await job._explore(None, Rules(), [], now=NOW) is False  # type: ignore[arg-type]
    assert calls == []


# ---------- 발송 제목 ----------


class TitlesSession:
    def __init__(self, titles: list[str]) -> None:
        self.titles = titles

    async def execute(self, _stmt):
        return SimpleNamespace(scalars=lambda: iter(self.titles))


async def test_send_title_without_siblings_is_unchanged():
    item, summary, _ = make_triple()
    item.title = "Upgrade from v1.9 to v1.10"
    title = await job._send_title(TitlesSession([]), Rules(), item, summary, NOW)  # type: ignore[arg-type]
    assert title == summary.title_ko


async def test_send_title_appends_sibling_versions():
    item, summary, _ = make_triple()
    session = TitlesSession(["MCP Python SDK v1.30.0 released"])
    title = await job._send_title(session, Rules(), item, summary, NOW)  # type: ignore[arg-type]
    assert title == "[릴리즈] MCP Python SDK v2.2.0 (v2.2.0 · v1.30.0)"
