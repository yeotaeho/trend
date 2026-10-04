# 설정 API 테스트 — 관심사 PUT 즉시 반영·검증, 알림 설정 PATCH 부분 병합·409·클러스터 상한 변환,
# YAML 과 다른 값만 저장, 키 되돌리기, 저장 이력·버전 되돌리기

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api.v1 import settings as settings_api
from app.api.v1.errors import ApiError
from app.api.v1.pagination import encode_cursor
from app.api.v1.queries import settings as queries
from app.config import get_rules, yaml_rules
from app.db import prefs
from app.db.models import SettingsRevision
from app.db.users import DEFAULT_USER_ID
from app.schemas import Kind
from tests.api.conftest import AUTH, FakeSession, PrefsStore

INTERESTS = "/api/v1/settings/interests"
NOTIFICATIONS = "/api/v1/settings/notifications"
OVERRIDES = "/api/v1/settings/overrides"
REVISIONS = "/api/v1/settings/revisions"


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
    weights = {k.value: 0.0 for k in Kind} | {"survey": -0.2, "technique": -0.123}
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
    assert rules.scoring.kind_weights[Kind.TECHNIQUE] == -0.12  # 소수 2자리 반올림
    body = res.json()
    assert body["watch_keywords"] == ["Claude", "MCP", "anthropics/*"]
    assert body["updated_at"] == "2026-09-24T02:18:01Z"
    assert "taxonomy" not in store.data["policy"]
    assert store.data["policy"]["interests"] == "에이전트를 만드는 개발자."


def test_missing_kind_keys_keep_current_values(client: TestClient, store: PrefsStore):
    client.put(INTERESTS, headers=AUTH, json=_interests_body(kind_weights={"news": -0.1}))

    weights = {k.value: 0.0 for k in Kind if k not in (Kind.NEWS, Kind.OTHER)}
    res = client.put(INTERESTS, headers=AUTH, json=_interests_body(kind_weights=weights))

    assert res.status_code == 200
    assert res.json()["kind_weights"]["news"] == -0.1  # 앞 저장값
    assert res.json()["kind_weights"]["other"] == 0.0  # YAML 값
    assert get_rules().scoring.kind_weights[Kind.NEWS] == -0.1


@pytest.mark.parametrize(
    "changes",
    [
        {"selected_categories": []},
        {"selected_categories": ["not-a-slug"]},
        {"selected_categories": ["agent", "agent"]},
        {"kind_weights": {"survey": -0.6}},
        {"kind_weights": {"technique": 0.1}},  # 감점 전용(#32)
        {"kind_weights": {"not_a_kind": -0.1}},
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
                "enabled": False,  # rules.yaml 10-04 부터 끔
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
    discord_before = get_rules().notify.channels.discord

    res = client.patch(
        NOTIFICATIONS, headers=AUTH, json={"channels": {"telegram": {"enabled": True}}}
    )

    assert res.json()["channels"]["telegram"] == {"enabled": True, "connected": True}
    assert get_rules().notify.channels.telegram is True
    # 보낸 채널만 바뀐다. 디스코드는 YAML 값 그대로다.
    assert get_rules().notify.channels.discord is discord_before


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
    assert store.data == {}  # YAML 값과 같아 덮어쓰기가 지워진다


def test_dedupe_on_writes_one_when_yaml_cap_is_zero(
    client: TestClient, store: PrefsStore, env, monkeypatch
):
    zero = yaml_rules().model_copy(deep=True)
    zero.notify.cluster_daily_cap = 0
    monkeypatch.setattr(settings_api, "yaml_rules", lambda: zero)
    monkeypatch.setattr(config, "yaml_rules", lambda: zero)  # 저장 때 비교하는 YAML 값

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


def test_stale_stored_keys_are_dropped_on_save(client: TestClient, store: PrefsStore, env):
    # 기동 때 무시된 옛 키가 남아 있어도 새 저장은 막히지 않고, 그 키만 지워진다.
    store.data = {
        "notify": {"removed_key": 1, "channels": {"fcm": False}},
        "policy": {"taxonomy": ["agent"]},
    }

    res = client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 7})
    assert res.status_code == 200, res.text
    assert store.data == {
        "notify": {"channels": {"fcm": False}, "daily_push_cap": 7},
    }

    res = client.put(INTERESTS, headers=AUTH, json=_interests_body())
    assert res.status_code == 200, res.text
    assert "taxonomy" not in store.data["policy"]
    assert store.data["policy"]["interests"] == "에이전트를 만드는 개발자."


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


