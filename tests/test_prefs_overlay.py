# 설정 덮어쓰기 병합 테스트 — 목록 교체·dict 병합, 알 수 없는 키·taxonomy 거부, 틀린 섹션 무시

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from structlog.testing import capture_logs

from app.config import (
    CONFIG_DIR,
    PolicyConfig,
    _read_yaml,
    get_rules,
    merge_overlay,
    rules_with_overlay,
    sanitize_overlay,
    set_prefs_overlay,
    validate_overlay,
    yaml_rules,
)
from app.schemas import Kind


def _yaml() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "rules.yaml")


def test_merge_replaces_lists_and_recurses_into_dicts():
    base = {"policy": {"focus_stack": ["a", "b"], "interests": "x"}, "n": 1}
    overlay = {"policy": {"focus_stack": ["c"]}}

    merged = merge_overlay(base, overlay)

    assert merged == {"policy": {"focus_stack": ["c"], "interests": "x"}, "n": 1}
    assert base["policy"]["focus_stack"] == ["a", "b"]  # 입력은 그대로


def test_kind_weights_overlay_keeps_other_yaml_kinds():
    rules = rules_with_overlay(_yaml(), {"scoring": {"kind_weights": {"survey": -0.1}}})

    assert rules.scoring.kind_weights[Kind.SURVEY] == -0.1
    assert rules.scoring.kind_weights[Kind.PROMO] == -0.30


def test_unknown_key_is_rejected_on_save():
    with pytest.raises(ValueError):
        validate_overlay({"notify": {"bogus": 1}})
    with pytest.raises(ValueError, match="알 수 없는 설정 섹션"):
        validate_overlay({"bogus": {}})


def test_invalid_section_is_ignored_with_warning_and_others_apply():
    overlay = {"triage": {"removed_key": 3}, "notify": {"daily_push_cap": 20}}

    with capture_logs() as logs:
        rules = rules_with_overlay(_yaml(), overlay)

    assert rules.triage == yaml_rules().triage
    assert rules.notify.daily_push_cap == 20
    assert [e["section"] for e in logs if e["event"] == "config.prefs_section_ignored"] == [
        "triage"
    ]


def test_taxonomy_cannot_be_overridden():
    overlay = {"policy": {"taxonomy": ["agent"], "interests": "바뀐 문장"}}

    with pytest.raises(ValueError, match="taxonomy"):
        validate_overlay(overlay)
    with capture_logs():
        rules = rules_with_overlay(_yaml(), overlay)
    assert rules.policy.taxonomy == yaml_rules().policy.taxonomy
    assert rules.policy.interests == yaml_rules().policy.interests


def test_sources_key_is_not_a_rules_section():
    rules = validate_overlay({"sources": {"rss:openai": {"enabled": False}}})
    assert rules == yaml_rules()


def test_set_prefs_overlay_swaps_effective_rules():
    set_prefs_overlay({"policy": {"interests": "새 관심사"}, "notify": {"cluster_daily_cap": 0}})

    assert get_rules().policy.interests == "새 관심사"
    assert get_rules().notify.cluster_daily_cap == 0

    set_prefs_overlay({})
    assert get_rules() == yaml_rules()


def test_categories_default_to_taxonomy_and_stay_within_it():
    assert PolicyConfig(taxonomy=["a", "b"]).categories == ["a", "b"]
    assert PolicyConfig(taxonomy=["a", "b"], categories=["b"]).categories == ["b"]
    with pytest.raises(ValueError, match="taxonomy 밖"):
        PolicyConfig(taxonomy=["a"], categories=["z"])


def test_negative_cluster_cap_is_rejected():
    with pytest.raises(ValueError):
        validate_overlay({"notify": {"cluster_daily_cap": -1}})


def test_older_save_does_not_replace_newer_overlay():
    # 커밋 뒤 교체 호출은 순서가 섞일 수 있다. 늦게 온 옛 저장은 버린다.
    newer, older = datetime(2026, 9, 24, 3, tzinfo=UTC), datetime(2026, 9, 24, 2, tzinfo=UTC)
    set_prefs_overlay({"notify": {"daily_push_cap": 30}}, newer)
    set_prefs_overlay({"notify": {"daily_push_cap": 10}}, older)

    assert get_rules().notify.daily_push_cap == 30


def test_sanitize_drops_only_invalid_sections():
    overlay = {
        "notify": {"removed_key": 1},
        "scoring": {"threshold": 0.5},
        "sources": {"rss:a": {"enabled": False}},
    }
    with capture_logs():
        assert sanitize_overlay(overlay) == {
            "scoring": {"threshold": 0.5},
            "sources": {"rss:a": {"enabled": False}},
        }
