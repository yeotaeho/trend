# 주간 튜닝 리포트 — 깔때기·소스별 정밀도·강도·점수 구간·선별 보정·탈락 사유. --apply 면 신뢰도 기록

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from app.db.session import engine, session_scope
from app.pipeline.trust import adjust_trust, band_table, precision

TRUST_DAYS = 30

# 발송 코호트 기준이다. "최근 N 일에 발송된 항목" 에 붙은 피드백은 언제 도착했든 다 센다.
# 늦게 온 라벨을 보려면 --days 를 늘린다. 신뢰도 보정(C-2)만 별도로 최근 30일 라벨을 쓴다.

# 선별 행의 reason 은 항목마다 다른 자유 문장이라 묶음 키에서 뺀다. 표본은 LOW_RELEVANCE_SAMPLES.
FUNNEL = text(
    """
    SELECT d.stage, d.passed,
           CASE WHEN d.stage = 'triage' THEN NULL ELSE d.details->>'reason' END AS reason,
           count(*) AS n
    FROM decisions d
    WHERE d.created_at >= now() - make_interval(days => :days)
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
    WHERE NOT d.passed AND d.created_at >= now() - make_interval(days => :days)
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
         AND n.sent_at >= now() - make_interval(days => :days)
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
    WHERE n.error IS NULL AND n.sent_at >= now() - make_interval(days => :days)
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
      AND n.sent_at >= now() - make_interval(days => :days)
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
      AND t.created_at >= now() - make_interval(days => :days)
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
      AND d.created_at >= now() - make_interval(days => :days)
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
         AND f.created_at >= now() - make_interval(days => :days)
    WHERE s.enabled
    GROUP BY 1, 2, 3 ORDER BY 2
    """
)


def table(title: str, rows: Sequence[Any], header: Sequence[str] | None = None) -> None:
    print(f"\n## {title}")
    if not rows:
        print("(없음)")
        return
    keys = list(header) if header else list(rows[0]._mapping.keys())
    print(" | ".join(keys))
    for r in rows:
        values = r if header else r._mapping.values()
        print(" | ".join(str(v) for v in values))


async def main(days: int, apply: bool) -> None:
    applied: list[tuple[str, float]] = []
    try:
        async with session_scope() as session:
            p = {"days": days}
            print(f"# 최근 {days}일 발송 코호트 (피드백은 도착 시점 무관)")
            table("관문별 깔때기", (await session.execute(FUNNEL, p)).all())
            table("탈락 사유 상위 10", (await session.execute(DROP_REASONS, p)).all())
            sources = (await session.execute(BY_SOURCE, p)).all()
            table(
                "소스별 발송·👍·👎·정밀도",
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
                header=["source", "trust", "adjusted", "sent", "useful", "useless", "precision"],
            )
            table("importance 별 발송·👍·👎", (await session.execute(BY_IMPORTANCE, p)).all())
            table(
                "점수 구간별 발송·👍·👎·정밀도 (탐색 포함)",
                band_table(
                    (r.score, r.verdict) for r in (await session.execute(BY_SCORE_ROWS, p)).all()
                ),
                header=["band", "sent", "useful", "useless", "precision"],
            )
            table("선별 relevance 구간 vs 판정", (await session.execute(TRIAGE_VS_JUDGE, p)).all())
            table(
                "저관련도 선별 이유 표본 10",
                (await session.execute(LOW_RELEVANCE_SAMPLES, p)).all(),
            )

            labels = (await session.execute(TRUST_LABELS, {"days": TRUST_DAYS})).all()
            print(f"\n## 신뢰도 보정 (최근 {TRUST_DAYS}일 라벨, 활성 소스)")
            print("source | base | useful | useless | adjusted")
            for r in labels:
                adjusted = adjust_trust(r.trust_score, r.useful, r.useless)
                print(f"{r.name} | {r.trust_score} | {r.useful} | {r.useless} | {adjusted}")
                if apply:
                    await session.execute(
                        text("UPDATE sources SET trust_adjusted = :v WHERE id = :id"),
                        {"v": adjusted, "id": r.id},
                    )
                    applied.append((r.name, adjusted))
        # session_scope 가 커밋한 뒤에만 반영됐다고 말한다.
        if apply:
            print(f"\n(--apply: {len(applied)}개 소스의 trust_adjusted 를 커밋함)")
        else:
            print("\n(드라이런. --apply 로 sources.trust_adjusted 에 씀)")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="주간 튜닝 리포트")
    parser.add_argument("--days", type=int, default=7, help="발송 코호트 기간 (기본 7일)")
    parser.add_argument("--apply", action="store_true", help="신뢰도 보정값을 DB 에 쓴다")
    args = parser.parse_args()
    asyncio.run(main(args.days, args.apply))
