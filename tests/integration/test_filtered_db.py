# 걸러진 항목 API 통합 테스트 — 일곱 관문 분류, cluster_dup 합류, 탐색 후보, 복원·취소와 피드 반영

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, select

from app.api.v1 import deps
from app.api.v1.queries.filtered import build_groups, load_dropped, summarize
from app.api.v1.schemas.filtered import DroppedItem, FilteredView, Gate, GroupSort
from app.db.models import Decision, Feedback, Item, Notification, Source, User
from app.db.session import SessionLocal
from app.jobs.notify import explore_candidate
from app.main import app

TOKEN = "test-app-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
FLOOR = 0.5
THRESHOLD = 0.45
BREAKDOWN = {"src": 0.1, "rel": 0.2, "fresh": 0.1, "kind": 0.0}


@dataclass
class World:
    me: int
    other: int
    src: int
    items: dict[str, int]
    now: datetime
    cluster_at: datetime


def _triage(kind: str, relevance: float) -> dict[str, Any]:
    return {"relevance": relevance, "kind": kind, "reason": "선별", "topics": ["agent"]}


@pytest.fixture
async def world(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[World]:
    """관문마다 한 항목 + 발송된 항목. 결정 시각은 방금 전이라 복원 결정이 마지막 결정이 된다."""
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(app_api_token=TOKEN))
    now = datetime.now(UTC)
    at = now - timedelta(minutes=10)
    cluster_at = now - timedelta(minutes=5)
    statuses = {
        "exclude": "FILTERED_OUT",
        "dedup": "FILTERED_OUT",
        "stale": "DROPPED",
        "screening": "DROPPED",
        "score": "DROPPED",
        "judgment": "DROPPED",
        "cluster": "SENT",
        "delivered": "SENT",
    }
    scores = {"screening": 0.2, "score": 0.40, "judgment": 0.6, "cluster": 0.7, "delivered": 0.7}

    async with SessionLocal() as s, s.begin():
        me, other = User(name="test-filtered-me"), User(name="test-filtered-other")
        src = Source(name="test:filtered", type="rss", config={"display_name": "걸러짐 소스"})
        s.add_all([me, other, src])
        await s.flush()
        items = {
            k: Item(
                source_id=src.id,
                external_id=k,
                url=f"https://t/filtered/{k}",
                url_normalized=f"https://t/filtered/{k}",
                url_hash=f"filtered-db-{k}",
                title=f"원문 {k}",
                published_at=now - timedelta(hours=1),
                status=status,
                score=scores.get(k),
            )
            for k, status in statuses.items()
        }
        s.add_all(items.values())
        await s.flush()
        ids = {k: it.id for k, it in items.items()}

        def d(key: str, stage: str, passed: bool, minute: int, **details: Any) -> Decision:
            return Decision(
                item_id=ids[key],
                stage=stage,
                passed=passed,
                details=details,
                created_at=at + timedelta(minutes=minute),
            )

        s.add_all(
            [
                d("exclude", "rule", False, 0, reason="exclude_keyword", matched=["sponsored"]),
                d("dedup", "rule", False, 0, reason="dup", cluster_id=ids["dedup"]),
                d("stale", "score", False, 0, reason="stale", age_hours=80),
                d("screening", "triage", True, 0, **_triage("survey", 0.3)),
                d("screening", "score", False, 1, breakdown=BREAKDOWN),
                d("score", "triage", True, 0, **_triage("survey", 0.7)),
                d("score", "score", False, 1, breakdown=BREAKDOWN),
                d("judgment", "triage", True, 0, **_triage("news", 0.8)),
                d("judgment", "score", True, 1, breakdown=BREAKDOWN),
                d("judgment", "llm", False, 2, importance=2),
                d("cluster", "triage", True, 0, **_triage("release_patch", 0.9)),
                d("cluster", "score", True, 1, breakdown=BREAKDOWN),
                d("cluster", "llm", True, 2, importance=4),
                d("delivered", "llm", True, 2, importance=4),
                Notification(
                    user_id=me.id,
                    item_id=ids["cluster"],
                    channel="discord",
                    level="cluster_dup",
                    sent_at=cluster_at,
                ),
                Notification(
                    user_id=me.id,
                    item_id=ids["delivered"],
                    channel="discord",
                    level="push",
                    sent_at=cluster_at,
                ),
            ]
        )
        world = World(
            me=me.id, other=other.id, src=src.id, items=ids, now=now, cluster_at=cluster_at
        )

    try:
        yield world
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(list(world.items.values()))))
            await s.execute(delete(Source).where(Source.id == world.src))
            await s.execute(delete(User).where(User.id.in_([world.me, world.other])))


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


def _client(user_id: int) -> httpx.AsyncClient:
    app.dependency_overrides[deps.current_user_id] = lambda: user_id
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def _mine(w: World, user_id: int) -> dict[str, DroppedItem]:
    """창 안의 걸러진 항목 중 이 테스트가 만든 것만. 개발 DB 의 다른 항목과 섞지 않는다."""
    async with SessionLocal() as s:
        items = await load_dropped(
            s, user_id, w.now - timedelta(hours=1), now=w.now, floor=FLOOR, threshold=THRESHOLD
        )
    by_id = {str(v): k for k, v in w.items.items()}
    return {by_id[it.id]: it for it in items if it.id in by_id}


async def _is_candidate(w: World, key: str) -> bool:
    stmt = select(Item.id).where(Item.id == w.items[key], explore_candidate(THRESHOLD, w.now))
    async with SessionLocal() as s:
        return (await s.execute(stmt)).first() is not None


