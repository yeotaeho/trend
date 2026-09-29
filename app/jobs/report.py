# 주간 리포트 — 깔때기·소스별 정밀도·점수 구간·선별 보정 등 표 여덟 개를 weekly_reports 에 저장

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

from sqlalchemy import TextClause, func, text
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_rules
from app.db.models import WeeklyReport
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.log import get_logger
from app.pipeline.trust import adjust_trust, band_table, precision

TRUST_DAYS = 30
# 표 순서. JSONB 는 키 순서를 지키지 않으므로 읽는 쪽이 이 순서로 다시 늘어놓는다.
SECTION_KEYS = (
    "funnel",
    "drop_reasons",
    "by_source",
    "by_importance",
    "by_score_band",
    "triage_vs_judge",
    "low_relevance_samples",
    "trust_adjust",
)
SUBTITLE = "깔때기 · 소스별 정밀도 · 점수 구간 · 선별 보정"
log = get_logger(__name__)

# 발송 코호트 기준이다. "[since, until) 에 발송된 항목" 에 붙은 피드백은 언제 도착했든 다 센다.
# 늦게 온 라벨을 보려면 기간을 늘린다. 신뢰도 보정(C-2)만 별도로 until 까지 최근 30일 라벨을 쓴다.

# 선별 행의 reason 은 항목마다 다른 자유 문장이라 묶음 키에서 뺀다. 표본은 LOW_RELEVANCE_SAMPLES.
FUNNEL = text(
    """
    SELECT d.stage, d.passed,
           CASE WHEN d.stage = 'triage' THEN NULL ELSE d.details->>'reason' END AS reason,
           count(*) AS n
    FROM decisions d
    WHERE d.created_at >= :since AND d.created_at < :until
    GROUP BY 1, 2, 3 ORDER BY 1, 2, 4 DESC
    """
)
# 탈락 사유 상위 10. reason 이 없는 점수 미달은 'below_threshold', 판정 false 는 'judge_false'.
DROP_REASONS = text(
    """
    SELECT d.stage,
           COALESCE(d.details->>'reason',
                    CASE d.stage WHEN 'score' THEN 'below_threshold'
                                 WHEN 'llm' THEN 'judge_false' END) AS reason,
           count(*) AS n
    FROM decisions d
    WHERE NOT d.passed AND d.created_at >= :since AND d.created_at < :until
    GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10
    """
)
BY_SOURCE = text(
    """
    SELECT s.name, s.trust_score, s.trust_adjusted,
           count(DISTINCT n.item_id) AS sent,
           count(DISTINCT f.item_id) FILTER (WHERE f.verdict = 'useful') AS useful,
           count(DISTINCT f.item_id) FILTER (WHERE f.verdict = 'useless') AS useless
    FROM sources s
    LEFT JOIN items i ON i.source_id = s.id
    LEFT JOIN notifications n ON n.item_id = i.id AND n.error IS NULL
         AND n.sent_at >= :since AND n.sent_at < :until
    LEFT JOIN feedback f ON f.item_id = n.item_id
    GROUP BY 1, 2, 3 ORDER BY sent DESC
    """
)
BY_IMPORTANCE = text(
    """
    SELECT sm.importance,
           count(DISTINCT n.item_id) AS sent,
           count(DISTINCT f.item_id) FILTER (WHERE f.verdict = 'useful') AS useful,
           count(DISTINCT f.item_id) FILTER (WHERE f.verdict = 'useless') AS useless
    FROM notifications n
    JOIN summaries sm ON sm.item_id = n.item_id
    LEFT JOIN feedback f ON f.item_id = n.item_id
    WHERE n.error IS NULL AND n.sent_at >= :since AND n.sent_at < :until
    GROUP BY 1 ORDER BY 1 DESC
    """
)
BY_SCORE_ROWS = text(
    """
    SELECT DISTINCT ON (n.item_id) i.score, f.verdict
    FROM notifications n
    JOIN items i ON i.id = n.item_id
    LEFT JOIN feedback f ON f.item_id = n.item_id
    WHERE n.error IS NULL AND i.score IS NOT NULL
      AND n.sent_at >= :since AND n.sent_at < :until
    ORDER BY n.item_id
    """
)
TRIAGE_VS_JUDGE = text(
    """
    SELECT round((floor((t.details->>'relevance')::float / 0.2) * 0.2)::numeric, 1) AS band,
           count(*) AS triaged,
           count(*) FILTER (WHERE j.passed) AS judged_true,
           count(*) FILTER (WHERE j.id IS NOT NULL AND NOT j.passed) AS judged_false
    FROM decisions t
    LEFT JOIN decisions j ON j.item_id = t.item_id AND j.stage = 'llm'
    WHERE t.stage = 'triage' AND t.passed
      AND t.created_at >= :since AND t.created_at < :until
    GROUP BY 1 ORDER BY 1
    """
)
# 정책 문장을 고칠 근거인 선별 이유 "문장" 표본.
LOW_RELEVANCE_SAMPLES = text(
    """
    SELECT s.name AS source, left(i.title, 60) AS title,
           (d.details->>'relevance')::float AS relevance, d.details->>'reason' AS reason
    FROM decisions d
    JOIN items i ON i.id = d.item_id
    JOIN sources s ON s.id = i.source_id
    WHERE d.stage = 'triage' AND d.passed AND (d.details->>'relevance')::float < 0.3
      AND d.created_at >= :since AND d.created_at < :until
    ORDER BY d.created_at DESC LIMIT 10
    """
)
TRUST_LABELS = text(
    """
    SELECT s.id, s.name, s.trust_score,
           count(f.item_id) FILTER (WHERE f.verdict = 'useful') AS useful,
           count(f.item_id) FILTER (WHERE f.verdict = 'useless') AS useless
    FROM sources s
    LEFT JOIN items i ON i.source_id = s.id
    LEFT JOIN feedback f ON f.item_id = i.id
         AND f.created_at >= :since AND f.created_at < :until
    WHERE s.enabled
    GROUP BY 1, 2, 3 ORDER BY 2
    """
)

