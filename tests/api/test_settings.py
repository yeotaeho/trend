# 설정 API 테스트 — 관심사 PUT 즉시 반영·검증, 알림 설정 PATCH 부분 병합·409·클러스터 상한 변환

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import settings as settings_api
from app.api.v1.queries import settings as queries
from app.config import get_rules, yaml_rules
from app.db import prefs
from app.schemas import Kind
from tests.api.conftest import AUTH, PrefsStore

INTERESTS = "/api/v1/settings/interests"
NOTIFICATIONS = "/api/v1/settings/notifications"


def _interests_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "profile": {"self_description": "에이전트를 만드는 개발자.", "not_interested": "채용"},
        "selected_categories": ["llm-model", "agent"],
        "watch_keywords": ["claude", "anthropics/*"],
        "kind_weights": {k.value: 0.0 for k in Kind},
    }
    body.update(changes)
    return body


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """연결 정보. 기본은 디스코드만 연결, FCM·텔레그램 미연결. 기기 2대."""
    settings = SimpleNamespace(
        fcm_project_id="",
        fcm_service_account_file="",
        discord_bot_token="t",
        discord_channel_id="42",
        discord_channel_name="",
        telegram_bot_token="",
        telegram_chat_id="",
    )
    monkeypatch.setattr(settings_api, "get_settings", lambda: settings)

    async def devices(_session: Any, _user_id: int) -> int:
        return 2

    monkeypatch.setattr(queries, "active_device_count", devices)
    return settings


# --- 04 관심사 ---


def test_get_interests_reflects_yaml_before_any_save(client: TestClient, store: PrefsStore):
    body = client.get(INTERESTS, headers=AUTH).json()

    policy = yaml_rules().policy
    assert body["profile"]["self_description"] == policy.interests
    assert body["selected_categories"] == policy.taxonomy
    assert body["watch_keywords"] == policy.focus_stack + policy.focus_repos
    assert list(body["kind_weights"]) == [k.value for k in Kind]
    assert body["kind_weights"]["promo"] == -0.30
    assert body["updated_at"] is None


def test_put_interests_changes_effective_rules_immediately(client: TestClient, store: PrefsStore):
    weights = {k.value: 0.0 for k in Kind} | {"survey": -0.2, "technique": 0.123}
    res = client.put(
        INTERESTS,
        headers=AUTH,
        json=_interests_body(
            watch_keywords=[" Claude ", "claude", "anthropics/*", "MCP"], kind_weights=weights
        ),
    )

    assert res.status_code == 200, res.text
    rules = get_rules()
    assert rules.policy.interests == "에이전트를 만드는 개발자."
    assert rules.policy.categories == ["llm-model", "agent"]
    assert rules.policy.focus_stack == ["Claude", "MCP"]
    assert rules.policy.focus_repos == ["anthropics/*"]
    assert rules.scoring.kind_weights[Kind.SURVEY] == -0.2
    assert rules.scoring.kind_weights[Kind.TECHNIQUE] == 0.12  # 소수 2자리 반올림
    body = res.json()
    assert body["watch_keywords"] == ["Claude", "MCP", "anthropics/*"]
    assert body["updated_at"] == "2026-09-24T02:18:01Z"
    assert "taxonomy" not in store.data["policy"]


def test_missing_kind_keys_keep_current_values(client: TestClient, store: PrefsStore):
    client.put(INTERESTS, headers=AUTH, json=_interests_body(kind_weights={"news": 0.1}))

    weights = {k.value: 0.0 for k in Kind if k not in (Kind.NEWS, Kind.OTHER)}
    res = client.put(INTERESTS, headers=AUTH, json=_interests_body(kind_weights=weights))

    assert res.status_code == 200
    assert res.json()["kind_weights"]["news"] == 0.1  # 앞 저장값
    assert res.json()["kind_weights"]["other"] == 0.0  # YAML 값
    assert get_rules().scoring.kind_weights[Kind.NEWS] == 0.1


