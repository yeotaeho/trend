"""settings_revisions — 설정 저장 이력과 버전 되돌리기 (에픽 #30, #34)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settings_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("changes", JSONB(), nullable=False),
        sa.Column("origin", sa.String(10), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_settings_revisions_user_id", "settings_revisions", ["user_id", "id"])


def downgrade() -> None:
    # 이력이 사라진다. 0005 가 없는 옛 SHA 이미지로 되돌리기 전에만 내린다(deploy-verify 롤백 절).
    op.drop_table("settings_revisions")
