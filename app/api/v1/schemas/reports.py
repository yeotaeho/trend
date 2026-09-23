# 화면 08 주간 리포트 응답 모델 — 목록 한 줄, 상세의 표 묶음

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.api.v1.schemas.common import UtcDateTime

# 셀 값. bool 은 깔때기의 passed 열이다.
Cell = str | bool | int | float | None


class ReportRef(BaseModel):
    """프로필 카드가 가리키는 리포트."""

    id: str
    title: str
    subtitle: str
    period_start: date
    period_end: date


class ReportSummary(ReportRef):
    created_at: UtcDateTime


class ReportSection(BaseModel):
    key: str
    title: str
    columns: list[str]
    rows: list[list[Cell]]


class Report(ReportSummary):
    sections: list[ReportSection]
