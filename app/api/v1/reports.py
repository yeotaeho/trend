# 화면 08 주간 리포트 — GET /reports, GET /reports/{id} (B9)

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.deps import Session, UserId
from app.api.v1.pagination import Paging
from app.api.v1.queries import reports as queries
from app.api.v1.schemas.common import Page
from app.api.v1.schemas.reports import Report, ReportSummary

router = APIRouter(prefix="/reports")


@router.get("")
async def list_reports(session: Session, user_id: UserId, paging: Paging) -> Page[ReportSummary]:
    items, next_cursor = await queries.report_page(session, user_id, paging)
    return Page[ReportSummary](items=items, next_cursor=next_cursor)


@router.get("/{report_id}")
async def get_report(report_id: str, session: Session, user_id: UserId) -> Report:
    return await queries.get_report(session, user_id, report_id)
