"""add_discount_codes

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2026-04-23

"""
import sqlalchemy as sa
from alembic import op

revision = "m6n7o8p9q0r1"
down_revision = "l5m6n7o8p9q0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discount_codes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("code", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("discount_type", sa.String(20), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("minimum_order_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("usage_limit_total", sa.Integer(), nullable=True),
        sa.Column("usage_limit_per_customer", sa.Integer(), nullable=True),
        sa.Column("applicable_to", sa.String(30), nullable=False, server_default="'all'"),
        sa.Column("applicable_ids", sa.Text(), nullable=True),
        sa.Column("customer_eligibility", sa.String(20), nullable=False, server_default="'all'"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "discount_usage",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("discount_code_id", sa.UUID(), sa.ForeignKey("discount_codes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("order_id", sa.UUID(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("discount_amount_applied", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("discount_usage")
    op.drop_table("discount_codes")
