# 설정 이력 통합 테스트 — 저장마다 이력 한 행·바뀐 키만, 커서 목록, 버전 되돌리기, 전체 설정 조회

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from sqlalchemy import delete, func, select, update

from app.api.v1 import deps
from app.config import get_source_configs, yaml_rules
from app.db.models import SettingsRevision, Source, UserPrefs
from app.db.prefs import last_defaults
from app.db.session import SessionLocal
from app.db.users import DEFAULT_USER_ID
from app.main import app

TOKEN = "test-app-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
SOURCE = "rss:anthropic"


@pytest.fixture(autouse=True)
async def clean(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """기본 사용자의 설정·이력을 비우고, 끝나면 소스 행을 YAML 값으로 돌린다."""
    monkeypatch.setattr(deps, "get_settings", lambda: SimpleNamespace(app_api_token=TOKEN))
    yaml_enabled = next(c.enabled for c in get_source_configs() if c.name == SOURCE)

    async def _clean() -> None:
        async with SessionLocal() as s, s.begin():
            mine = SettingsRevision.user_id == DEFAULT_USER_ID
            await s.execute(delete(SettingsRevision).where(mine))
            await s.execute(delete(UserPrefs).where(UserPrefs.user_id == DEFAULT_USER_ID))
            source = update(Source).where(Source.name == SOURCE)
            await s.execute(source.values(enabled=yaml_enabled))

    await _clean()
    yield
    await _clean()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


def _ok(res: httpx.Response) -> Any:
    assert res.status_code == 200, res.text
    return res.json()


def _keys(page: dict[str, Any]) -> list[list[str]]:
    return [[c["key"] for c in r["changes"]] for r in page["items"]]


async def test_saves_list_and_restore_round_trip():
    yaml = yaml_rules().notify
    async with _client() as c:
        notifications = "/api/v1/settings/notifications"
        _ok(await c.patch(notifications, headers=AUTH, json={"daily_push_cap": 20}))
        _ok(await c.patch(f"/api/v1/sources/{SOURCE}", headers=AUTH, json={"enabled": False}))
        _ok(await c.patch(notifications, headers=AUTH, json={"quiet_hours": {"start": "00:00"}}))

        newest = _ok(await c.get("/api/v1/settings/revisions?limit=2", headers=AUTH))
        rest = _ok(
            await c.get(
                "/api/v1/settings/revisions",
                headers=AUTH,
                params={"limit": 2, "cursor": newest["next_cursor"]},
            )
        )
        assert _keys(newest) == [["notify.quiet_start_hour"], [f"sources.{SOURCE}.enabled"]]
        assert (_keys(rest), rest["next_cursor"]) == ([["notify.daily_push_cap"]], None)

        first = rest["items"][0]["id"]
        restored = _ok(await c.post(f"/api/v1/settings/revisions/{first}/restore", headers=AUTH))
        assert (restored["revision"]["origin"], restored["dropped"]) == ("restore", [])
        assert sorted(ch["key"] for ch in restored["revision"]["changes"]) == [
            "notify.quiet_start_hour",
            f"sources.{SOURCE}.enabled",
        ]

        now = _ok(await c.get(notifications, headers=AUTH))
        assert (now["daily_push_cap"], now["quiet_hours"]["start"]) == (
            20,
            f"{yaml.quiet_start_hour:02d}:00",
        )
        listed = _ok(await c.get("/api/v1/sources", headers=AUTH))["sources"]
        assert {s["id"]: s["enabled"] for s in listed}[SOURCE] is True

        overview = _ok(await c.get("/api/v1/settings", headers=AUTH))
        items = {item["key"]: item for item in overview["items"]}
        assert overview["revision"] == restored["revision"]["id"]
        assert (
            items["notify.daily_push_cap"]["source"],
            items["notify.daily_push_cap"]["value"],
        ) == (
            "app",
            20,
        )
        assert items[f"sources.{SOURCE}.enabled"]["source"] == "default"

    async with SessionLocal() as s:
        row = select(Source.enabled).where(Source.name == SOURCE)
        enabled = (await s.execute(row)).scalar_one()
        count = (
            await s.execute(
                select(func.count())
                .select_from(SettingsRevision)
                .where(SettingsRevision.user_id == DEFAULT_USER_ID)
            )
        ).scalar_one()
        defaults = await last_defaults(s, DEFAULT_USER_ID)
    assert (enabled, count) == (True, 4)
    assert defaults["notify.daily_push_cap"] == yaml.daily_push_cap