Cell = str | bool | int | float | None


class Section(TypedDict):
    title: str
    columns: list[str]
    rows: list[list[Cell]]


@dataclass(frozen=True, slots=True)
class TrustAdjustment:
    source_id: int
    name: str
    base: float
    useful: int
    useless: int
    adjusted: float


def cell(value: Any) -> Cell:
    """JSONB 에 넣을 수 있는 값. round(...)::numeric 은 Decimal 로 온다."""
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def section(title: str, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> Section:
    return {
        "title": title,
        "columns": list(columns),
        "rows": [[cell(v) for v in r] for r in rows],
    }


async def _query(
    session: AsyncSession, title: str, stmt: TextClause, params: dict[str, Any]
) -> Section:
    # 행이 없어도 열 이름은 결과 메타데이터에서 온다.
    result = await session.execute(stmt, params)
    return section(title, list(result.keys()), result.all())


async def trust_adjustments(session: AsyncSession, until: datetime) -> list[TrustAdjustment]:
    """활성 소스마다 until 까지 최근 30일 라벨로 보정한 신뢰도. 저장은 하지 않는다."""
    params = {"since": until - timedelta(days=TRUST_DAYS), "until": until}
    return [
        TrustAdjustment(
            source_id=r.id,
            name=r.name,
            base=r.trust_score,
            useful=r.useful,
            useless=r.useless,
            adjusted=adjust_trust(r.trust_score, r.useful, r.useless),
        )
        for r in (await session.execute(TRUST_LABELS, params)).all()
    ]


async def build_sections(
    session: AsyncSession, since: datetime, until: datetime
) -> dict[str, Section]:
    """[since, until) 발송 코호트의 표 여덟 개. 키 순서가 SECTION_KEYS 다 (계약 4.8)."""
    p = {"since": since, "until": until}
    sources = (await session.execute(BY_SOURCE, p)).all()
    scores = (await session.execute(BY_SCORE_ROWS, p)).all()
    trust = await trust_adjustments(session, until)
    return {
        "funnel": await _query(session, "관문별 깔때기", FUNNEL, p),
        "drop_reasons": await _query(session, "탈락 사유 상위 10", DROP_REASONS, p),
        "by_source": section(
            "소스별 발송·👍·👎·정밀도",
            ["source", "trust", "adjusted", "sent", "useful", "useless", "precision"],
            [
                (
                    r.name,
                    r.trust_score,
                    r.trust_adjusted,
                    r.sent,
                    r.useful,
                    r.useless,
                    precision(r.useful, r.useless),
                )
                for r in sources
            ],
        ),
        "by_importance": await _query(session, "importance 별 발송·👍·👎", BY_IMPORTANCE, p),
        "by_score_band": section(
            "점수 구간별 발송·👍·👎·정밀도 (탐색 포함)",
            ["band", "sent", "useful", "useless", "precision"],
            band_table((r.score, r.verdict) for r in scores),
        ),
        "triage_vs_judge": await _query(session, "선별 relevance 구간 vs 판정", TRIAGE_VS_JUDGE, p),
        "low_relevance_samples": await _query(
            session, "저관련도 선별 이유 표본 10", LOW_RELEVANCE_SAMPLES, p
        ),
        "trust_adjust": section(
            f"신뢰도 보정 (최근 {TRUST_DAYS}일 라벨, 활성 소스)",
            ["source", "base", "useful", "useless", "adjusted"],
            [(t.name, t.base, t.useful, t.useless, t.adjusted) for t in trust],
        ),
    }


def last_week(today: date) -> tuple[date, date]:
    """오늘이 속한 주 바로 앞의 월요일~일요일. 월요일 09:00 에 돌면 지난 7일이다."""
    start = today - timedelta(days=today.weekday() + 7)
    return start, start + timedelta(days=6)


def report_title(period_start: date) -> str:
    """기간 시작일이 월요일 시작 달력의 몇째 줄인가. 9/1 이 화요일인 2026년은 9월 7일 → 2주차."""
    offset = period_start.replace(day=1).weekday()
    return f"{period_start.month}월 {(period_start.day + offset - 1) // 7 + 1}주차 리포트"


def report_upsert_stmt(
    user_id: int, period_start: date, period_end: date, sections: dict[str, Section]
) -> Insert:
    """같은 주를 다시 만들면 덮어쓴다 (uq_weekly_reports_user_period)."""
    values = {
        "period_end": period_end,
        "title": report_title(period_start),
        "subtitle": SUBTITLE,
        "sections": sections,
    }
    stmt = insert(WeeklyReport).values(user_id=user_id, period_start=period_start, **values)
    return stmt.on_conflict_do_update(
        constraint="uq_weekly_reports_user_period",
        set_=values | {"created_at": func.now()},
    )


async def save_report(session: AsyncSession, user_id: int, today: date, tz: str) -> date:
    """지난주 리포트를 만들어 저장하고 기간 시작일을 돌려준다. 기간 경계는 tz 자정이다."""
    start, end = last_week(today)
    zone = ZoneInfo(tz)
    since = datetime.combine(start, time(), tzinfo=zone)
    until = datetime.combine(end + timedelta(days=1), time(), tzinfo=zone)
    sections = await build_sections(session, since, until)
    await session.execute(report_upsert_stmt(user_id, start, end, sections))
    return start


async def run_weekly_report() -> None:
    tz = get_rules().notify.timezone
    today = datetime.now(UTC).astimezone(ZoneInfo(tz)).date()
    async with session_scope() as session:
        start = await save_report(session, DEFAULT_USER_ID, today, tz)
    log.info("report.saved", user_id=DEFAULT_USER_ID, period_start=start.isoformat())
