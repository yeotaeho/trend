# 설정 모델 테스트 — 실제 YAML 세 파일 검증, 범위 밖 값 거부, 모든 설정 키의 주인 메타, 빈 정책 문장
from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo

from app.config import CONFIG_DIR, AppConfig, Rules, SourceConfig, _read_yaml


def _rules_yaml() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "rules.yaml")


def test_real_config_files_pass_validation():
    Rules.model_validate(_rules_yaml())
    AppConfig.model_validate(_read_yaml(CONFIG_DIR / "app.yaml"))
    for source in _read_yaml(CONFIG_DIR / "sources.yaml")["sources"]:
        SourceConfig.model_validate(source)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("notify", "timezone"), "KST"),
        (("scoring", "threshold"), 5),
        (("triage", "batch_size"), 0),
        (("notify", "quiet_start_hour"), 99),
        (("notify", "daily_push_cap"), 51),
        (("dedupe", "related_threshold"), 0.99),  # 중복 임계값(0.96)보다 크면 안 된다
        (("scoring", "kind_weights"), {"promo": -0.9}),
        (("scoring", "kind_weights"), {"technique": 0.1}),  # 감점 전용(#32)
        (("policy", "focus_stack"), [f"k{i}" for i in range(51)]),
        (("notify", "resurface_after_days"), 31),
        (("scoring", "explore_band"), 0),
        (("budget", "judge_daily_cap"), -1),
    ],
)
def test_out_of_range_values_are_rejected(path: tuple[str, str], value: Any):
    data = copy.deepcopy(_rules_yaml())
    section, key = path
    data[section][key] = value
    with pytest.raises(ValidationError):
        Rules.model_validate(data)


@pytest.mark.parametrize(
    "fields", [{"poll_interval_sec": 60}, {"trust_score": 1.5}, {"trust_score": -0.1}]
)
def test_source_out_of_range_is_rejected(fields: dict[str, Any]):
    with pytest.raises(ValidationError):
        SourceConfig.model_validate({"name": "rss:x", "type": "rss", **fields})


def _leaves(model: type[BaseModel], prefix: str = "") -> Iterator[tuple[str, FieldInfo]]:
    for name, info in model.model_fields.items():
        annotation = info.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            yield from _leaves(annotation, f"{prefix}{name}.")
        else:
            yield f"{prefix}{name}", info


@pytest.mark.parametrize("model", [Rules, AppConfig, SourceConfig])
def test_every_setting_has_an_owner(model: type[BaseModel]):
    """키마다 주인을 하나 정한다(에픽 #30). 새 키를 더하면 주인부터 정하게 한다."""
    for key, info in _leaves(model):
        meta = info.json_schema_extra
        assert isinstance(meta, dict), key
        assert meta.get("owner") in {"app", "yaml"}, key
        assert meta.get("apply") in {"next_job", "deploy"}, key
        assert meta.get("scope") in {"user", "global"}, key
        assert info.title, key  # GET /settings 의 label


def test_real_policy_sentences_are_not_empty():
    # YAML 에서 빠지면 빈 문자열 기본값으로 선별·판정이 조용히 돈다.
    policy = Rules.model_validate(_rules_yaml()).policy
    assert policy.interests.strip()
    assert policy.not_interested.strip()
