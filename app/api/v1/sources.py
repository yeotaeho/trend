# 화면 06 수집 소스 — GET /sources (Stat·소스 목록·미착수), PATCH /sources/{id} on/off

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api.v1.deps import Session, UserId
from app.api.v1.errors import ApiError
from app.api.v1.queries import sources as queries
from app.api.v1.schemas import sources as schemas
from app.api.v1.settings import save_or_422
from app.config import get_app_config, get_source_configs, merge_overlay
from app.db import budget, prefs
from app.db.models import Source

router = APIRouter(prefix="/sources")

COLLECTED_WINDOW_HOURS = 24


def source_group(source_type: str, config: dict[str, Any]) -> schemas.SourceGroup:
    """arXiv RSS 는 블로그가 아니라 논문 묶음이다."""
    if source_type == "rss" and config.get("family") != "arxiv":
        return "blog_rss"
    if source_type == "hackernews":
        return "community"
    return "paper_release_video"


def to_view(row: Source) -> schemas.Source:
    config = row.config or {}
    return schemas.Source(
        id=row.name,
        display_name=config.get("display_name") or row.name,
        type=row.type,
        group=source_group(row.type, config),
        enabled=row.enabled,
        poll_interval_min=row.poll_interval_sec // 60,
        trust=row.trust_adjusted if row.trust_adjusted is not None else row.trust_score,
        trust_base=row.trust_score,
        trust_calibrated=row.trust_adjusted,
        consecutive_failures=row.fail_count,
        error_hint=config.get("error_hint"),
        last_error=row.last_error,
        last_polled_at=row.last_polled_at,
        repo_count=len(config.get("repos", [])) if row.type == "github_release" else None,
    )


def _budget_use(usage: budget.BudgetUsage) -> schemas.BudgetUse:
    return schemas.BudgetUse(used=usage.used, cap=usage.cap)


def _yaml_names() -> list[str]:
    """목록은 sources.yaml 에 있는 소스만, YAML 순서로. 빠져서 비활성화된 과거 행은 뺀다."""
    return [cfg.name for cfg in get_source_configs()]


@router.get("")
async def list_sources(session: Session) -> schemas.SourceList:
    names = _yaml_names()
    rows = await queries.sources_by_name(session, names)
    sources = [to_view(rows[name]) for name in names if name in rows]
    usage = await budget.usage_today(session)
    return schemas.SourceList(
        stats=schemas.SourceStats(
            enabled_count=sum(s.enabled for s in sources),
            total=len(sources),
            window_hours=COLLECTED_WINDOW_HOURS,
            items_collected=await queries.items_collected(session, COLLECTED_WINDOW_HOURS),
            llm_budget=schemas.LlmBudget(
                triage=_budget_use(usage["triage"]),
                judge=_budget_use(usage["judge"]),
                explore=_budget_use(usage["explore"]),
            ),
        ),
        sources=sources,
        planned_sources=get_app_config().planned_sources,
    )


@router.patch("/{source_id}")
async def patch_source(
    source_id: str, body: schemas.SourcePatch, session: Session, user_id: UserId
) -> schemas.Source:
    """sources.enabled 와 user_prefs.data.sources 를 같이 쓴다. 재기동해도 유지된다."""
    row = None
    if source_id in _yaml_names():
        row = (await queries.sources_by_name(session, [source_id])).get(source_id)
    if row is None:
        raise ApiError(404, "not_found", "소스를 찾을 수 없습니다.", {"source_id": source_id})
    # 설정 잠금을 먼저 잡는다. 행을 먼저 고치면 자동 flush 로 소스 행을 잠근 채 기다린다.
    data = await prefs.prefs_for_update(session, user_id)
    row.enabled = body.enabled
    data = merge_overlay(data, {"sources": {source_id: {"enabled": body.enabled}}})
    await save_or_422(session, user_id, data)
    return to_view(row)
