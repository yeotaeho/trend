# GET /meta — 앱이 기동 시 한 번 읽는 마스터 데이터 (taxonomy 라벨·kind·입력 한도)

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.v1.schemas import common
from app.api.v1.schemas.meta import IntRange, Limits, Meta, StepRange, TaxonomyEntry
from app.config import get_app_config, get_rules
from app.log import get_logger
from app.schemas import Kind

router = APIRouter()
log = get_logger(__name__)


def taxonomy_entries(slugs: list[str], labels: dict[str, str]) -> list[TaxonomyEntry]:
    """policy.taxonomy 순서 그대로. 라벨이 없으면 slug 를 라벨로 쓴다."""
    return [TaxonomyEntry(slug=s, label=labels.get(s, s)) for s in slugs]


def warn_missing_taxonomy_labels() -> None:
    """기동 시 한 번. 라벨 누락은 기동을 막지 않는다."""
    labels = get_app_config().taxonomy_labels
    missing = [s for s in get_rules().policy.taxonomy if s not in labels]
    if missing:
        log.warning("api.taxonomy_label_missing", slugs=missing)


@router.get("/meta")
async def get_meta() -> Meta:
    rules = get_rules()
    app_cfg = get_app_config()
    return Meta(
        server_time=datetime.now(UTC),
        timezone=rules.notify.timezone,
        taxonomy=taxonomy_entries(rules.policy.taxonomy, app_cfg.taxonomy_labels),
        kinds=list(Kind),
        limits=Limits(
            kind_weight=StepRange(
                min=common.KIND_WEIGHT_MIN,
                max=common.KIND_WEIGHT_MAX,
                step=common.KIND_WEIGHT_STEP,
            ),
            daily_push_cap=IntRange(min=common.DAILY_PUSH_CAP_MIN, max=common.DAILY_PUSH_CAP_MAX),
            watch_keywords_max=common.WATCH_KEYWORDS_MAX,
            folder_name_max=common.FOLDER_NAME_MAX,
            memo_max=common.MEMO_MAX,
        ),
        resurface_unread_after_days=app_cfg.resurface_unread_after_days,
    )
