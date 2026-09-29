# 찜 API 테스트 — 201→200·폴더 인자, 메모·읽음 값, 폴더 404·409, unfiled 필터, 422 (DB 없이)

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import saved as router
from app.api.v1.errors import ApiError
from app.api.v1.queries.saved import folder_conflict
from app.api.v1.schemas.saved import Folder, FolderList, SavedItem, SavedSort
from tests.api.conftest import AUTH, FakeSession

SAVED = "/api/v1/saved"
FOLDERS = "/api/v1/folders"
ITEM = 42
MY_FOLDER = 7


class Store:
    """쿼리 함수 자리. SQL 의미는 통합 테스트가 본다. 여기는 라우터의 인자·응답 코드만 본다."""

    def __init__(self) -> None:
        self.bookmarks: set[int] = set()
        self.folder_names = {MY_FOLDER: "나중에 읽기"}
        self.calls: list[tuple[str, Any]] = []
        self.page_args: dict[str, Any] = {}

    async def existing_item_id(self, _session: Any, alert_id: str) -> int:
        if alert_id != str(ITEM):
            raise ApiError(404, "not_found", "알림을 찾을 수 없습니다.")
        return ITEM

    async def folder_exists(self, _session: Any, _user_id: int, folder_id: int) -> bool:
        return folder_id in self.folder_names

    async def upsert(
        self, _session: Any, _user_id: int, item_id: int, folder: int | None, *, set_folder: bool
    ) -> bool:
        self.calls.append(("upsert", (folder, set_folder)))
        created = item_id not in self.bookmarks
        self.bookmarks.add(item_id)
        return created

    async def update(
        self, _session: Any, _user_id: int, item_id: int, values: dict[str, Any]
    ) -> bool:
        self.calls.append(("update", values))
        return item_id in self.bookmarks

    async def delete(self, _session: Any, _user_id: int, item_id: int) -> None:
        self.calls.append(("delete", item_id))
        self.bookmarks.discard(item_id)

    async def get_saved(self, _session: Any, _user_id: int, item_id: int) -> SavedItem | None:
        if item_id not in self.bookmarks:
            return None
        return SavedItem(
            alert_id=str(item_id),
            source_name="테스트 소스",
            title="제목",
            url="https://t/42",
            delivered_at=None,
            saved_at=datetime(2026, 9, 24, 3, 0, tzinfo=UTC),
            folder=None,
            memo=None,
            is_read=False,
            read_at=None,
        )

    async def saved_page(self, _session: Any, _user_id: int, folder: Any, **kw: Any) -> Any:
        self.page_args = {"folder": folder, **kw}
        return [], None

    async def create_folder(self, _session: Any, _user_id: int, name: str) -> Folder:
        if name in self.folder_names.values():
            raise folder_conflict(name)
        self.calls.append(("create_folder", name))
        return Folder(id="8", name=name, count=0, unread_count=0, position=1)

    async def rename(self, _session: Any, _user_id: int, folder_id: int, name: str) -> None:
        self.calls.append(("rename", (folder_id, name)))

    async def move(self, _session: Any, _user_id: int, folder_id: int, position: int) -> None:
        self.calls.append(("move", (folder_id, position)))

    async def get_folder(self, _session: Any, _user_id: int, folder_id: int) -> Folder:
        name = self.folder_names[folder_id]
        return Folder(id=str(folder_id), name=name, count=0, unread_count=0, position=0)

    async def delete_folder(self, _session: Any, _user_id: int, folder_id: int) -> None:
        self.calls.append(("delete_folder", folder_id))

    async def folder_list(self, _session: Any, _user_id: int) -> FolderList:
        return FolderList(total_count=0, unread_count=0, unfiled_count=0, folders=[])


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, session: FakeSession) -> Store:
    fake = Store()
    for name, fn in {
        "existing_item_id": fake.existing_item_id,
        "folder_exists": fake.folder_exists,
        "upsert_bookmark": fake.upsert,
        "update_bookmark": fake.update,
        "delete_bookmark": fake.delete,
        "get_saved": fake.get_saved,
        "saved_page": fake.saved_page,
        "create_folder": fake.create_folder,
        "rename_folder": fake.rename,
        "move_folder": fake.move,
        "get_folder": fake.get_folder,
        "delete_folder": fake.delete_folder,
        "folder_list": fake.folder_list,
    }.items():
        monkeypatch.setattr(router, name, fn)
    return fake


