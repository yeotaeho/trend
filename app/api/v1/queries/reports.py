# 주간 리포트 조회 — 목록(커서)·상세·최신 한 건. 저장된 sections 를 계약 순서의 표 목록으로 편다

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Row, literal, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import ApiError
from app.api.v1.pagination import PageParams, paginate
from app.api.v1.queries.alerts import INT4_MAX
from app.api.v1.schemas.reports import Report, ReportRef, ReportSection, ReportSummary
from app.db.models import WeeklyReport
from app.jobs.report import SECTION_KEYS

_COLUMNS = (
    WeeklyReport.id,
    WeeklyReport.title,
    WeeklyReport.subtitle,
    WeeklyReport.period_start,
    WeeklyReport.period_end,
    WeeklyReport.created_at,
)
_NEWEST_FIRST = (WeeklyReport.period_start.desc(), WeeklyReport.id.desc())


def report_id(raw: str) -> int:
    """report_id 는 weekly_reports.id 문자열이다. 숫자가 아니면 없는 리포트와 같다."""
    rid = int(raw) if raw.isascii() and raw.isdecimal() else 0
    if not 0 < rid <= INT4_MAX:
        raise ApiError(404, "not_found", "리포트를 찾을 수 없습니다.", {"report_id": raw})
    return rid


def to_ref(row: Row[Any]) -> ReportRef:
    return ReportRef(
        id=str(row.id),
        title=row.title,
        subtitle=row.subtitle,
        period_start=row.period_start,
        period_end=row.period_end,
    )


def to_summary(row: Row[Any]) -> ReportSummary:
    return ReportSummary(**to_ref(row).model_dump(), created_at=row.created_at)


def to_sections(sections: dict[str, Any]) -> list[ReportSection]:
    return [ReportSection(key=k, **sections[k]) for k in SECTION_KEYS if k in sections]


def _after(key: dict[str, Any]) -> tuple[date, int]:
    """목록 커서 = 직전 페이지 마지막 행의 (period_start, id)."""
    try:
        start, rid = date.fromisoformat(key["d"]), int(key["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.") from exc
    if not 0 < rid <= INT4_MAX:
        raise ApiError(400, "bad_request", "커서를 해석할 수 없습니다.")
    return start, rid


async def report_page(
    session: AsyncSession, user_id: int, page: PageParams
) -> tuple[list[ReportSummary], str | None]:
    """기간 시작일 내림차순."""
    stmt = select(*_COLUMNS).where(WeeklyReport.user_id == user_id)
    if page.after is not None:
        start, rid = _after(page.after)
        stmt = stmt.where(
            tuple_(WeeklyReport.period_start, WeeklyReport.id)
            < tuple_(literal(start), literal(rid))
        )
    rows, next_cursor = paginate(
        (await session.execute(stmt.order_by(*_NEWEST_FIRST).limit(page.limit + 1))).all(),
        page.limit,
        lambda r: {"d": r.period_start.isoformat(), "id": r.id},
    )
    return [to_summary(r) for r in rows], next_cursor


async def get_report(session: AsyncSession, user_id: int, raw_id: str) -> Report:
    """다른 사용자의 리포트도 없는 리포트와 같다."""
    stmt = select(*_COLUMNS, WeeklyReport.sections).where(
        WeeklyReport.id == report_id(raw_id), WeeklyReport.user_id == user_id
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        raise ApiError(404, "not_found", "리포트를 찾을 수 없습니다.", {"report_id": raw_id})
    return Report(**to_summary(row).model_dump(), sections=to_sections(row.sections))


async def latest_report(session: AsyncSession, user_id: int) -> ReportRef | None:
    stmt = (
        select(*_COLUMNS).where(WeeklyReport.user_id == user_id).order_by(*_NEWEST_FIRST).limit(1)
    )
    row = (await session.execute(stmt)).one_or_none()
    return to_ref(row) if row else None
