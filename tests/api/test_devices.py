# 기기 등록 API 테스트 — 201→200, 비활성 재등록, 삭제, 검증 422 (DB 없이)

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import devices as router
from app.api.v1.queries.devices import Registered
from tests.api.conftest import AUTH, FakeSession

DEVICES = "/api/v1/devices"
BODY = {"token": "fcm-token-1", "platform": "android", "app_version": "0.1.0"}


class DeviceTable:
    """devices 테이블 대신. register_device·delete_device 의 upsert 의미를 흉내 낸다."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    async def register(
        self, _session: Any, user_id: int, token: str, platform: str, app_version: str | None
    ) -> Registered:
        row = self.rows.get(token)
        created = row is None
        if row is None:
            row = self.rows[token] = {
                "id": len(self.rows) + 1,
                "created_at": datetime(2026, 9, 24, 3, 0, tzinfo=UTC),
            }
        row.update(user_id=user_id, platform=platform, app_version=app_version, disabled_at=None)
        return Registered(row["id"], platform, row["created_at"], created)

    async def delete(self, _session: Any, user_id: int, token: str) -> None:
        if token in self.rows and self.rows[token]["user_id"] == user_id:
            del self.rows[token]


@pytest.fixture
def table(monkeypatch: pytest.MonkeyPatch, session: FakeSession) -> DeviceTable:
    fake = DeviceTable()
    monkeypatch.setattr(router, "register_device", fake.register)
    monkeypatch.setattr(router, "delete_device", fake.delete)
    return fake


def test_register_twice_is_201_then_200(client: TestClient, table: DeviceTable):
    first = client.post(DEVICES, json=BODY, headers=AUTH)
    assert first.status_code == 201
    registered = {"id": "1", "platform": "android", "registered_at": "2026-09-24T03:00:00Z"}
    assert first.json() == registered

    again = client.post(DEVICES, json=BODY, headers=AUTH)
    assert again.status_code == 200
    assert again.json() == first.json()


def test_disabled_device_is_active_again(client: TestClient, table: DeviceTable):
    client.post(DEVICES, json=BODY, headers=AUTH)
    table.rows["fcm-token-1"]["disabled_at"] = datetime.now(UTC)

    assert client.post(DEVICES, json=BODY, headers=AUTH).status_code == 200
    assert table.rows["fcm-token-1"]["disabled_at"] is None


def test_delete_is_204_even_when_missing(client: TestClient, table: DeviceTable):
    client.post(DEVICES, json=BODY, headers=AUTH)
    assert client.delete(f"{DEVICES}/fcm-token-1", headers=AUTH).status_code == 204
    assert table.rows == {}
    assert client.delete(f"{DEVICES}/fcm-token-1", headers=AUTH).status_code == 204


@pytest.mark.parametrize(
    "body",
    [
        {**BODY, "platform": "web"},
        {**BODY, "token": ""},
        {**BODY, "app_version": "x" * 31},
        {**BODY, "extra": 1},
        {"platform": "ios"},
    ],
)
def test_invalid_body_is_422(client: TestClient, table: DeviceTable, body: dict[str, Any]):
    res = client.post(DEVICES, json=body, headers=AUTH)
    assert res.status_code == 422
    assert table.rows == {}


def test_requires_token(client: TestClient):
    assert client.post(DEVICES, json=BODY).status_code == 401
