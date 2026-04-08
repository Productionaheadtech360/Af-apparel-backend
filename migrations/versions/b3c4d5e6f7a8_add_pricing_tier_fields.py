"""Add extended fields to pricing_tiers table.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pricing_tiers", sa.Column("moq", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("pricing_tiers", sa.Column("free_shipping", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("pricing_tiers", sa.Column("shipping_discount_percentage", sa.Float(), nullable=True, server_default="0"))
    op.add_column("pricing_tiers", sa.Column("tax_exempt", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("pricing_tiers", sa.Column("tax_percentage", sa.Float(), nullable=True, server_default="0"))
    op.add_column("pricing_tiers", sa.Column("payment_terms", sa.String(50), nullable=True, server_default="'immediate'"))
    op.add_column("pricing_tiers", sa.Column("credit_limit", sa.Float(), nullable=True, server_default="0"))
    op.add_column("pricing_tiers", sa.Column("priority_support", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("pricing_tiers", sa.Column("volume_breaks", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="'[]'::jsonb"))


def downgrade() -> None:
    for col in ["moq", "free_shipping", "shipping_discount_percentage", "tax_exempt",
                "tax_percentage", "payment_terms", "credit_limit", "priority_support", "volume_breaks"]:
        op.drop_column("pricing_tiers", col)
