# 프로필·주간 리포트 통합 테스트 — 기간 집계·카테고리 반응·복원 수, 이름 변경, 리포트 upsert 한 행

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, func, select

from app.api.v1 import deps
from app.db.models import Decision, Feedback, Item, Notification, Source, User, WeeklyReport
from app.db.session import SessionLocal
from app.jobs.report import SECTION_KEYS, last_week, save_report
from app.main import app

TOKEN = "test-app-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@dataclass
class World:
    me: int
    other: int
    src: int
    items: dict[str, int]


@pytest.fixture
async def world(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[World]:
    """사용자 둘. 내 항목은 발송 강도·판정·topics 가 다르고, 다른 사용자 행은 섞이면 안 된다."""
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(app_api_token=TOKEN))
    now = datetime.now(UTC)
    at = now - timedelta(hours=1)
    old = now - timedelta(days=20)
    async with SessionLocal() as s, s.begin():
        me, other = User(name="test-profile-me"), User(name="test-profile-other")
        src = Source(name="test:profile", type="rss", config={})
        s.add_all([me, other, src])
        await s.flush()
        keys = ["push", "explore", "silent", "restored", "cluster", "error", "old"]
        items = {
            k: Item(
                source_id=src.id,
                external_id=k,
                url=f"https://t/profile/{k}",
                url_normalized=f"https://t/profile/{k}",
                url_hash=f"profile-db-{k}",
                title=f"원문 {k}",
                published_at=at,
                status="SENT",
            )
            for k in keys
        }
        s.add_all(items.values())
        await s.flush()
        ids = {k: it.id for k, it in items.items()}

        def note(key: str, level: str, *, user: int, sent_at: datetime = at, **kw: Any) -> Any:
            return Notification(
                user_id=user,
                item_id=ids[key],
                channel="discord",
                level=level,
                sent_at=sent_at,
                **kw,
            )

        def triage(key: str, topics: list[str]) -> Decision:
            details = {"relevance": 0.8, "kind": "news", "reason": "r", "topics": topics}
            return Decision(item_id=ids[key], stage="triage", passed=True, details=details)

        def verdict(key: str, value: str, *, user: int, created_at: datetime = at) -> Feedback:
            return Feedback(
                user_id=user, item_id=ids[key], verdict=value, source="app", created_at=created_at
            )

        s.add_all(
            [
                note("push", "push", user=me.id),
                # 같은 항목이 다른 채널로 또 와도 한 번이다.
                note("push", "push", user=me.id, sent_at=at + timedelta(minutes=1)),
                note("explore", "explore", user=me.id),
                note("silent", "silent", user=me.id),
                Notification(
                    user_id=me.id, item_id=ids["restored"], channel="app", level="feed", sent_at=at
                ),
                note("cluster", "cluster_dup", user=me.id),
                note("error", "push", user=me.id, error="boom"),
                note("old", "push", user=me.id, sent_at=old),
                note("explore", "push", user=other.id),
                triage("push", ["mcp-tooling", "agent"]),
                triage("explore", ["agent"]),
                triage("silent", []),
                verdict("push", "useful", user=me.id),
                verdict("explore", "useless", user=me.id),
                verdict("silent", "useful", user=me.id),
                verdict("restored", "cleared", user=me.id),
                verdict("old", "useful", user=me.id, created_at=old),
                verdict("push", "useless", user=other.id),
                Decision(
                    item_id=ids["restored"],
                    stage="user",
                    passed=True,
                    details={"reason": "restored", "user_id": me.id},
                ),
                Decision(
                    item_id=ids["old"],
                    stage="user",
                    passed=True,
                    details={"reason": "restored", "user_id": other.id},
                    created_at=old,
                ),
            ]
        )
        world = World(me=me.id, other=other.id, src=src.id, items=ids)

    try:
        yield world
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(list(world.items.values()))))
            await s.execute(delete(Source).where(Source.id == world.src))
            # weekly_reports 는 users 에 ON DELETE CASCADE 다.
            await s.execute(delete(User).where(User.id.in_([world.me, world.other])))


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


