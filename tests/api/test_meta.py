# GET /meta 테스트 — taxonomy 12개가 policy.taxonomy 순서·app.yaml 라벨로, kind·한도·UTC 시각

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.api.v1.meta import taxonomy_entries
from app.config import DEFAULT_TAXONOMY, get_app_config, get_rules
from app.schemas import Kind
from tests.api.conftest import AUTH


def test_meta_taxonomy_follows_policy_order_and_labels(client: TestClient):
    res = client.get("/api/v1/meta", headers=AUTH)

    assert res.status_code == 200
    body = res.json()
    taxonomy = body["taxonomy"]
    assert len(taxonomy) == 12
    assert [t["slug"] for t in taxonomy] == get_rules().policy.taxonomy
    assert taxonomy[0] == {"slug": "llm-model", "label": "새 모델·벤치마크"}
    assert taxonomy[-1] == {"slug": "video", "label": "영상 채널"}


def test_meta_static_fields(client: TestClient):
    body = client.get("/api/v1/meta", headers=AUTH).json()

    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", body["server_time"])
    assert body["timezone"] == "Asia/Seoul"
    assert body["kinds"] == [k.value for k in Kind]
    assert body["limits"] == {
        "kind_weight": {"min": -0.5, "max": 0.5, "step": 0.05},
        "daily_push_cap": {"min": 1, "max": 50},
        "watch_keywords_max": 50,
        "folder_name_max": 30,
        "memo_max": 500,
    }
    assert body["resurface_unread_after_days"] == 7


def test_rules_yaml_taxonomy_matches_default():
    # YAML 과 코드 기본값이 같아야 옛 YAML(키 없음)로 기동해도 분류표가 같다.
    assert get_rules().policy.taxonomy == list(DEFAULT_TAXONOMY)


def test_app_yaml_labels_cover_taxonomy():
    labels = get_app_config().taxonomy_labels
    assert set(get_rules().policy.taxonomy) <= set(labels)


def test_missing_label_falls_back_to_slug():
    entries = taxonomy_entries(["agent", "new-slug"], {"agent": "에이전트 패턴"})
    assert [(e.slug, e.label) for e in entries] == [
        ("agent", "에이전트 패턴"),
        ("new-slug", "new-slug"),
    ]
