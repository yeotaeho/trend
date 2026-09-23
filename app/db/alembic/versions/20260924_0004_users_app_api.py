"""users·user_id·피드백 유니크 (user_id, item_id), 앱 API 테이블·컬럼·인덱스 — 모바일 앱 v0.1

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 사용자별 데이터를 가진 기존 테이블. 새 앱 테이블은 create_table 에서 바로 user_id 를 받는다.
_USER_TABLES = ("feedback", "notifications")


def _user_id() -> sa.Column[int]:
    # 앱 테이블의 user_id 는 기본값이 없다. API 계층이 DEFAULT_USER_ID 를 명시로 넘긴다.
    return sa.Column(
        "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


def _now(name: str) -> sa.Column[datetime]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        _now("created_at"),
    )
    op.execute("INSERT INTO users (id, name) VALUES (1, 'owner')")
    op.execute("SELECT setval('users_id_seq', 1)")

    # server_default 로 기존 행을 채운 뒤 기본값을 뗀다. 이후 코드가 user_id 를 빠뜨리면
    # NOT NULL 위반으로 즉시 드러나야 한다.
    for table in _USER_TABLES:
        op.add_column(table, sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"))
        op.create_foreign_key(
            f"fk_{table}_user_id", table, "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.alter_column(table, "user_id", server_default=None)

    op.drop_constraint("uq_feedback_item_id", "feedback", type_="unique")
    op.create_unique_constraint("uq_feedback_user_item", "feedback", ["user_id", "item_id"])

    # 기존 판정은 전부 디스코드 버튼·리액션에서 왔다.
    op.add_column(
        "feedback",
        sa.Column("source", sa.String(10), nullable=False, server_default="discord"),
    )
    op.add_column("notifications", sa.Column("title", sa.Text(), nullable=True))
    op.create_index("ix_notifications_sent_at", "notifications", ["sent_at"])
    op.create_index("ix_decisions_created_at", "decisions", ["created_at"])

    op.create_table(
        "user_prefs",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("data", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        _now("updated_at"),
    )

    op.create_table(
        "bookmark_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        _user_id(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        _now("created_at"),
        sa.UniqueConstraint("user_id", "name", name="uq_bookmark_folders_user_name"),
    )

    op.create_table(
        "bookmarks",
        _user_id(),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "folder_id",
            sa.Integer(),
            sa.ForeignKey("bookmark_folders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        _now("saved_at"),
        sa.Column("resurfaced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "item_id"),
    )
    op.create_index("ix_bookmarks_folder_id", "bookmarks", ["folder_id"])
    op.create_index("ix_bookmarks_user_saved_at", "bookmarks", ["user_id", "saved_at"])

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        _user_id(),
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("app_version", sa.String(30), nullable=True),
        _now("created_at"),
        _now("last_seen_at"),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_devices_user_id", "devices", ["user_id"])

    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        _user_id(),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=False),
        sa.Column("sections", JSONB(), nullable=False),
        _now("created_at"),
        sa.UniqueConstraint("user_id", "period_start", name="uq_weekly_reports_user_period"),
    )


def downgrade() -> None:
    op.drop_table("weekly_reports")
    op.drop_table("devices")
    op.drop_table("bookmarks")
    op.drop_table("bookmark_folders")
    op.drop_table("user_prefs")

    op.drop_index("ix_decisions_created_at", table_name="decisions")
    op.drop_index("ix_notifications_sent_at", table_name="notifications")
    op.drop_column("notifications", "title")
    op.drop_column("feedback", "source")

    # 사용자가 하나뿐일 때만 되돌릴 수 있다. 같은 항목에 판정이 둘이면 유니크 생성이 실패한다.
    op.drop_constraint("uq_feedback_user_item", "feedback", type_="unique")
    op.create_unique_constraint("uq_feedback_item_id", "feedback", ["item_id"])
    for table in reversed(_USER_TABLES):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_constraint(f"fk_{table}_user_id", table, type_="foreignkey")
        op.drop_column(table, "user_id")
    op.drop_table("users")
