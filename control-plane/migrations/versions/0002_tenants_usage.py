"""租户、用户与 LLM 用量

Revision ID: 0002_tenants_usage
Revises: 0001_initial
Create Date: 2026-11-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_tenants_usage"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("max_active_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_token_budget", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("subject", sa.String(length=128), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), nullable=False),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_usage_session_id", "llm_usage", ["session_id"])
    op.create_index("ix_llm_usage_tenant_id", "llm_usage", ["tenant_id"])

    # 存量会话归入 default 租户；租户行在用户首次登录时按默认配额建档（ensure_principal）。
    op.add_column(
        "sessions",
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
    )
    op.create_index("ix_sessions_tenant_id", "sessions", ["tenant_id"])


def downgrade() -> None:
    # SQLite 不支持原生 DROP COLUMN 时由 batch 模式重建表（Postgres 仍走原生 ALTER）；
    # 先删索引，否则 batch 反射会把引用 tenant_id 的索引原样重建回新表。
    op.drop_index("ix_sessions_tenant_id", table_name="sessions")
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("tenant_id")
    op.drop_index("ix_llm_usage_tenant_id", table_name="llm_usage")
    op.drop_index("ix_llm_usage_session_id", table_name="llm_usage")
    op.drop_table("llm_usage")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
