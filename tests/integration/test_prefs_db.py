# user_prefs·예산 통합 테스트 — upsert 는 행을 통째로 바꾸고, 오늘 사용량은 어제 호출을 뺀다

from datetime import timedelta

import pytest
from sqlalchemy import delete, func, select

from app.db.budget import usage_today
from app.db.models import LlmCall, UserPrefs
from app.db.prefs import fetch_prefs, upsert_prefs
from app.db.session import SessionLocal
from app.db.users import DEFAULT_USER_ID


@pytest.fixture(autouse=True)
async def clean_tables():
    async def _clean():
        async with SessionLocal() as s, s.begin():
            await s.execute(delete(UserPrefs).where(UserPrefs.user_id == DEFAULT_USER_ID))
            await s.execute(delete(LlmCall))

    await _clean()
    yield
    await _clean()


async def test_upsert_prefs_inserts_then_replaces_whole_data():
    async with SessionLocal() as s, s.begin():
        first = await upsert_prefs(s, DEFAULT_USER_ID, {"notify": {"daily_push_cap": 20}})
    async with SessionLocal() as s, s.begin():
        second = await upsert_prefs(s, DEFAULT_USER_ID, {"sources": {"rss:a": {"enabled": False}}})
    async with SessionLocal() as s:
        row = await fetch_prefs(s, DEFAULT_USER_ID)

    assert row is not None
    assert row.data == {"sources": {"rss:a": {"enabled": False}}}
    assert row.updated_at == second >= first


async def test_usage_today_skips_yesterday(monkeypatch):
    monkeypatch.setattr("app.db.budget._caps", lambda: {"triage": 60, "judge": 300, "explore": 3})
    async with SessionLocal() as s, s.begin():
        now = (await s.execute(select(func.now()))).scalar_one()
        s.add_all(
            [
                LlmCall(kind="triage", batch_id="t1", called_at=now),
                LlmCall(kind="judge", batch_id="j1", called_at=now),
                LlmCall(kind="explore", batch_id="e1", called_at=now),
                LlmCall(kind="triage", batch_id="old", called_at=now - timedelta(days=2)),
            ]
        )

    async with SessionLocal() as s:
        usage = await usage_today(s)

    assert {name: u.used for name, u in usage.items()} == {"triage": 1, "judge": 2, "explore": 1}
