# 피드백 upsert 문장 테스트 — (user_id, item_id) 충돌 시 verdict·source·created_at 덮어쓰기

from sqlalchemy.dialects import postgresql

from app.db.feedback import feedback_upsert_stmt


def test_upsert_conflict_on_user_and_item():
    sql = str(
        feedback_upsert_stmt(1, 7, "useless", "discord").compile(dialect=postgresql.dialect())
    )
    assert "ON CONFLICT (user_id, item_id) DO UPDATE" in sql
    assert "verdict = excluded.verdict" in sql
    assert "created_at = now()" in sql


def test_upsert_records_and_overwrites_source():
    sql = str(
        feedback_upsert_stmt(1, 7, "useful", "telegram").compile(dialect=postgresql.dialect())
    )
    assert "INSERT INTO feedback (user_id, item_id, verdict, source)" in sql
    assert "source = excluded.source" in sql
