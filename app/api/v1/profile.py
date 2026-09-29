# 화면 08 내 프로필 — GET·PATCH /profile (B9)

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.v1.deps import Session, UserId
from app.api.v1.queries import profile as queries
from app.api.v1.schemas.profile import PeriodDays, Profile, ProfileIn

router = APIRouter(prefix="/profile")


@router.get("")
async def get_profile(
    session: Session, user_id: UserId, period_days: PeriodDays = PeriodDays.TWO_WEEKS
) -> Profile:
    """period_days 는 7·14·30 만 받는다 (그 밖은 422)."""
    return await queries.load_profile(session, user_id, period_days, datetime.now(UTC))


@router.patch("")
async def patch_profile(body: ProfileIn, session: Session, user_id: UserId) -> Profile:
    """표시 이름을 바꾸고 기본 기간(14일) 프로필을 돌려준다."""
    await queries.rename(session, user_id, body.display_name)
    return await queries.load_profile(session, user_id, PeriodDays.TWO_WEEKS, datetime.now(UTC))
