# 찜 통합 테스트 — 폴더 유니크·삭제 뒤 미분류·카운트, PUT 멱등·메모·읽음, 정렬·커서, 재알림 대상

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from sqlalchemy import delete

from app.api.v1 import deps
from app.db.models import Bookmark, Item, Notification, Source, User
from app.db.session import SessionLocal
from app.jobs.resurface import _claim, _title
from app.main import app

TOKEN = "test-app-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
KEYS = ["a", "b", "c", "d"]


@dataclass
class World:
    me: int
    other: int
    src: int
    items: dict[str, int]
    t0: datetime


@pytest.fixture
async def world(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[World]:
    """a·b·c 는 10·20·30분에 전달, d 는 전달 전(걸러진 항목을 찜함). 찜은 테스트가 만든다."""
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(app_api_token=TOKEN))
    t0 = datetime.now(UTC).replace(microsecond=0) - timedelta(days=30)
    async with SessionLocal() as s, s.begin():
        me, other = User(name="test-saved-me"), User(name="test-saved-other")
        src = Source(name="test:saved", type="rss", config={"display_name": "찜 소스"})
        s.add_all([me, other, src])
        await s.flush()
        items = {
            k: Item(
                source_id=src.id,
                external_id=k,
                url=f"https://t/saved/{k}",
                url_normalized=f"https://t/saved/{k}",
                url_hash=f"saved-db-{k}",
                title=f"원문 {k}",
                published_at=t0,
            )
            for k in KEYS
        }
        s.add_all(items.values())
        await s.flush()
        ids = {k: it.id for k, it in items.items()}
        s.add_all(
            [
                Notification(
                    user_id=me.id,
                    item_id=ids[k],
                    channel="discord",
                    level="push",
                    sent_at=t0 + timedelta(minutes=minute),
                    title=f"발송 {k}",
                )
                for k, minute in (("a", 10), ("b", 20), ("c", 30))
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


def _ok(res: httpx.Response, status: int = 200) -> Any:
    assert res.status_code == status, res.text
    return res.json() if status != 204 else None


async def _keys(c: httpx.AsyncClient, w: World, **params: Any) -> list[str]:
    body = _ok(await c.get("/api/v1/saved", params=params, headers=AUTH))
    by_id = {str(v): k for k, v in w.items.items()}
    return [by_id[s["alert_id"]] for s in body["items"]]


async def test_folders_are_unique_per_user_and_delete_leaves_bookmarks_unfiled(world: World):
    ids = world.items
    async with _client(world.me) as c:
        later = _ok(
            await c.post("/api/v1/folders", json={"name": "나중에 읽기"}, headers=AUTH), 201
        )
        assert later["position"] == 0 and later["count"] == 0
        dup = await c.post("/api/v1/folders", json={"name": " 나중에 읽기 "}, headers=AUTH)
        assert dup.status_code == 409 and dup.json()["error"]["code"] == "conflict"
        apply = _ok(await c.post("/api/v1/folders", json={"name": "적용해보기"}, headers=AUTH), 201)
        assert apply["position"] == 1

        rename = await c.patch(
            f"/api/v1/folders/{apply['id']}", json={"name": "나중에 읽기"}, headers=AUTH
        )
        assert rename.status_code == 409
        moved = _ok(
            await c.patch(f"/api/v1/folders/{apply['id']}", json={"position": 0}, headers=AUTH)
        )
        assert moved["position"] == 0

        for key in ("a", "b"):
            _ok(
                await c.put(
                    f"/api/v1/saved/{ids[key]}", json={"folder_id": later["id"]}, headers=AUTH
                ),
                201,
            )
        _ok(await c.put(f"/api/v1/saved/{ids['c']}", headers=AUTH), 201)
        _ok(await c.patch(f"/api/v1/saved/{ids['b']}", json={"is_read": True}, headers=AUTH))

        chips = _ok(await c.get("/api/v1/folders", headers=AUTH))
        assert (chips["total_count"], chips["unread_count"], chips["unfiled_count"]) == (3, 2, 1)
        assert [
            (f["name"], f["position"], f["count"], f["unread_count"]) for f in chips["folders"]
        ] == [
            ("적용해보기", 0, 0, 0),
            ("나중에 읽기", 1, 2, 1),
        ]
        # 칩 카운트가 목록과 맞는다.
        assert len(await _keys(c, world, folder_id=later["id"])) == 2
        assert await _keys(c, world, folder_id=later["id"], unread_only="true") == ["a"]
        assert await _keys(c, world, folder_id="unfiled") == ["c"]

    async with _client(world.other) as c:
        # 폴더 이름 유니크는 사용자 안에서만이고, 남의 폴더는 없는 폴더다.
        _ok(await c.post("/api/v1/folders", json={"name": "나중에 읽기"}, headers=AUTH), 201)
        assert (
            await c.get("/api/v1/saved", params={"folder_id": later["id"]}, headers=AUTH)
        ).status_code == 404
        put = await c.put(
            f"/api/v1/saved/{ids['a']}", json={"folder_id": later["id"]}, headers=AUTH
        )
        assert put.status_code == 404
        assert await _keys(c, world) == []

    async with _client(world.me) as c:
        _ok(await c.delete(f"/api/v1/folders/{later['id']}", headers=AUTH), 204)
        assert sorted(await _keys(c, world, folder_id="unfiled")) == ["a", "b", "c"]
        chips = _ok(await c.get("/api/v1/folders", headers=AUTH))
        assert (chips["total_count"], chips["unfiled_count"]) == (3, 3)
        assert [f["name"] for f in chips["folders"]] == ["적용해보기"]


async def test_put_is_idempotent_and_patch_sets_memo_and_read(world: World):
    a = world.items["a"]
    async with _client(world.me) as c:
        folder = _ok(await c.post("/api/v1/folders", json={"name": "적용"}, headers=AUTH), 201)

        first = _ok(await c.put(f"/api/v1/saved/{a}", json={}, headers=AUTH), 201)
        assert first["folder"] is None and first["is_read"] is False
        assert first["title"] == "발송 a" and first["source_name"] == "찜 소스"
        assert first["delivered_at"] == (world.t0 + timedelta(minutes=10)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        moved = _ok(
            await c.put(f"/api/v1/saved/{a}", json={"folder_id": folder["id"]}, headers=AUTH)
        )
        assert moved["folder"] == {"id": folder["id"], "name": "적용"}
        assert moved["saved_at"] == first["saved_at"]
        kept = _ok(await c.put(f"/api/v1/saved/{a}", headers=AUTH))
        assert kept["folder"] == moved["folder"]  # 폴더를 안 보내면 그대로

        memo = _ok(await c.patch(f"/api/v1/saved/{a}", json={"memo": "OAuth 확인"}, headers=AUTH))
        assert memo["memo"] == "OAuth 확인"
        cleared = _ok(await c.patch(f"/api/v1/saved/{a}", json={"memo": ""}, headers=AUTH))
        assert cleared["memo"] is None

        read = _ok(await c.patch(f"/api/v1/saved/{a}", json={"is_read": True}, headers=AUTH))
        assert read["is_read"] is True and read["read_at"] is not None
        again = _ok(await c.patch(f"/api/v1/saved/{a}", json={"is_read": True}, headers=AUTH))
        assert again["read_at"] == read["read_at"]  # 처음 읽은 시각을 지킨다
        unread = _ok(await c.patch(f"/api/v1/saved/{a}", json={"is_read": False}, headers=AUTH))
        assert unread["is_read"] is False and unread["read_at"] is None

        unfiled = _ok(await c.patch(f"/api/v1/saved/{a}", json={"folder_id": None}, headers=AUTH))
        assert unfiled["folder"] is None

        _ok(await c.delete(f"/api/v1/saved/{a}", headers=AUTH), 204)
        assert (await c.patch(f"/api/v1/saved/{a}", json={}, headers=AUTH)).status_code == 404

        undelivered = _ok(await c.put(f"/api/v1/saved/{world.items['d']}", headers=AUTH), 201)
        assert undelivered["delivered_at"] is None and undelivered["title"] == "원문 d"


async def test_sorts_unread_only_and_cursor(world: World):
    ids, t0 = world.items, world.t0
    saved_minutes = {"a": 3, "b": 1, "c": 2, "d": 4}
    async with SessionLocal() as s, s.begin():
        s.add_all(
            [
                Bookmark(
                    user_id=world.me,
                    item_id=ids[k],
                    saved_at=t0 + timedelta(hours=1, minutes=m),
                    is_read=k == "b",
                )
                for k, m in saved_minutes.items()
            ]
        )

    expected = {
        "saved_desc": ["d", "a", "c", "b"],
        "saved_asc": ["b", "c", "a", "d"],
        "delivered_desc": ["c", "b", "a", "d"],  # 전달 전 찜은 맨 뒤
    }
    async with _client(world.me) as c:
        assert await _keys(c, world) == expected["saved_desc"]
        for sort, keys in expected.items():
            assert await _keys(c, world, sort=sort) == keys, sort
            assert await _keys(c, world, sort=sort, unread_only="true") == [
                k for k in keys if k != "b"
            ], sort

            paged: list[str] = []
            cursor = None
            while True:
                params: dict[str, Any] = {"sort": sort, "limit": 1}
                if cursor:
                    params["cursor"] = cursor
                body = _ok(await c.get("/api/v1/saved", params=params, headers=AUTH))
                by_id = {str(v): k for k, v in ids.items()}
                paged += [by_id[x["alert_id"]] for x in body["items"]]
                cursor = body["next_cursor"]
                if cursor is None:
                    break
            assert paged == keys, sort

        bad = await c.get("/api/v1/saved", params={"cursor": "e30"}, headers=AUTH)  # "{}"
        assert bad.status_code == 400


async def test_resurface_claims_only_old_unread_unsent_bookmarks_of_the_user(world: World):
    ids = world.items
    now = datetime.now(UTC)
    old, recent = now - timedelta(days=8), now - timedelta(days=3)
    async with SessionLocal() as s, s.begin():
        s.add_all(
            [
                Bookmark(user_id=world.me, item_id=ids["a"], saved_at=old),
                Bookmark(user_id=world.me, item_id=ids["b"], saved_at=old, is_read=True),
                Bookmark(user_id=world.me, item_id=ids["c"], saved_at=recent),
                Bookmark(user_id=world.me, item_id=ids["d"], saved_at=old, resurfaced_at=recent),
                Bookmark(user_id=world.other, item_id=ids["b"], saved_at=old),
            ]
        )

    cutoff = now - timedelta(days=7)
    async with SessionLocal() as s, s.begin():
        claimed = await _claim(s, world.me, cutoff)
        assert claimed is not None
        bookmark, item = claimed
        assert item.id == ids["a"]
        assert await _title(s, world.me, item) == "발송 a"
        bookmark.resurfaced_at = now

    async with SessionLocal() as s, s.begin():
        assert await _claim(s, world.me, cutoff) is None  # 한 번만 간다
        other = await _claim(s, world.other, cutoff)
        assert other is not None and other[1].id == ids["b"]

    # 재알림은 읽음 상태를 바꾸지 않는다.
    async with _client(world.me) as c:
        chips = _ok(await c.get("/api/v1/folders", headers=AUTH))
        assert (chips["total_count"], chips["unread_count"]) == (4, 3)