# ---------- PUT /saved ----------


def test_put_is_201_then_200(client: TestClient, store: Store):
    first = client.put(f"{SAVED}/{ITEM}", headers=AUTH)
    assert first.status_code == 201
    assert first.json()["alert_id"] == str(ITEM)

    again = client.put(f"{SAVED}/{ITEM}", json={}, headers=AUTH)
    assert again.status_code == 200
    assert again.json() == first.json()
    # 본문이 없거나 {} 면 폴더를 건드리지 않는다.
    assert store.calls == [("upsert", (None, False)), ("upsert", (None, False))]


def test_put_folder_is_forwarded_only_when_sent(client: TestClient, store: Store):
    client.put(f"{SAVED}/{ITEM}", json={"folder_id": str(MY_FOLDER)}, headers=AUTH)
    client.put(f"{SAVED}/{ITEM}", json={"folder_id": None}, headers=AUTH)
    assert store.calls == [("upsert", (MY_FOLDER, True)), ("upsert", (None, True))]


@pytest.mark.parametrize("folder_id", ["999", "abc", "٣", "0", "99999999999"])
def test_put_unknown_folder_is_404(client: TestClient, store: Store, folder_id: str):
    res = client.put(f"{SAVED}/{ITEM}", json={"folder_id": folder_id}, headers=AUTH)
    assert res.status_code == 404
    assert res.json()["error"]["details"] == {"folder_id": folder_id}
    assert store.bookmarks == set()


def test_put_unknown_item_is_404(client: TestClient, store: Store):
    assert client.put(f"{SAVED}/1", headers=AUTH).status_code == 404
    assert store.calls == []


# ---------- PATCH /saved ----------


@pytest.mark.parametrize(
    ("body", "values"),
    [
        ({"memo": ""}, {"memo": None}),
        ({"memo": None}, {"memo": None}),
        ({"memo": "OAuth 확인"}, {"memo": "OAuth 확인"}),
        ({"is_read": True}, {"is_read": True}),
        ({"is_read": False}, {"is_read": False}),
        ({"folder_id": None}, {"folder_id": None}),
        ({"folder_id": str(MY_FOLDER)}, {"folder_id": MY_FOLDER}),
        ({}, {}),
    ],
)
def test_patch_sends_only_given_keys(
    client: TestClient, store: Store, body: dict[str, Any], values: dict[str, Any]
):
    store.bookmarks.add(ITEM)
    res = client.patch(f"{SAVED}/{ITEM}", json=body, headers=AUTH)
    assert res.status_code == 200
    assert store.calls == [("update", values)]


def test_patch_missing_bookmark_is_404(client: TestClient, store: Store):
    res = client.patch(f"{SAVED}/{ITEM}", json={"is_read": True}, headers=AUTH)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "body", [{"memo": "가" * 501}, {"is_read": "maybe"}, {"folder_id": 7}, {"saved_at": "x"}]
)
def test_patch_invalid_body_is_422(client: TestClient, store: Store, body: dict[str, Any]):
    store.bookmarks.add(ITEM)
    assert client.patch(f"{SAVED}/{ITEM}", json=body, headers=AUTH).status_code == 422
    assert store.calls == []


def test_patch_memo_500_chars_is_ok(client: TestClient, store: Store):
    store.bookmarks.add(ITEM)
    res = client.patch(f"{SAVED}/{ITEM}", json={"memo": "가" * 500}, headers=AUTH)
    assert res.status_code == 200


# ---------- DELETE /saved ----------