@pytest.mark.parametrize(
    "changes",
    [
        {"selected_categories": []},
        {"selected_categories": ["not-a-slug"]},
        {"selected_categories": ["agent", "agent"]},
        {"kind_weights": {"survey": -0.6}},
        {"kind_weights": {"not_a_kind": 0.1}},
        {"watch_keywords": ["   "]},
        {"watch_keywords": ["x" * 51]},
        {"watch_keywords": [f"k{i}" for i in range(51)]},
        {"profile": {"self_description": "", "not_interested": ""}},
        {"updated_at": "2026-09-20T11:00:00Z"},
    ],
)
def test_put_interests_rejects_invalid(client: TestClient, store: PrefsStore, changes):
    res = client.put(INTERESTS, headers=AUTH, json=_interests_body(**changes))

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
    assert store.saves == 0
    assert get_rules() == yaml_rules()


# --- 05 알림 설정 ---


def test_get_notifications_defaults(client: TestClient, store: PrefsStore, env):
    body = client.get(NOTIFICATIONS, headers=AUTH).json()

    assert body == {
        "channels": {
            "fcm": {"enabled": True, "connected": False, "device_count": 2},
            "discord": {
                "enabled": True,
                "connected": True,
                "channel_name": "#42",
                "reaction_sync": True,
            },
            "telegram": {"enabled": False, "connected": False},
        },
        "daily_push_cap": 15,
        "quiet_hours": {"start": "23:00", "end": "08:00", "timezone": "Asia/Seoul"},
        "dedupe_same_issue_daily": True,
        "delivery_by_importance": {"high": "instant", "mid": "quiet", "low": "feed_only"},
        "exploration_slot": {"enabled": True, "daily_limit": 1},
        "updated_at": None,
    }