def _client(user_id: int) -> httpx.AsyncClient:
    app.dependency_overrides[deps.current_user_id] = lambda: user_id
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_profile_counts_period(world: World):
    async with _client(world.me) as c:
        body = (await c.get("/api/v1/profile", params={"period_days": 7}, headers=AUTH)).json()

    assert body["user"]["display_name"] == "test-profile-me"
    assert body["stats"] == {
        "alerts_received": 4,  # push·explore·silent·restored (cluster_dup·오류·기간 밖 제외)
        "push_count": 1,
        "experiment_count": 1,
        "useful_count": 2,
        "not_useful_count": 1,
        "useful_ratio": 67,
        "missed_issues": 1,
    }
    assert body["category_reactions"] == [
        {"category": "agent", "useful": 1, "not_useful": 1, "total": 2},
        {"category": "mcp-tooling", "useful": 1, "not_useful": 0, "total": 1},
    ]
    # 전체 판정 수는 기간과 무관하다 (cleared 제외).
    assert body["learned"]["profile_vector_labels"] == 4
    assert body["weekly_report_latest"] is None

    async with _client(world.me) as c:
        month = (await c.get("/api/v1/profile", params={"period_days": 30}, headers=AUTH)).json()
        bad = await c.get("/api/v1/profile", params={"period_days": 8}, headers=AUTH)
    assert month["stats"]["alerts_received"] == 5
    assert month["stats"]["useful_count"] == 3
    assert bad.status_code == 422


async def test_other_user_sees_only_own_rows(world: World):
    async with _client(world.other) as c:
        body = (await c.get("/api/v1/profile", headers=AUTH)).json()
    assert body["stats"]["alerts_received"] == 1
    assert (body["stats"]["useful_count"], body["stats"]["not_useful_count"]) == (0, 1)
    assert body["stats"]["useful_ratio"] == 0
    # 다른 사용자의 복원은 기간(14일) 밖이다.
    assert body["stats"]["missed_issues"] == 0


async def test_patch_renames_user(world: World):
    async with _client(world.me) as c:
        res = await c.patch("/api/v1/profile", json={"display_name": "여태호"}, headers=AUTH)
        again = await c.get("/api/v1/profile", headers=AUTH)
    assert res.status_code == 200
    assert res.json()["user"]["display_name"] == "여태호"
    assert again.json()["user"]["display_name"] == "여태호"
    async with SessionLocal() as s:
        assert await s.scalar(select(User.name).where(User.id == world.me)) == "여태호"
        assert await s.scalar(select(User.name).where(User.id == world.other)) == (
            "test-profile-other"
        )


async def test_report_job_twice_keeps_one_row(world: World):
    today = datetime.now(UTC).date()
    for _ in range(2):
        async with SessionLocal() as s, s.begin():
            await save_report(s, world.me, today, "Asia/Seoul")

    start, end = last_week(today)
    async with SessionLocal() as s:
        rows = (
            (await s.execute(select(WeeklyReport).where(WeeklyReport.user_id == world.me)))
            .scalars()
            .all()
        )
        assert (
            await s.scalar(
                select(func.count())
                .select_from(WeeklyReport)
                .where(WeeklyReport.user_id == world.other)
            )
            == 0
        )
    [row] = rows
    assert (row.period_start, row.period_end) == (start, end)
    assert set(row.sections) == set(SECTION_KEYS) and len(row.sections) == 8

    async with _client(world.me) as c:
        latest = (await c.get("/api/v1/profile", headers=AUTH)).json()["weekly_report_latest"]
        listing = (await c.get("/api/v1/reports", headers=AUTH)).json()
        detail = (await c.get(f"/api/v1/reports/{row.id}", headers=AUTH)).json()
    async with _client(world.other) as c:
        hidden = await c.get(f"/api/v1/reports/{row.id}", headers=AUTH)

    assert latest["id"] == str(row.id)
    assert latest["period_start"] == start.isoformat()
    assert [i["id"] for i in listing["items"]] == [str(row.id)]
    assert [sec["key"] for sec in detail["sections"]] == list(SECTION_KEYS)
    assert detail["period_end"] == end.isoformat()
    assert hidden.status_code == 404
