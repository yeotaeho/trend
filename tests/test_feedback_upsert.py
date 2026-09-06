# 피드백 upsert 문장 테스트 — ON CONFLICT 로 verdict·created_at 을 덮어쓴다

from sqlalchemy.dialects import postgresql

from app.db.feedback import feedback_upsert_stmt


def test_upsert_overwrites_verdict_and_time():
    sql = str(feedback_upsert_stmt(7, "useless").compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT ON CONSTRAINT uq_feedback_item_id DO UPDATE" in sql
    assert "verdict = excluded.verdict" in sql
    assert "created_at = now()" in sql
