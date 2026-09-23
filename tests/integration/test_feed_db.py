# 피드·상세·피드백 API 통합 테스트 — 카드 합치기·필터·커서·사용자 분리·근거 조립·앱 판정 우선

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
from app.api.v1.queries.alerts import recent_feedback
from app.api.v1.queries.filtered import filtered_total
from app.db.budget import today_start
from app.db.models import (
    Bookmark,
    Decision,
    Feedback,
    Item,
    Notification,
    Source,
    Summary,
    User,
)
from app.db.session import SessionLocal
from app.db.users import DEFAULT_USER_ID
from app.jobs.feedback import sync_feedback
from app.main import app

TOKEN = "test-app-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
TZ = "Asia/Seoul"


@dataclass
class World:
    me: int
    other: int
    src: int
    items: dict[str, int]
    t0: datetime


def _item(src_id: int, key: str, **kw: Any) -> Item:
    return Item(
        source_id=src_id,
        external_id=key,
        url=f"https://t/feed/{key}",
        url_normalized=f"https://t/feed/{key}",
        url_hash=f"feed-db-{key}",
        title=kw.pop("title", f"원문 {key}"),
        published_at=kw.pop("published_at", datetime.now(UTC)),
        **kw,
    )


def _summary(item_id: int, title: str, importance: int = 4) -> Summary:
    return Summary(
        item_id=item_id,
        title_ko=title,
        summary_ko=f"{title} 요약",
        tags=["t"],
        importance=importance,
        worth_notifying=True,
        model="m",
    )


def _note(user_id: int, item_id: int, level: str, at: datetime, **kw: Any) -> Notification:
    return Notification(
        user_id=user_id,
        item_id=item_id,
        channel=kw.pop("channel", "discord"),
        level=level,
        sent_at=at,
        **kw,
    )


