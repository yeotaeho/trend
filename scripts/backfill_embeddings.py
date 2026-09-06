# 임베딩 백필 — NULL 이거나 모델이 바뀐 행을 128건씩 계산한다. 멱등이라 중단 후 재실행 가능

from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.config import get_settings
from app.db.models import Item
from app.db.session import engine, session_scope
from app.log import configure_logging
from app.pipeline.embedding import MAX_BATCH, embed_pending, needs_embedding

BATCH_GAP_SEC = 20  # 3 RPM 무료 등급 기준. 유료면 0 으로 내려도 된다
RATE_WINDOW_SEC = 60
MAX_FAILURES = 5


async def main() -> None:
    configure_logging()
    model = get_settings().embedding_model
    pending = needs_embedding()
    try:
        async with session_scope() as session:
            todo = (
                await session.execute(select(func.count()).select_from(Item).where(pending))
            ).scalar_one()
        print(f"대상 {todo}건 (NULL 또는 모델 {model!r} 불일치). {MAX_BATCH}건씩 호출한다.")
        print("모델 불일치 행이 남아 있는 동안 파이프라인 잡은 스스로 멈춘다.")

        total = 0
        failures = 0
        while True:
            async with session_scope() as session:
                done = await embed_pending(session)
            if done == 0:
                async with session_scope() as session:
                    remaining = (
                        await session.execute(select(func.count()).select_from(Item).where(pending))
                    ).scalar_one()
                if remaining == 0:
                    break
                # 배치 실패(대개 분 단위 속도 제한). 한 창을 쉬고 다시 간다. 연속 실패면 포기.
                failures += 1
                if failures >= MAX_FAILURES:
                    print(f"연속 {failures}회 실패. 중단한다. 남은 대상 {remaining}건")
                    break
                print(f"배치 실패 {failures}회. {RATE_WINDOW_SEC}초 뒤 재시도 (남은 {remaining}건)")
                await asyncio.sleep(RATE_WINDOW_SEC)
                continue
            failures = 0
            total += done
            print(f"진행: {total}/{todo}")
            # 무료 등급은 분당 요청 수가 작다. 배치 사이를 띄워 429 를 애초에 피한다.
            await asyncio.sleep(BATCH_GAP_SEC)

        async with session_scope() as session:
            left = (
                await session.execute(select(func.count()).select_from(Item).where(pending))
            ).scalar_one()
        print(f"완료: {total}건 계산, 남은 대상 {left}건 (0 이 아니면 재실행)")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
