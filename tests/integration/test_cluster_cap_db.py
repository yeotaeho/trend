# 클러스터 하루 상한 통합 테스트 — 같은 클러스터 두 번째 항목 억제·어제 발송·DISTINCT 집계·제목 병기

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.config import NotifyConfig, Rules
from app.db.budget import today_start
from app.db.models import Item, Notification, Source, Summary
from app.db.session import SessionLocal
from app.db.users import DEFAULT_USER_ID
from app.jobs import notify as job
from app.notify.base import APP_CHANNEL
from app.notify.policy import push_count_today
from app.schemas import Level
from tests.test_notify_fanout import FakeNotifier

TZ = "Asia/Seoul"


@dataclass
class Pair:
    a: int
    b: int
    src: int


def _item(src_id: int, key: str, title: str, status: str) -> Item:
    return Item(
        source_id=src_id,
        external_id=key,
        url=f"https://t/cap/{key}",
        url_normalized=f"https://t/cap/{key}",
        url_hash=f"cluster-cap-{key}",
        title=title,
        published_at=datetime.now(UTC) - timedelta(hours=1),
        status=status,
    )


def _summary(item_id: int, title_ko: str) -> Summary:
    return Summary(
        item_id=item_id,
        title_ko=title_ko,
        summary_ko="요약",
        tags=[],
        importance=5,
        worth_notifying=True,
        model="m",
    )


def _rules(cap: int) -> Rules:
    # 무음 시간을 끈다. 테스트가 밤에 돌아도 피드 전용으로 빠지지 않게 한다.
    return Rules(notify=NotifyConfig(quiet_start_hour=0, quiet_end_hour=0, cluster_daily_cap=cap))


@pytest.fixture
async def pair(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Pair]:
    """같은 클러스터의 A(SENT, v1.30.0)와 B(SCORED, v2.2.0). A 의 발송 행은 테스트가 넣는다."""
    async with SessionLocal() as s, s.begin():
        src = Source(name="test:cluster-cap", type="rss", config={})
        s.add(src)
        await s.flush()
        a = _item(src.id, "a", "MCP Python SDK v1.30.0 released", "SENT")
        b = _item(src.id, "b", "MCP Python SDK v2.2.0 released", "SCORED")
        s.add_all([a, b])
        await s.flush()
        a.cluster_id = b.cluster_id = a.id
        s.add_all([_summary(a.id, "[릴리즈] v1.30.0"), _summary(b.id, "[릴리즈] v2.2.0")])
        ids = Pair(a.id, b.id, src.id)

    async def claim_ours(session):
        # dev DB 의 다른 대기 항목을 건드리지 않는다. B 만 잡는다.
        stmt = (
            select(Item, Summary, Source)
            .join(Summary, Summary.item_id == Item.id)
            .join(Source, Source.id == Item.source_id)
            .where(Item.id == ids.b, Item.status.in_(job.PENDING))
            .with_for_update(of=Item)
        )
        row = (await session.execute(stmt)).first()
        return (row[0], row[1], row[2]) if row else None

    async def no_explore(*_, **__):
        return False

    monkeypatch.setattr(job, "_claim_one", claim_ours)
    monkeypatch.setattr(job, "_explore", no_explore)
    try:
        yield ids
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_([ids.a, ids.b])))
            await s.execute(delete(Source).where(Source.id == ids.src))


async def _sent_a(pair: Pair, at: datetime, channels: tuple[str, ...] = ("discord",)) -> None:
    async with SessionLocal() as s, s.begin():
        for channel in channels:
            s.add(
                Notification(
                    user_id=DEFAULT_USER_ID,
                    item_id=pair.a,
                    channel=channel,
                    level=Level.PUSH.value,
                    message_id="m",
                    sent_at=at,
                )
            )


async def _rows_b(pair: Pair) -> list[Notification]:
    async with SessionLocal() as s:
        stmt = select(Notification).where(Notification.item_id == pair.b)
        return list((await s.execute(stmt)).scalars())


async def _status_b(pair: Pair) -> str:
    async with SessionLocal() as s:
        return (await s.execute(select(Item.status).where(Item.id == pair.b))).scalar_one()


async def test_second_item_in_cluster_is_suppressed(pair, monkeypatch):
    monkeypatch.setattr(job, "get_rules", lambda: _rules(1))
    await _sent_a(pair, datetime.now(UTC))
    notifier = FakeNotifier("discord")

    assert await job.run_notify([notifier]) == 0

    assert notifier.calls == []
    [row] = await _rows_b(pair)
    assert (row.level, row.channel, row.message_id) == ("cluster_dup", APP_CHANNEL, None)
    assert await _status_b(pair) == "SENT"


async def test_two_channel_rows_count_as_one_item(pair, monkeypatch):
    # 행 수(2)로 세면 상한 2 에 걸린다. 서로 다른 항목 수(1)로 세야 B 가 나간다.
    await _sent_a(pair, datetime.now(UTC), channels=("discord", "telegram"))
    monkeypatch.setattr(job, "get_rules", lambda: _rules(2))
    assert await job.run_notify([FakeNotifier("discord")]) == 1


async def test_two_channel_rows_still_suppress_at_cap_one(pair, monkeypatch):
    await _sent_a(pair, datetime.now(UTC), channels=("discord", "telegram"))
    monkeypatch.setattr(job, "get_rules", lambda: _rules(1))
    assert await job.run_notify([FakeNotifier("discord")]) == 0
    assert [r.level for r in await _rows_b(pair)] == ["cluster_dup"]


async def test_sent_yesterday_does_not_suppress_and_title_is_decorated(pair, monkeypatch):
    monkeypatch.setattr(job, "get_rules", lambda: _rules(1))
    await _sent_a(pair, today_start(TZ, datetime.now(UTC)) - timedelta(hours=1))
    discord, telegram = FakeNotifier("discord"), FakeNotifier("telegram")

    assert await job.run_notify([discord, telegram]) == 1

    title = "[릴리즈] v2.2.0 (v2.2.0 · v1.30.0)"
    assert [c[2] for c in discord.calls + telegram.calls] == [title, title]
    rows = await _rows_b(pair)
    assert sorted(r.channel for r in rows) == ["discord", "telegram"]
    assert all(r.title == title and r.error is None for r in rows)


async def test_cap_zero_sends_second_item(pair, monkeypatch):
    monkeypatch.setattr(job, "get_rules", lambda: _rules(0))
    await _sent_a(pair, datetime.now(UTC))
    notifier = FakeNotifier("discord")

    assert await job.run_notify([notifier]) == 1
    assert len(notifier.calls) == 1


async def test_push_cap_counts_items_and_ignores_cluster_dup(pair):
    cfg = NotifyConfig()
    now = datetime.now(UTC)
    async with SessionLocal() as s:
        before = await push_count_today(s, cfg, now)
    await _sent_a(pair, now, channels=("discord", "telegram"))
    async with SessionLocal() as s, s.begin():
        s.add(
            Notification(
                user_id=DEFAULT_USER_ID,
                item_id=pair.b,
                channel=APP_CHANNEL,
                level=Level.CLUSTER_DUP.value,
                sent_at=now,
            )
        )
    async with SessionLocal() as s:
        assert await push_count_today(s, cfg, now) == before + 1