@pytest.fixture
async def world(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[World]:
    """현재 사용자(me)와 다른 사용자(other)를 새로 만든다. 운영 사본 데이터와 섞이지 않는다."""
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(app_api_token=TOKEN))
    now = datetime.now(UTC)
    # 모든 발송 시각이 같은 서울 달력일에 들어가게 자정 직후에서 시작한다.
    t0 = today_start(TZ, now).astimezone(UTC) + timedelta(minutes=1)
    at = {n: t0 + timedelta(minutes=n) for n in range(0, 100, 5)}

    async with SessionLocal() as s, s.begin():
        me, other = User(name="test-feed-me"), User(name="test-feed-other")
        src = Source(name="test:feed", type="rss", config={"display_name": "테스트 소스"})
        s.add_all([me, other, src])
        await s.flush()
        keys = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        items = {k: _item(src.id, k) for k in keys}
        items["c"].summary_raw = "가" * 300
        items["e"].status = "SENT"
        items["j"].status = "DROPPED"
        s.add_all(items.values())
        await s.flush()
        ids = {k: it.id for k, it in items.items()}

        s.add_all(
            [
                _summary(ids["a"], "요약 A"),
                _summary(ids["b"], "요약 B", 3),
                _summary(ids["h"], "요약 H"),
                # a — 디스코드·FCM 두 행. 이른 쪽(FCM)이 카드 시각·발송 제목이다.
                _note(me.id, ids["a"], "push", at[10], title="발송 A 늦은 행"),
                _note(me.id, ids["a"], "push", at[5], channel="fcm", title="발송 A"),
                _note(me.id, ids["b"], "silent", at[20]),
                _note(me.id, ids["c"], "explore", at[30]),
                _note(me.id, ids["d"], "feed", at[40]),
                _note(me.id, ids["i"], "feed", at[40]),  # d 와 시각이 같다 → id 내림차순
                _note(me.id, ids["e"], "cluster_dup", at[50]),
                _note(me.id, ids["f"], "push", at[60], error="HTTPError: 500"),
                _note(other.id, ids["g"], "push", at[70]),
                _note(me.id, ids["h"], "push", at[80]),
                Feedback(user_id=me.id, item_id=ids["b"], verdict="useful", source="app"),
                Feedback(user_id=other.id, item_id=ids["b"], verdict="useless"),
                Feedback(user_id=other.id, item_id=ids["h"], verdict="useful"),
                Bookmark(user_id=me.id, item_id=ids["h"]),
                Bookmark(user_id=other.id, item_id=ids["a"]),
                Decision(
                    item_id=ids["a"],
                    stage="triage",
                    passed=True,
                    details={"relevance": 0.4, "reason": "옛 선별", "kind": "news"},
                    created_at=at[0],
                ),
                Decision(
                    item_id=ids["a"],
                    stage="triage",
                    passed=True,
                    details={
                        "relevance": 0.83,
                        "reason": "구체 기법",
                        "kind": "technique",
                        "topics": ["mcp-tooling", "python-backend"],
                    },
                    created_at=at[0] + timedelta(seconds=30),
                ),
                Decision(
                    item_id=ids["a"],
                    stage="triage",
                    passed=False,
                    details={"reason": "triage_error"},
                    created_at=at[0] + timedelta(minutes=2),
                ),
                Decision(
                    item_id=ids["a"],
                    stage="score",
                    passed=True,
                    details={"breakdown": {"src": 0.1, "rel": 0.25, "fresh": 0.1, "kind": 0.05}},
                    created_at=at[0] + timedelta(minutes=3),
                ),
                Decision(
                    item_id=ids["a"],
                    stage="llm",
                    passed=True,
                    details={
                        "importance": 4,
                        "examples": [
                            {"item_id": 17220, "verdict": "useless", "title": "옛 사례"},
                            {"item_id": 1, "verdict": "cleared", "title": "해제는 빠진다"},
                        ],
                    },
                    created_at=at[0] + timedelta(minutes=4),
                ),
                Decision(
                    item_id=ids["j"],
                    stage="score",
                    passed=False,
                    details={"reason": "stale", "age_hours": 80},
                    created_at=at[0],
                ),
            ]
        )
        world = World(me=me.id, other=other.id, src=src.id, items=ids, t0=t0)

    try:
        yield world
    finally:
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(Item).where(Item.id.in_(list(world.items.values()))))
            await s.execute(delete(Source).where(Source.id == world.src))
            await s.execute(delete(User).where(User.id.in_([world.me, world.other])))


def _client(user_id: int) -> httpx.AsyncClient:
    app.dependency_overrides[deps.current_user_id] = lambda: user_id
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


async def _ids(client: httpx.AsyncClient, w: World, **params: Any) -> list[str]:
    res = await client.get("/api/v1/feed", params=params, headers=AUTH)
    assert res.status_code == 200, res.text
    by_id = {str(v): k for k, v in w.items.items()}
    return [by_id[a["id"]] for a in res.json()["items"]]


