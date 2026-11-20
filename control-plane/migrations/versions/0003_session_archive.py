"""会话卷归档字段

Revision ID: 0003_session_archive
Revises: 0002_tenants_usage
Create Date: 2026-11-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_session_archive"
down_revision: str | None = "0002_tenants_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sessions", sa.Column("archive_path", sa.String(length=512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("archive_path")
        batch.drop_column("archived_at")
