# 앱 fixture 계약 테스트 — mobile/assets/fixtures 의 JSON 을 서버 응답 모델로 검증하고 받은 필드만 되살려 원본과 같은지 본다

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from app.api.v1.schemas.alerts import Alert, AlertDetail, RecentFeedback
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.feed import TodayStats
from app.api.v1.schemas.filtered import DroppedItem, FilteredGroups, FilteredSummary
from app.api.v1.schemas.meta import Meta
from app.api.v1.schemas.profile import Profile
from app.api.v1.schemas.reports import Report, ReportSummary
from app.api.v1.schemas.saved import FolderList, SavedItem
from app.api.v1.schemas.settings import Interests, NotificationSettings
from app.api.v1.schemas.sources import SourceList

FIXTURES = Path(__file__).resolve().parents[2] / "mobile" / "assets" / "fixtures"

# 파일 → 그 화면이 부르는 GET 의 응답 모델. alerts.json 은 07 상세 여러 건을 페이지 모양으로 담는다.
MODELS: dict[str, Any] = {
    "alerts.json": Page[AlertDetail],
    "feed.json": Page[Alert],
    "feedback_recent.json": RecentFeedback,
    "filtered_groups_gate.json": FilteredGroups,
    "filtered_groups_kind.json": FilteredGroups,
    "filtered_groups_source.json": FilteredGroups,
    "filtered_items.json": Page[DroppedItem],
    "filtered_summary.json": FilteredSummary,
    "folders.json": FolderList,
    "meta.json": Meta,
    "profile.json": Profile,
    "report_12.json": Report,
    "reports.json": Page[ReportSummary],
    "saved.json": Page[SavedItem],
    "settings_interests.json": Interests,
    "settings_notifications.json": NotificationSettings,
    "sources.json": SourceList,
    "stats_today.json": TodayStats,
}


def test_every_fixture_has_a_server_model():
    assert {p.name for p in FIXTURES.glob("*.json")} == set(MODELS)


@pytest.mark.parametrize("name", sorted(MODELS))
def test_fixture_round_trips_through_server_model(name: str):
    raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    adapter = TypeAdapter(MODELS[name])
    parsed = adapter.validate_python(raw)
    # 받은 필드만 되살린다. 서버가 모르는 필드는 빠지고, 이름·형식이 다르면 값이 달라져 여기서 걸린다.
    assert adapter.dump_python(parsed, mode="json", by_alias=True, exclude_unset=True) == raw