async def test_seven_gates_classified(world: World):
    mine = await _mine(world, world.me)
    assert {k: it.dropped_gate for k, it in mine.items()} == {
        "exclude": Gate.EXCLUDE,
        "dedup": Gate.DEDUP,
        "stale": Gate.STALE,
        "screening": Gate.SCREENING,
        "score": Gate.SCORE,
        "judgment": Gate.JUDGMENT,
        "cluster": Gate.CLUSTER_DUP,
    }
    assert mine["exclude"].matched_keywords == ["sponsored"]
    assert [k for k, it in mine.items() if it.exploration_candidate] == ["score"]
    cluster = mine["cluster"]
    assert cluster.dropped_at == world.cluster_at
    assert (cluster.relevance, cluster.kind, cluster.topics) == (0.9, "release_patch", ["agent"])
    assert cluster.score is not None
    assert mine["exclude"].kind is None and mine["exclude"].topics == []

    items = list(mine.values())
    summary = summarize(items, hours=1, collected=0, threshold=THRESHOLD)
    kinds = build_groups(
        items, FilteredView.KIND, GroupSort.COUNT_DESC, floor=FLOOR, kind_weights={}, feedback={}
    )
    assert sum(summary.gate_counts.values()) == summary.filtered_total == 7
    assert sum(g.count for g in kinds) == 7
    assert {g.key: g.gate_counts[Gate.CLUSTER_DUP] for g in kinds}["release_patch"] == 1

    # cluster_dup 은 사용자별이다. 다른 사용자에게는 그 알림 행이 없다.
    assert "cluster" not in await _mine(world, world.other)


async def test_restore_and_undo(world: World):
    iid = world.items["score"]
    assert await _is_candidate(world, "score")
    async with _client(world.me) as c:
        res = await c.post(f"/api/v1/filtered/items/{iid}/restore", headers=AUTH)
        assert res.status_code == 200, res.text
        body = res.json()
        assert (body["item_id"], body["restored"]) == (str(iid), True)
        assert (body["alert"]["delivery_mode"], body["alert"]["feedback"]) == (
            "feed_only",
            "useful",
        )
        # 다시 눌러도 같은 응답, 행이 늘지 않는다.
        again = await c.post(f"/api/v1/filtered/items/{iid}/restore", headers=AUTH)
        assert again.json() == body
        feed = (await c.get("/api/v1/feed", headers=AUTH)).json()["items"]
        assert feed[0]["id"] == str(iid)
        assert (feed[0]["delivery_mode"], feed[0]["feedback"]) == ("feed_only", "useful")
        listed = await c.get(
            "/api/v1/filtered/items", params={"view": "gate", "key": "score"}, headers=AUTH
        )
        restored = [it for it in listed.json()["items"] if it["id"] == str(iid)]
        assert restored and restored[0]["restored"] is True

    async with SessionLocal() as s:
        users = (
            await s.execute(
                select(Decision).where(Decision.item_id == iid, Decision.stage == "user")
            )
        ).scalars()
        assert [(u.passed, u.details) for u in users] == [
            (True, {"reason": "restored", "user_id": world.me})
        ]
        notes = (await s.execute(select(Notification).where(Notification.item_id == iid))).scalars()
        # 복원은 어느 채널로도 보내지 않는다 — 앱 피드 행 하나뿐.
        assert [(n.channel, n.level) for n in notes] == [("app", "feed")]
        assert await s.scalar(select(Item.status).where(Item.id == iid)) == "DROPPED"
    assert not await _is_candidate(world, "score")

    async with _client(world.me) as c:
        res = await c.delete(f"/api/v1/filtered/items/{iid}/restore", headers=AUTH)
        assert res.status_code == 204
        assert (await c.get("/api/v1/feed", headers=AUTH)).json()["items"] == []
    async with SessionLocal() as s:
        stages = (await s.execute(select(Decision.stage).where(Decision.item_id == iid))).scalars()
        assert "user" not in list(stages)
        assert (
            await s.execute(select(Notification.id).where(Notification.item_id == iid))
        ).first() is None
        verdict = await s.scalar(
            select(Feedback.verdict).where(Feedback.item_id == iid, Feedback.user_id == world.me)
        )
        assert verdict == "cleared"
    assert await _is_candidate(world, "score")


async def test_restore_cluster_dup_keeps_sent(world: World):
    iid = world.items["cluster"]
    async with _client(world.me) as c:
        res = await c.post(f"/api/v1/filtered/items/{iid}/restore", headers=AUTH)
        assert res.status_code == 200, res.text
        feed = (await c.get("/api/v1/feed", headers=AUTH)).json()["items"]
    assert feed[0]["id"] == str(iid) and feed[0]["delivery_mode"] == "feed_only"
    async with SessionLocal() as s:
        assert await s.scalar(select(Item.status).where(Item.id == iid)) == "SENT"
    cluster = (await _mine(world, world.me))["cluster"]
    assert cluster.restored is True and cluster.dropped_gate is Gate.CLUSTER_DUP


async def test_restore_needs_filtered_item(world: World):
    async with _client(world.me) as c:
        delivered = world.items["delivered"]
        assert (
            await c.post(f"/api/v1/filtered/items/{delivered}/restore", headers=AUTH)
        ).status_code == 404
        assert (
            await c.delete(f"/api/v1/filtered/items/{delivered}/restore", headers=AUTH)
        ).status_code == 404
        # 복원한 적 없는 걸러진 항목의 취소는 아무것도 바꾸지 않는다.
        dedup = world.items["dedup"]
        assert (
            await c.delete(f"/api/v1/filtered/items/{dedup}/restore", headers=AUTH)
        ).status_code == 204
    # 다른 사용자에게 cluster 항목은 걸러진 항목이 아니다.
    async with _client(world.other) as c:
        cluster = world.items["cluster"]
        assert (
            await c.post(f"/api/v1/filtered/items/{cluster}/restore", headers=AUTH)
        ).status_code == 404
