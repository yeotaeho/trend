# 주간 튜닝 리포트 — app/jobs/report.py 의 표를 출력만 한다. --apply 면 신뢰도 기록

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.db.session import engine, session_scope
from app.jobs.report import Section, build_sections, trust_adjustments


def table(s: Section) -> None:
    print(f"\n## {s['title']}")
    if not s["rows"]:
        print("(없음)")
        return
    print(" | ".join(s["columns"]))
    for r in s["rows"]:
        print(" | ".join(str(v) for v in r))


async def main(days: int, apply: bool) -> None:
    applied: list[tuple[str, float]] = []
    try:
        async with session_scope() as session:
            until = datetime.now(UTC)
            print(f"# 최근 {days}일 발송 코호트 (피드백은 도착 시점 무관)")
            for s in (await build_sections(session, until - timedelta(days=days), until)).values():
                table(s)
            if apply:
                for t in await trust_adjustments(session, until):
                    await session.execute(
                        text("UPDATE sources SET trust_adjusted = :v WHERE id = :id"),
                        {"v": t.adjusted, "id": t.source_id},
                    )
                    applied.append((t.name, t.adjusted))
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
