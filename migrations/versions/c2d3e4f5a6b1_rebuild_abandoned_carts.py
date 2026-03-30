"""rebuild_abandoned_carts

Revision ID: c2d3e4f5a6b1
Revises: b1c2d3e4f5a6
Create Date: 2026-03-30 00:00:00.000000

Drop and recreate abandoned_carts with company_id-based schema.
The old table used user_id and lacked company_id, total, item_count,
abandoned_at, is_recovered, recovered_at, recovery_order_id.
The Celery detection task was broken (referenced CartItem.user_id which
does not exist), so the table was never populated — safe to recreate.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2d3e4f5a6b1"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("abandoned_carts")

    op.create_table(
        "abandoned_carts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("items_snapshot", sa.Text(), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("abandoned_at", sa.String(50), nullable=False),
        sa.Column("is_recovered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("recovered_at", sa.String(50), nullable=True),
        sa.Column("recovery_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recovery_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_abandoned_carts_company_id", "abandoned_carts", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_abandoned_carts_company_id", table_name="abandoned_carts")
    op.drop_table("abandoned_carts")

    op.create_table(
        "abandoned_carts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("items_snapshot", sa.Text(), nullable=False),
        sa.Column("total_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
