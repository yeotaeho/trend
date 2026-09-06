# LLM 호출 예산 — 호출 직전에 독립 트랜잭션으로 예약 행을 커밋해 실패한 호출까지 상한에 센다

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text

from app.config import get_rules, get_settings
from app.db.models import LlmCall
from app.db.session import SessionLocal

Kind = Literal["triage", "judge", "explore"]
# 예산 이름 → 그 예산을 쓰는 kind. 탐색 판정은 판정 예산을 같이 쓴다.
BUDGETS: dict[str, tuple[str, ...]] = {"triage": ("triage",), "judge": ("judge", "explore")}
# 예산이 달라도 잠금은 하나. kind 별 키면 judge 와 explore 가 서로를 못 막아 301회가 난다.
LOCK_KEY = 74_110_003


def today_start(tz: str, now: datetime) -> datetime:
    local = now.astimezone(ZoneInfo(tz))
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def budget_for(kind: str) -> tuple[str, tuple[str, ...]]:
    for name, kinds in BUDGETS.items():
        if kind in kinds:
            return name, kinds
    raise ValueError(f"알 수 없는 kind {kind!r}")


def _caps() -> dict[str, int]:
    rules = get_rules()
    return {
        "triage": rules.triage.daily_cap_calls,
        "judge": get_settings().llm_daily_cap,
        "explore": rules.notify.explore_judge_cap,
    }


async def reserve_call(kind: Kind) -> str | None:
    """상한 미만이면 예약 행을 커밋하고 batch_id 를 돌려준다. 상한이면 None.

    배치 트랜잭션과 별개의 세션이다. 잠금 → 집계 → 삽입 → 커밋이 한 트랜잭션이라
    같은 프로세스의 두 잡이 교차해도 상한을 넘지 않는다. 시각은 DB 에서 한 번만 읽어
    "오늘" 범위와 called_at 에 같이 쓴다.
    """
    budget, kinds = budget_for(kind)
    caps = _caps()
    tz = get_rules().notify.timezone
    async with SessionLocal() as session, session.begin():
        await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": LOCK_KEY})
        now = (await session.execute(select(func.now()))).scalar_one()
        start = today_start(tz, now)
        used = (
            await session.execute(
                select(func.count())
                .select_from(LlmCall)
                .where(LlmCall.kind.in_(kinds), LlmCall.called_at >= start)
            )
        ).scalar_one()
        if used >= caps[budget]:
            return None
        if kind != budget:
            own = (
                await session.execute(
                    select(func.count())
                    .select_from(LlmCall)
                    .where(LlmCall.kind == kind, LlmCall.called_at >= start)
                )
            ).scalar_one()
            if own >= caps[kind]:
                return None
        batch_id = str(uuid.uuid4())
        session.add(LlmCall(kind=kind, batch_id=batch_id, called_at=now))
        return batch_id