def test_channel_check_uses_locked_stored_value(client: TestClient, store: PrefsStore, env):
    # 다른 요청이 방금 끈 미연결 FCM. 프로세스 캐시(get_rules)는 아직 켜짐이어도 저장값으로 본다.
    store.data = {"notify": {"channels": {"fcm": False}}}

    res = client.patch(NOTIFICATIONS, headers=AUTH, json={"channels": {"fcm": {"enabled": True}}})

    assert res.status_code == 409
    assert store.saves == 0


# --- YAML 과 다른 값만 저장 · 키 되돌리기 (에픽 #30) ---


def _interests_from_get(client: TestClient) -> dict[str, Any]:
    body = client.get(INTERESTS, headers=AUTH).json()
    body.pop("updated_at")
    return body


def test_saving_get_values_back_stores_nothing(client: TestClient, store: PrefsStore):
    # YAML 과 같은 값을 덮어쓰기로 남기면 나중에 YAML 을 고쳐도 옛 값이 이긴다.
    res = client.put(INTERESTS, headers=AUTH, json=_interests_from_get(client))

    assert res.status_code == 200, res.text
    assert store.data == {}


def test_changing_one_kind_stores_only_that_key(client: TestClient, store: PrefsStore):
    body = _interests_from_get(client)
    body["kind_weights"]["survey"] = -0.2

    client.put(INTERESTS, headers=AUTH, json=body)

    assert store.data == {"scoring": {"kind_weights": {"survey": -0.2}}}


async def test_saving_yaml_owned_key_is_422(store: PrefsStore, session: FakeSession):
    # 이 키를 보내는 API 는 없다. 저장 함수가 막는다.
    with pytest.raises(ApiError) as exc:
        await settings_api.save_or_422(
            session, DEFAULT_USER_ID, {}, {"scoring": {"threshold": 0.5}}
        )

    assert exc.value.status == 422
    assert "scoring.threshold" in exc.value.details["reason"]
    assert store.saves == 0


def test_delete_override_restores_yaml_value(client: TestClient, store: PrefsStore, env):
    client.patch(
        NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 20, "quiet_hours": {"start": "00:00"}}
    )

    res = client.delete(f"{OVERRIDES}/notify.daily_push_cap", headers=AUTH)

    assert res.status_code == 204, res.text
    body = client.get(NOTIFICATIONS, headers=AUTH).json()
    assert body["daily_push_cap"] == yaml_rules().notify.daily_push_cap
    assert body["quiet_hours"]["start"] == "00:00"  # 다른 키는 그대로
    assert store.data == {"notify": {"quiet_start_hour": 0}}


def test_delete_one_kind_keeps_the_others(client: TestClient, store: PrefsStore):
    body = _interests_from_get(client)
    body["kind_weights"] |= {"survey": -0.2, "promo": -0.1}
    client.put(INTERESTS, headers=AUTH, json=body)

    res = client.delete(f"{OVERRIDES}/scoring.kind_weights.survey", headers=AUTH)

    assert res.status_code == 204, res.text
    assert get_rules().scoring.kind_weights == yaml_rules().scoring.kind_weights | {
        Kind.PROMO: -0.1
    }
    assert store.data == {"scoring": {"kind_weights": {"promo": -0.1}}}


@pytest.mark.parametrize(
    "key", ["scoring.threshold", "policy.taxonomy", "notify", "notify.channels", "bogus"]
)
def test_delete_non_app_key_is_404(client: TestClient, store: PrefsStore, key: str):
    res = client.delete(f"{OVERRIDES}/{key}", headers=AUTH)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"
    assert store.saves == 0


# --- 저장 이력 · 버전 되돌리기 (#34) ---


def _changed_keys(session: FakeSession) -> list[list[str]]:
    return [[c["key"] for c in r.changes] for r in session.revisions()]