def test_delete_is_204_even_when_not_saved(client: TestClient, store: Store):
    store.bookmarks.add(ITEM)
    assert client.delete(f"{SAVED}/{ITEM}", headers=AUTH).status_code == 204
    assert client.delete(f"{SAVED}/{ITEM}", headers=AUTH).status_code == 204
    assert store.bookmarks == set()
    assert client.delete(f"{SAVED}/1", headers=AUTH).status_code == 404


# ---------- GET /saved ----------


@pytest.mark.parametrize(
    ("params", "folder"),
    [({}, None), ({"folder_id": "unfiled"}, "unfiled"), ({"folder_id": str(MY_FOLDER)}, 7)],
)
def test_list_folder_filter(client: TestClient, store: Store, params: dict[str, str], folder: Any):
    res = client.get(SAVED, params=params, headers=AUTH)
    assert res.status_code == 200
    assert res.json() == {"items": [], "next_cursor": None}
    assert store.page_args["folder"] == folder
    assert store.page_args["sort"] is SavedSort.SAVED_DESC
    assert store.page_args["unread_only"] is False


def test_list_sort_and_unread_only(client: TestClient, store: Store):
    params = {"sort": "delivered_desc", "unread_only": "true", "limit": "5"}
    assert client.get(SAVED, params=params, headers=AUTH).status_code == 200
    assert store.page_args["sort"] is SavedSort.DELIVERED_DESC
    assert store.page_args["unread_only"] is True
    assert store.page_args["page"].limit == 5


def test_list_bad_query_is_rejected(client: TestClient, store: Store):
    assert client.get(SAVED, params={"folder_id": "999"}, headers=AUTH).status_code == 404
    assert client.get(SAVED, params={"sort": "title"}, headers=AUTH).status_code == 422


# ---------- 폴더 ----------


def test_create_folder_strips_name(client: TestClient, store: Store):
    res = client.post(FOLDERS, json={"name": "  리팩터링 아이디어 "}, headers=AUTH)
    assert res.status_code == 201
    assert res.json()["name"] == "리팩터링 아이디어"
    assert store.calls == [("create_folder", "리팩터링 아이디어")]


def test_create_duplicate_folder_is_409(client: TestClient, store: Store):
    res = client.post(FOLDERS, json={"name": "나중에 읽기"}, headers=AUTH)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize("name", ["", "   ", "가" * 31])
def test_folder_name_length_is_422(client: TestClient, store: Store, name: str):
    assert client.post(FOLDERS, json={"name": name}, headers=AUTH).status_code == 422
    assert (
        client.patch(f"{FOLDERS}/{MY_FOLDER}", json={"name": name}, headers=AUTH).status_code == 422
    )


def test_patch_folder_renames_and_moves(client: TestClient, store: Store):
    res = client.patch(
        f"{FOLDERS}/{MY_FOLDER}", json={"name": " 새 이름", "position": 0}, headers=AUTH
    )
    assert res.status_code == 200
    assert store.calls == [("rename", (MY_FOLDER, "새 이름")), ("move", (MY_FOLDER, 0))]


def test_patch_folder_errors(client: TestClient, store: Store):
    assert client.patch(f"{FOLDERS}/999", json={"position": 0}, headers=AUTH).status_code == 404
    res = client.patch(f"{FOLDERS}/{MY_FOLDER}", json={"position": -1}, headers=AUTH)
    assert res.status_code == 422
    assert store.calls == []


@pytest.mark.parametrize(("folder_id", "deleted"), [("7", [7]), ("999", [999]), ("abc", [])])
def test_delete_folder_is_always_204(
    client: TestClient, store: Store, folder_id: str, deleted: list[int]
):
    assert client.delete(f"{FOLDERS}/{folder_id}", headers=AUTH).status_code == 204
    assert store.calls == [("delete_folder", fid) for fid in deleted]


def test_requires_token(client: TestClient):
    assert client.get(SAVED).status_code == 401
    assert client.get(FOLDERS).status_code == 401
