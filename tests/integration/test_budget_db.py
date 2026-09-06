# 예약 원자성 테스트 — 299건 상태에서 judge·explore 를 동시에 예약하면 하나만 성공한다

import asyncio

import pytest
from sqlalchemy import delete, func, select

from app.db.budget import reserve_call
from app.db.models import LlmCall
from app.db.session import SessionLocal


@pytest.fixture(autouse=True)
async def clean_llm_calls():
    async with SessionLocal() as s, s.begin():
        await s.execute(delete(LlmCall))
    yield
    async with SessionLocal() as s, s.begin():
        await s.execute(delete(LlmCall))


async def test_concurrent_reservations_respect_shared_cap(monkeypatch):
    monkeypatch.setattr("app.db.budget._caps", lambda: {"triage": 60, "judge": 300, "explore": 3})
    async with SessionLocal() as s, s.begin():
        now = (await s.execute(select(func.now()))).scalar_one()
        s.add_all(LlmCall(kind="judge", batch_id=f"seed-{i}", called_at=now) for i in range(299))

    results = await asyncio.gather(reserve_call("judge"), reserve_call("explore"))
    assert sum(r is not None for r in results) == 1

    async with SessionLocal() as s:
        total = (await s.execute(select(func.count()).select_from(LlmCall))).scalar_one()
    assert total == 300


async def test_explore_own_cap(monkeypatch):
    monkeypatch.setattr("app.db.budget._caps", lambda: {"triage": 60, "judge": 300, "explore": 1})
    assert await reserve_call("explore") is not None
    assert await reserve_call("explore") is None
    assert await reserve_call("judge") is not None