async def test_feed_merges_channels_and_hides_undelivered(world: World):
    async with _client(world.me) as c:
        res = await c.get("/api/v1/feed", headers=AUTH)
    body = res.json()
    cards = {a["id"]: a for a in body["items"]}
    ids = world.items
    # e(cluster_dup 만)·f(오류 행만)·g(다른 사용자)·j(미발송) 는 없다. a 는 한 장.
    first_i_then_d = [ids["i"], ids["d"]] if ids["i"] > ids["d"] else [ids["d"], ids["i"]]
    expected = [ids["h"], *first_i_then_d, ids["c"], ids["b"], ids["a"]]
    assert [int(a["id"]) for a in body["items"]] == expected
    assert body["next_cursor"] is None

    a = cards[str(ids["a"])]
    assert a["delivered_at"] == (world.t0 + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert a["delivery_mode"] == "instant"
    assert a["title"] == "발송 A"  # notifications.title 우선
    assert a["categories"] == ["mcp-tooling", "python-backend"]  # 마지막 성공 선별 행
    assert a["source_id"] == "test:feed" and a["source_name"] == "테스트 소스"
    assert a["is_saved"] is False  # 다른 사용자의 찜
    assert a["feedback"] is None

    b = cards[str(ids["b"])]
    assert (b["title"], b["delivery_mode"], b["feedback"]) == ("요약 B", "quiet", "useful")
    assert b["categories"] == []  # 선별 결정 없음

    c_ = cards[str(ids["c"])]
    assert c_["title"] == "원문 c" and c_["summary"] == "가" * 200
    assert c_["delivery_mode"] == "experiment" and c_["is_exploration"] is True
    assert c_["importance"] is None and c_["tags"] == []

    h = cards[str(ids["h"])]
    assert h["is_saved"] is True and h["feedback"] is None  # 다른 사용자의 판정은 섞이지 않는다
    assert cards[str(ids["d"])]["delivery_mode"] == "feed_only"


async def test_feed_filters(world: World):
    async with _client(world.me) as c:
        assert await _ids(c, world, filter="instant") == ["h", "a"]
        assert await _ids(c, world, filter="quiet") == ["b"]
        assert await _ids(c, world, filter="experiment") == ["c"]
        assert await _ids(c, world, filter="useful") == ["b"]
        assert len(await _ids(c, world, filter="all")) == 6


async def test_feed_cursor_pages_have_no_gaps_or_duplicates(world: World):
    seen: list[str] = []
    async with _client(world.me) as c:
        full = await _ids(c, world)
        cursor = None
        for _ in range(10):
            params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
            res = (await c.get("/api/v1/feed", params=params, headers=AUTH)).json()
            seen += [a["id"] for a in res["items"]]
            cursor = res["next_cursor"]
            if cursor is None:
                break
    by_id = {str(v): k for k, v in world.items.items()}
    # 시각이 같은 d·i 가 페이지 경계에 걸려도 빠지거나 겹치지 않는다.
    assert [by_id[i] for i in seen] == full


async def test_other_user_sees_only_own_rows(world: World):
    async with _client(world.other) as c:
        body = (await c.get("/api/v1/feed", headers=AUTH)).json()
    assert [int(a["id"]) for a in body["items"]] == [world.items["g"]]


async def test_alert_detail_rationale(world: World):
    ids = world.items
    async with _client(world.me) as c:
        a = (await c.get(f"/api/v1/alerts/{ids['a']}", headers=AUTH)).json()
        e = (await c.get(f"/api/v1/alerts/{ids['e']}", headers=AUTH)).json()
        j = (await c.get(f"/api/v1/alerts/{ids['j']}", headers=AUTH)).json()
        cx = (await c.get(f"/api/v1/alerts/{ids['c']}", headers=AUTH)).json()
        missing = await c.get("/api/v1/alerts/2147483647", headers=AUTH)

    assert a["title"] == "발송 A" and a["delivery_mode"] == "instant"
    r = a["rationale"]
    assert r["routing"] == "passed"
    assert r["score"]["components"] == {"src": 0.1, "rel": 0.25, "fresh": 0.1, "kind": 0.05}
    assert r["score"]["total"] == pytest.approx(0.5)
    assert r["score"]["threshold"] == 0.45
    assert "component_max" not in r["score"]
    # 선별 오류 행(passed=false)이 뒤에 있어도 마지막 성공 선별 행을 쓴다.
    assert r["screening"] == {
        "relevance": 0.83,
        "kind": "technique",
        "topics": ["mcp-tooling", "python-backend"],
        "reason": "구체 기법",
    }
    assert r["judgment"] == {
        "importance": 4,
        "worth_notifying": True,
        "similar_feedback": [{"alert_id": "17220", "feedback": "not_useful", "title": "옛 사례"}],
    }
    assert r["trust_note_source"] == "테스트 소스"

    # cluster_dup 행만 있는 항목 — 전달 아님, routing cluster_dup, 선별·점수·판정 전
    assert (e["delivered_at"], e["delivery_mode"]) == (None, None)
    assert e["rationale"] == {
        "score": None,
        "routing": "cluster_dup",
        "screening": None,
        "judgment": None,
        "trust_note_source": "테스트 소스",
    }
    # stale 탈락 — 점수 결정은 있지만 breakdown 이 없어 score 는 null
    assert j["rationale"]["routing"] == "dropped" and j["rationale"]["score"] is None
    assert cx["rationale"]["routing"] == "explore_slot"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


async def test_restore_decision_routes_as_restored(world: World):
    ids = world.items
    async with SessionLocal() as s, s.begin():
        s.add_all(
            [
                Decision(
                    item_id=ids["d"], stage="user", passed=True, details={"user_id": world.me}
                ),
                Decision(
                    item_id=ids["h"], stage="user", passed=True, details={"user_id": world.other}
                ),
            ]
        )
    async with _client(world.me) as c:
        d = (await c.get(f"/api/v1/alerts/{ids['d']}", headers=AUTH)).json()
        h = (await c.get(f"/api/v1/alerts/{ids['h']}", headers=AUTH)).json()
    assert d["rationale"]["routing"] == "restored"
    assert h["rationale"]["routing"] == "passed"  # 다른 사용자의 복원


async def test_app_feedback_wins_over_reaction_poll(world: World):
    """앱 판정·해제는 리액션 폴링이 바꾸지 못한다. 디스코드에서만 준 판정은 계속 갱신된다."""
    ids = world.items
    async with SessionLocal() as s, s.begin():
        # 리액션 폴링은 DEFAULT_USER_ID 로 돈다. 이 테스트의 항목에만 판정을 단다.
        s.add_all(
            [
                _note(DEFAULT_USER_ID, ids["i"], "push", world.t0, message_id="m-feed-app"),
                _note(DEFAULT_USER_ID, ids["j"], "push", world.t0, message_id="m-feed-dc"),
            ]
        )

    async def verdict_of(item_id: int) -> tuple[str, str] | None:
        async with SessionLocal() as s:
            row = (
                await s.execute(
                    select(Feedback.verdict, Feedback.source).where(
                        Feedback.user_id == DEFAULT_USER_ID, Feedback.item_id == item_id
                    )
                )
            ).first()
        return (row[0], row[1]) if row else None

    async def poll(verdicts: dict[str, str]) -> int:
        async with SessionLocal() as s, s.begin():
            return await sync_feedback(s, verdicts)

    async with _client(DEFAULT_USER_ID) as c:
        put = await c.put(
            f"/api/v1/alerts/{ids['i']}/feedback", json={"verdict": "useful"}, headers=AUTH
        )
        assert put.status_code == 200
        assert put.json()["feedback"] == "useful" and put.json()["alert_id"] == str(ids["i"])
        put = await c.put(
            f"/api/v1/alerts/{ids['i']}/feedback", json={"verdict": "not_useful"}, headers=AUTH
        )
        assert put.json()["feedback"] == "not_useful"
        assert await verdict_of(ids["i"]) == ("useless", "app")

        assert await poll({"m-feed-app": "useful"}) == 0
        assert await verdict_of(ids["i"]) == ("useless", "app")

        res = await c.delete(f"/api/v1/alerts/{ids['i']}/feedback", headers=AUTH)
        assert res.status_code == 204
        detail = (await c.get(f"/api/v1/alerts/{ids['i']}", headers=AUTH)).json()
        assert detail["feedback"] is None
        assert await poll({"m-feed-app": "useful"}) == 0
        assert await verdict_of(ids["i"]) == ("cleared", "app")

        # 판정이 없던 항목의 해제도 204, 행은 생기지 않는다.
        assert (
            await c.delete(f"/api/v1/alerts/{ids['j']}/feedback", headers=AUTH)
        ).status_code == 204
        assert await verdict_of(ids["j"]) is None

    # 디스코드에서만 준 판정은 폴링이 계속 바꾼다.
    assert await poll({"m-feed-dc": "useful"}) == 1
    assert await poll({"m-feed-dc": "useless"}) == 1
    assert await verdict_of(ids["j"]) == ("useless", "discord")


async def test_recent_feedback_today_is_seoul_calendar_day(world: World):
    ids = world.items
    today = today_start(TZ, datetime.now(UTC))
    async with SessionLocal() as s, s.begin():
        await s.execute(delete(Feedback).where(Feedback.user_id == world.me))
        s.add_all(
            [
                Feedback(
                    user_id=world.me,
                    item_id=ids["a"],
                    verdict="useful",
                    created_at=today + timedelta(minutes=1),
                ),
                # 서울 자정 1분 전 — UTC 로는 같은 날이어도 어제다.
                Feedback(
                    user_id=world.me,
                    item_id=ids["j"],
                    verdict="useless",
                    created_at=today - timedelta(minutes=1),
                ),
                Feedback(
                    user_id=world.me,
                    item_id=ids["c"],
                    verdict="cleared",
                    source="app",
                    created_at=today + timedelta(minutes=2),
                ),
                Feedback(
                    user_id=world.other,
                    item_id=ids["d"],
                    verdict="useful",
                    created_at=today + timedelta(minutes=3),
                ),
            ]
        )
    async with SessionLocal() as s:
        recent = await recent_feedback(s, world.me, limit=5, today=today)
    assert recent.today_count == 1
    assert [(e.alert_id, e.feedback.value, e.title) for e in recent.items] == [
        (str(ids["a"]), "useful", "발송 A"),
        (str(ids["j"]), "not_useful", "원문 j"),
    ]

    async with _client(world.me) as c:
        body = (await c.get("/api/v1/feedback/recent", params={"limit": 1}, headers=AUTH)).json()
    assert body["today_count"] == 1 and [e["alert_id"] for e in body["items"]] == [str(ids["a"])]


async def test_today_stats_counts_distinct_pushed_items(world: World):
    async with _client(world.me) as c:
        body = (await c.get("/api/v1/stats/today", headers=AUTH)).json()
    # a(두 채널)·h. 오류 행 f·다른 사용자 g 는 세지 않는다.
    assert body["push_sent_today"] == 2
    assert body["timezone"] == TZ and body["window_hours"] == 24
    assert body["date"] == today_start(TZ, datetime.now(UTC)).date().isoformat()
    assert body["daily_push_cap"] == 15
    assert body["collected_count"] >= len(world.items)


async def test_filtered_total_definition(world: World):
    """창을 먼 미래로 잡아 다른 데이터와 섞이지 않게 한다."""
    since = datetime.now(UTC) + timedelta(days=400)
    inside, outside = since + timedelta(hours=1), since - timedelta(hours=1)
    async with SessionLocal() as s, s.begin():
        src = world.src
        xs = {k: _item(src, f"flt-{k}") for k in "1234567"}
        for k in "137":
            xs[k].status = "DROPPED"
        xs["2"].status = "FILTERED_OUT"
        for k in "456":
            xs[k].status = "SENT"
        s.add_all(xs.values())
        await s.flush()
        x = {k: it.id for k, it in xs.items()}
        world.items |= {f"flt-{k}": v for k, v in x.items()}
        s.add_all(
            [
                Decision(item_id=x["1"], stage="score", passed=False, created_at=inside),
                Decision(item_id=x["2"], stage="rule", passed=False, created_at=outside),
                # 복원 결정은 "마지막 탈락 결정" 이 아니다.
                Decision(item_id=x["3"], stage="rule", passed=False, created_at=outside),
                Decision(item_id=x["3"], stage="user", passed=True, created_at=inside),
                _note(world.me, x["4"], "cluster_dup", inside),
                # 복원으로 피드 행이 붙은 cluster_dup 항목은 cluster_dup 행뿐이 아니다.
                _note(world.me, x["5"], "cluster_dup", inside),
                _note(world.me, x["5"], "feed", inside, channel="app"),
                _note(world.other, x["6"], "cluster_dup", inside),
                Decision(item_id=x["7"], stage="triage", passed=False, created_at=inside),
                Decision(item_id=x["7"], stage="triage", passed=False, created_at=inside),
            ]
        )
    async with SessionLocal() as s:
        assert await filtered_total(s, world.me, since) == 3  # 1, 4, 7
        assert await filtered_total(s, world.other, since) == 3  # 1, 6, 7