def test_each_save_leaves_a_revision_with_only_changed_keys(
    client: TestClient, store: PrefsStore, session: FakeSession, env
):
    client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 20})
    client.patch(NOTIFICATIONS, headers=AUTH, json={"quiet_hours": {"start": "00:00"}})
    client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 25})

    assert _changed_keys(session) == [
        ["notify.daily_push_cap"],
        ["notify.quiet_start_hour"],
        ["notify.daily_push_cap"],
    ]
    last = session.revisions()[-1]
    default = yaml_rules().notify.daily_push_cap
    assert last.changes == [
        {"key": "notify.daily_push_cap", "old": 20, "new": 25, "default": default}
    ]
    assert (last.origin, last.data) == ("app", store.data)  # 저장 뒤 user_prefs.data 전체
    assert last.created_at == store.updated_at


def test_restore_brings_values_back_and_adds_a_revision(
    client: TestClient, store: PrefsStore, session: FakeSession, env
):
    client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 20})
    client.patch(
        NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 30, "quiet_hours": {"start": "00:00"}}
    )
    first = session.revisions()[0]

    res = client.post(f"{REVISIONS}/{first.id}/restore", headers=AUTH)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["dropped"] == []
    assert body["revision"]["origin"] == "restore"
    assert [c["key"] for c in body["revision"]["changes"]] == [
        "notify.daily_push_cap",
        "notify.quiet_start_hour",
    ]
    notify = get_rules().notify
    assert (notify.daily_push_cap, notify.quiet_start_hour) == (
        20,
        yaml_rules().notify.quiet_start_hour,
    )
    assert len(session.revisions()) == 3
    assert store.data == first.data


def test_restore_drops_keys_the_current_model_rejects(
    client: TestClient, store: PrefsStore, session: FakeSession
):
    # 옛 저장에 지금은 YAML 소유인 키가 있었다. 그 키만 빼고 되돌린다.
    data = {"notify": {"daily_push_cap": 20}, "scoring": {"threshold": 0.5}}
    session.add(_revision(7, DEFAULT_USER_ID, data))

    res = client.post(f"{REVISIONS}/7/restore", headers=AUTH)

    assert res.status_code == 200, res.text
    assert res.json()["dropped"] == ["scoring.threshold"]
    assert store.data == {"notify": {"daily_push_cap": 20}}


@pytest.mark.parametrize("revision_id", ["5", "999", "abc", "0"])
def test_restore_unknown_or_others_revision_is_404(
    client: TestClient, store: PrefsStore, session: FakeSession, revision_id: str
):
    session.add(_revision(5, DEFAULT_USER_ID + 1, {"notify": {"daily_push_cap": 20}}))

    res = client.post(f"{REVISIONS}/{revision_id}/restore", headers=AUTH)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"
    assert store.saves == 0


def test_reset_leaves_a_reset_revision(
    client: TestClient, store: PrefsStore, session: FakeSession, env
):
    client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 20})

    client.delete(f"{OVERRIDES}/notify.daily_push_cap", headers=AUTH)

    reset = session.revisions()[-1]
    assert (reset.origin, [c["key"] for c in reset.changes]) == ("reset", ["notify.daily_push_cap"])


def test_list_revisions_maps_rows(
    client: TestClient, store: PrefsStore, session: FakeSession, env, monkeypatch
):
    client.patch(NOTIFICATIONS, headers=AUTH, json={"daily_push_cap": 20})

    async def page(_s: Any, user_id: int, paging: Any) -> tuple[list[Any], str | None]:
        assert (user_id, paging.limit) == (DEFAULT_USER_ID, 20)
        return session.revisions(), None

    monkeypatch.setattr(queries, "revision_page", page)

    body = client.get(REVISIONS, headers=AUTH).json()

    default = yaml_rules().notify.daily_push_cap
    assert body == {
        "items": [
            {
                "id": "1",
                "origin": "app",
                "note": None,
                "changes": [
                    {"key": "notify.daily_push_cap", "old": default, "new": 20, "default": default}
                ],
                "created_at": "2026-09-24T02:18:01Z",
            }
        ],
        "next_cursor": None,
    }


def _revision(rid: int, user_id: int, data: dict[str, Any]) -> SettingsRevision:
    return SettingsRevision(
        id=rid,
        user_id=user_id,
        data=data,
        changes=[],
        origin="app",
        note=None,
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize("key", [{"id": True}, {"id": "3"}, {"id": 0}, {}])
def test_bad_revision_cursor_is_400(client: TestClient, store: PrefsStore, key: dict[str, Any]):
    res = client.get(REVISIONS, headers=AUTH, params={"cursor": encode_cursor(key)})

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "bad_request"
