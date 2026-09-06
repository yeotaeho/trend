# 임베딩 백필 — NULL 이거나 모델이 바뀐 행을 128건씩 계산한다. 멱등이라 중단 후 재실행 가능

from __future__ import annotations

import asyncio

from sqlalchemy import func, or_, select

from app.config import get_settings
from app.db.models import Item
from app.db.session import engine, session_scope
from app.log import configure_logging
from app.pipeline.embedding import MAX_BATCH, embed_pending


async def main() -> None:
    configure_logging()
    model = get_settings().embedding_model
    pending = or_(Item.embedding.is_(None), Item.embedding_model != model)
    try:
        async with session_scope() as session:
            todo = (
                await session.execute(select(func.count()).select_from(Item).where(pending))
            ).scalar_one()
        print(f"대상 {todo}건 (NULL 또는 모델 {model!r} 불일치). {MAX_BATCH}건씩 호출한다.")
        print("모델 불일치 행이 남아 있는 동안 파이프라인 잡은 스스로 멈춘다.")

        total = 0
        while True:
            async with session_scope() as session:
                done = await embed_pending(session)
            if done == 0:
                break
            total += done
            print(f"진행: {total}/{todo}")

        async with session_scope() as session:
            left = (
                await session.execute(select(func.count()).select_from(Item).where(pending))
            ).scalar_one()
        print(f"완료: {total}건 계산, 남은 대상 {left}건 (0 이 아니면 재실행)")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
