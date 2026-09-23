# 화면 08 프로필 집계 — 기간 통계, 카테고리 반응, 학습된 취향(kind 감점·소스 신뢰도), 표시 이름

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.queries import reports
from app.api.v1.queries.alerts import (
    VERDICT_TO_FEEDBACK,
    first_delivery,
    last_triage,
    source_display_name,
    topics_of,
)
from app.api.v1.queries.filtered import kind_feedback
from app.api.v1.schemas.filtered import KindFeedback
from app.api.v1.schemas.profile import (
    CATEGORY_REACTIONS_TOP,
    CategoryReaction,
    KindPenalty,
    Learned,
    PeriodDays,
    Profile,
    ProfileStats,
    ProfileUser,
    SourceTrustChange,
)
from app.config import get_app_config, get_rules, get_settings
from app.db.models import Decision, Feedback, Source, User
from app.notify.base import channel_connected
from app.schemas import Kind, Level, Stage

JUDGED = list(VERDICT_TO_FEEDBACK)


def useful_ratio(useful: int, not_useful: int) -> int | None:
    """useful / 전체 × 100 을 사사오입한 정수. 판정이 없으면 None."""
    total = useful + not_useful
    # round() 는 짝수 쪽으로 붙는다 (12.5 → 12). 정수 연산으로 0.5 를 올린다.
    return (200 * useful + total) // (2 * total) if total else None


def category_reactions(
    verdicts: Sequence[tuple[int, str]], triage: Mapping[int, dict[str, Any]]
) -> list[CategoryReaction]:
    """판정을 그 항목의 마지막 선별 topics 로 펼친다. topics 가 없으면 세지 않는다."""
    useful: Counter[str] = Counter()
    useless: Counter[str] = Counter()
    for item_id, verdict in verdicts:
        for topic in dict.fromkeys(topics_of(triage.get(item_id))):
            (useful if verdict == "useful" else useless)[topic] += 1
    rows = [
        CategoryReaction(
            category=t, useful=useful[t], not_useful=useless[t], total=useful[t] + useless[t]
        )
        for t in useful.keys() | useless.keys()
    ]
    rows.sort(key=lambda r: (-r.total, r.category))
    return rows[:CATEGORY_REACTIONS_TOP]


def kind_penalties(
    weights: Mapping[Kind, float], feedback: Mapping[Kind, KindFeedback]
) -> list[KindPenalty]:
    """감점(가중치 < 0) kind 마다 최근 30일 판정 수. 판정이 없어도 행은 나온다."""
    empty = KindFeedback(not_useful=0, total=0)
    return [
        KindPenalty(
            kind=kind,
            weight=weight,
            not_useful=feedback.get(kind, empty).not_useful,
            total=feedback.get(kind, empty).total,
            active=weight < 0,
        )
        for kind, weight in weights.items()
        if weight < 0
    ]


async def display_name(session: AsyncSession, user_id: int) -> str:
    name: str = (await session.execute(select(User.name).where(User.id == user_id))).scalar_one()
    return name


async def rename(session: AsyncSession, user_id: int, name: str) -> None:
    await session.execute(update(User).where(User.id == user_id).values(name=name))


async def delivery_counts(
    session: AsyncSession, user_id: int, since: datetime
) -> tuple[int, int, int]:
    """기간 안에 처음 전달된 서로 다른 항목 (전체, instant, experiment). 복원 항목도 전달이다."""
    delivery = first_delivery(user_id)
    stmt = select(
        func.count(),
        func.count().filter(delivery.c.level == Level.PUSH.value),
        func.count().filter(delivery.c.level == Level.EXPLORE.value),
    ).where(delivery.c.sent_at >= since)
    total, push, experiment = (await session.execute(stmt)).one()
    return total, push, experiment


async def period_verdicts(
    session: AsyncSession, user_id: int, since: datetime
) -> list[tuple[int, str]]:
    """기간 안에 만들어진 👍/👎 판정 (item_id, verdict). 해제(cleared)는 판정이 아니다."""
    stmt = select(Feedback.item_id, Feedback.verdict).where(
        Feedback.user_id == user_id,
        Feedback.verdict.in_(JUDGED),
        Feedback.created_at >= since,
    )
    return [(r.item_id, r.verdict) for r in (await session.execute(stmt)).all()]


async def restored_count(session: AsyncSession, user_id: int, since: datetime) -> int:
    """기간 안의 복원 결정 수. 복원을 취소하면 결정 행을 지우므로 남은 행이 곧 복원이다."""
    stmt = (
        select(func.count())
        .select_from(Decision)
        .where(
            Decision.stage == Stage.USER.value,
            Decision.passed.is_(True),
            Decision.details.contains({"user_id": user_id}),
            Decision.created_at >= since,
        )
    )
    return (await session.scalar(stmt)) or 0


async def label_count(session: AsyncSession, user_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Feedback)
        .where(Feedback.user_id == user_id, Feedback.verdict.in_(JUDGED))
    )
    return (await session.scalar(stmt)) or 0


async def trust_changes(session: AsyncSession) -> list[SourceTrustChange]:
    """보정값이 있고 기본값과 소수 2자리에서 다른 소스."""
    stmt = (
        select(Source.name, Source.config, Source.trust_score, Source.trust_adjusted)
        .where(Source.trust_adjusted.is_not(None))
        .order_by(Source.name)
    )
    return [
        SourceTrustChange(
            source_id=r.name,
            source_name=source_display_name(r.name, r.config),
            from_=r.trust_score,
            to=r.trust_adjusted,
        )
        for r in (await session.execute(stmt)).all()
        if round(r.trust_adjusted, 2) != round(r.trust_score, 2)
    ]


async def load_profile(
    session: AsyncSession, user_id: int, period: PeriodDays, now: datetime
) -> Profile:
    since = now - timedelta(days=period)
    app_cfg = get_app_config()
    received, push, experiment = await delivery_counts(session, user_id, since)
    verdicts = await period_verdicts(session, user_id, since)
    useful = sum(1 for _, v in verdicts if v == "useful")
    not_useful = len(verdicts) - useful
    triage = await last_triage(session, sorted({item_id for item_id, _ in verdicts}))
    return Profile(
        period_days=period,
        user=ProfileUser(
            display_name=await display_name(session, user_id),
            discord_connected=channel_connected(get_settings())["discord"],
            onboarding_done=app_cfg.onboarding.done,
            onboarding_total=app_cfg.onboarding.total,
        ),
        stats=ProfileStats(
            alerts_received=received,
            push_count=push,
            experiment_count=experiment,
            useful_count=useful,
            not_useful_count=not_useful,
            useful_ratio=useful_ratio(useful, not_useful),
            missed_issues=await restored_count(session, user_id, since),
        ),
        category_reactions=category_reactions(verdicts, triage),
        learned=Learned(
            kind_penalties=kind_penalties(
                get_rules().scoring.kind_weights, await kind_feedback(session, user_id, now)
            ),
            source_trust_changes=await trust_changes(session),
            profile_vector_labels=await label_count(session, user_id),
            personal_model_threshold=app_cfg.personal_model_threshold,
        ),
        weekly_report_latest=await reports.latest_report(session, user_id),
    )
