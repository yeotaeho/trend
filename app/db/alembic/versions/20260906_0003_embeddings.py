"""임베딩 컬럼·llm_calls·feedback 유니크·trust_adjusted — 검증 파이프라인 v2

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.types import Vector

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("items", sa.Column("embedding", Vector(1024), nullable=True))
    op.add_column("items", sa.Column("embedding_model", sa.Text(), nullable=True))
    # 제목 trigram 검색은 벡터 검색으로 대체된다. 확장은 다른 용도가 없어도 해가 없으니 둔다.
    op.execute("DROP INDEX IF EXISTS ix_items_title_trgm")

    op.add_column("sources", sa.Column("trust_adjusted", sa.Float(), nullable=True))

    # 피드백은 항목당 1건. 기존 중복은 최신(created_at DESC, id DESC) 1건만 남긴다.
    op.execute(
        """
        DELETE FROM feedback f
        USING (
            SELECT id, row_number() OVER (
                PARTITION BY item_id ORDER BY created_at DESC, id DESC
            ) AS rn
            FROM feedback
        ) ranked
        WHERE f.id = ranked.id AND ranked.rn > 1
        """
    )
    op.create_unique_constraint("uq_feedback_item_id", "feedback", ["item_id"])

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("batch_id", sa.String(36), nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_calls_kind", "llm_calls", ["kind"])
    op.create_index("ix_llm_calls_called_at", "llm_calls", ["called_at"])


def downgrade() -> None:
    op.drop_table("llm_calls")
    op.drop_constraint("uq_feedback_item_id", "feedback", type_="unique")
    op.drop_column("sources", "trust_adjusted")
    op.execute("CREATE INDEX ix_items_title_trgm ON items USING gin (title gin_trgm_ops)")
    op.drop_column("items", "embedding_model")
    op.drop_column("items", "embedding")
