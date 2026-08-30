"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("poll_interval_sec", sa.Integer(), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_normalized", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary_raw", sa.Text()),
        sa.Column("author", sa.String(300)),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("cluster_id", sa.Integer()),
        sa.Column("score", sa.Float()),
        sa.Column("raw", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("url_hash", name="uq_items_url_hash"),
    )
    op.create_index("ix_items_source_id", "items", ["source_id"])
    op.create_index("ix_items_status", "items", ["status"])
    op.create_index("ix_items_published_at", "items", ["published_at"])
    op.create_index("ix_items_cluster_id", "items", ["cluster_id"])
    op.execute("CREATE INDEX ix_items_title_trgm ON items USING gin (title gin_trgm_ops)")

    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("stage", sa.String(10), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_decisions_item_id", "decisions", ["item_id"])

    op.create_table(
        "summaries",
        sa.Column(
            "item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("title_ko", sa.Text(), nullable=False),
        sa.Column("summary_ko", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("worth_notifying", sa.Boolean(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("message_id", sa.String(100)),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_notifications_item_id", "notifications", ["item_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("verdict", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_feedback_item_id", "feedback", ["item_id"])


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("notifications")
    op.drop_table("summaries")
    op.drop_table("decisions")
    op.drop_table("items")
    op.drop_table("sources")