def test_patch_notifications_merges_partially(client: TestClient, store: PrefsStore, env):
    client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 20})
    client.patch(NOTIFICATIONS, headers=AUTH, json={"quiet_hours": {"start": "00:00"}})
    res = client.patch(
        NOTIFICATIONS,
        headers=AUTH,
        json={
            "delivery_by_importance": {"mid": "feed_only"},
            "exploration_slot": {"enabled": False},
        },
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["daily_push_cap"] == 20
    assert body["quiet_hours"] == {"start": "00:00", "end": "08:00", "timezone": "Asia/Seoul"}
    assert body["delivery_by_importance"] == {
        "high": "instant",
        "mid": "feed_only",
        "low": "feed_only",
    }
    assert body["exploration_slot"] == {"enabled": False, "daily_limit": 1}
    notify = get_rules().notify
    assert (notify.daily_push_cap, notify.quiet_start_hour, notify.quiet_end_hour) == (20, 0, 8)
    assert notify.explore_enabled is False


def test_patch_enables_connected_channel(client: TestClient, store: PrefsStore, env):
    env.telegram_bot_token, env.telegram_chat_id = "tok", "1"

    res = client.patch(
        NOTIFICATIONS, headers=AUTH, json={"channels": {"telegram": {"enabled": True}}}
    )

    assert res.json()["channels"]["telegram"] == {"enabled": True, "connected": True}
    assert get_rules().notify.channels.telegram is True
    assert get_rules().notify.channels.discord is True


def test_enabling_unconnected_channel_is_409(client: TestClient, store: PrefsStore, env):
    res = client.patch(
        NOTIFICATIONS, headers=AUTH, json={"channels": {"telegram": {"enabled": True}}}
    )

    assert res.status_code == 409
    assert res.json()["error"]["code"] == "channel_not_connected"
    assert res.json()["error"]["details"] == {"channel": "telegram"}
    assert store.saves == 0


def test_disabling_unconnected_channel_is_allowed(client: TestClient, store: PrefsStore, env):
    res = client.patch(NOTIFICATIONS, headers=AUTH, json={"channels": {"fcm": {"enabled": False}}})

    assert res.status_code == 200
    assert get_rules().notify.channels.fcm is False


def test_dedupe_toggle_maps_to_cluster_daily_cap(client: TestClient, store: PrefsStore, env):
    off = client.patch(NOTIFICATIONS, headers=AUTH, json={"dedupe_same_issue_daily": False})
    assert off.json()["dedupe_same_issue_daily"] is False
    assert get_rules().notify.cluster_daily_cap == 0

    on = client.patch(NOTIFICATIONS, headers=AUTH, json={"dedupe_same_issue_daily": True})
    assert on.json()["dedupe_same_issue_daily"] is True
    assert get_rules().notify.cluster_daily_cap == yaml_rules().notify.cluster_daily_cap == 1
    assert "cluster_daily_cap" not in store.data["notify"]  # 덮어쓰기를 지워 YAML 값으로


def test_dedupe_on_writes_one_when_yaml_cap_is_zero(
    client: TestClient, store: PrefsStore, env, monkeypatch
):
    zero = yaml_rules().model_copy(deep=True)
    zero.notify.cluster_daily_cap = 0
    monkeypatch.setattr(settings_api, "yaml_rules", lambda: zero)

    client.patch(NOTIFICATIONS, headers=AUTH, json={"dedupe_same_issue_daily": True})

    assert store.data["notify"]["cluster_daily_cap"] == 1


@pytest.mark.parametrize(
    "body",
    [
        {"quiet_hours": {"start": "23:30"}},
        {"quiet_hours": {"end": "24:00"}},
        {"quiet_hours": {"timezone": "UTC"}},
        {"daily_push_cap": 0},
        {"daily_push_cap": 51},
        {"channels": {"discord": {"enabled": True, "connected": True}}},
        {"channels": {"sms": {"enabled": True}}},
        {"exploration_slot": {"enabled": True, "daily_limit": 2}},
        {"delivery_by_importance": {"high": "loud"}},
        {"updated_at": "2026-09-20T11:00:00Z"},
    ],
)
def test_patch_notifications_rejects_invalid(client: TestClient, store: PrefsStore, env, body):
    res = client.patch(NOTIFICATIONS, headers=AUTH, json=body)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
    assert store.saves == 0


def test_stale_stored_section_is_dropped_on_save(client: TestClient, store: PrefsStore, env):
    # 기동 때 무시된 틀린 섹션(옛 키)이 남아 있어도 새 저장은 막히지 않고, 그 섹션은 지워진다.
    store.data = {"notify": {"removed_key": 1}, "policy": {"taxonomy": ["agent"]}}

    res = client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 7})
    assert res.status_code == 200, res.text
    assert store.data == {"notify": {"daily_push_cap": 7}}

    res = client.put(INTERESTS, headers=AUTH, json=_interests_body())
    assert res.status_code == 200, res.text
    assert "taxonomy" not in store.data["policy"]


def test_merge_failure_on_save_is_422(client: TestClient, store: PrefsStore, monkeypatch):
    def reject(_data):
        raise ValueError("합치면 틀린 값")

    monkeypatch.setattr(prefs, "validate_overlay", reject)

    res = client.put(INTERESTS, headers=AUTH, json=_interests_body())

    assert res.status_code == 422
    assert res.json()["error"]["details"] == {"reason": "합치면 틀린 값"}
    assert store.saves == 0


def test_already_enabled_unconnected_channel_can_be_resent(
    client: TestClient, store: PrefsStore, env
):
    # FCM 은 YAML 기본으로 켜져 있고 미연결이다. 409 는 꺼진 채널을 켤 때만.
    body = {"channels": {"fcm": {"enabled": True}, "discord": {"enabled": False}}}

    res = client.patch(NOTIFICATIONS, headers=AUTH, json=body)

    assert res.status_code == 200, res.text
    assert get_rules().notify.channels.discord is False
