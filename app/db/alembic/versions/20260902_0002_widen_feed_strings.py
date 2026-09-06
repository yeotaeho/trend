"""items.external_id·author 를 text 로 — 피드가 주는 문자열은 길이를 보장할 수 없다

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # arXiv 저자 목록이 varchar(300) 을 넘겨 적재가 죽었다. Postgres 에서 varchar(n) 은
    # text 대비 성능 이득이 없으므로 외부 유입 문자열에는 길이 제한을 두지 않는다.
    op.alter_column(
        "items",
        "author",
        type_=sa.Text(),
        existing_type=sa.String(300),
        existing_nullable=True,
    )
    op.alter_column(
        "items",
        "external_id",
        type_=sa.Text(),
        existing_type=sa.String(500),
        existing_nullable=False,
    )


def downgrade() -> None:
    # 이미 긴 값이 들어가 있으면 되돌리기가 실패한다.
    op.alter_column(
        "items",
        "external_id",
        type_=sa.String(500),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "items",
        "author",
        type_=sa.String(300),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
