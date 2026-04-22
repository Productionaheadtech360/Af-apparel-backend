"""add_discount_groups_and_variant_pricing

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-04-22

"""
import sqlalchemy as sa
from alembic import op

revision = "l5m6n7o8p9q0"
down_revision = "k4l5m6n7o8p9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discount_groups",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("customer_tag", sa.String(100), nullable=True),
        sa.Column("applies_to", sa.String(20), nullable=False, server_default="'store'"),
        sa.Column("min_req_type", sa.String(20), nullable=False, server_default="'none'"),
        sa.Column("min_req_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("shipping_type", sa.String(20), nullable=False, server_default="'store_default'"),
        sa.Column("shipping_amount", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'enabled'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "variant_pricing_overrides",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("product_id", sa.String(36), nullable=False, index=True),
        sa.Column("tier_id", sa.String(36), nullable=False, index=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_id", "tier_id", name="uq_variant_pricing_product_tier"),
    )


def downgrade() -> None:
    op.drop_table("variant_pricing_overrides")
    op.drop_table("discount_groups")
