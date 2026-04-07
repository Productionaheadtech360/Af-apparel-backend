"""Add product_type, vendor, tags to products; compare_price to variants.

Revision ID: f6e5d4c3b2a1
Revises: e1f2a3b4c5d6
Create Date: 2026-04-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6e5d4c3b2a1"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("product_type", sa.String(100), nullable=True))
    op.add_column("products", sa.Column("vendor", sa.String(255), nullable=True))
    op.add_column("products", sa.Column("tags", postgresql.ARRAY(sa.String(100)), nullable=True))
    op.add_column("product_variants", sa.Column("compare_price", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("product_variants", "compare_price")
    op.drop_column("products", "tags")
    op.drop_column("products", "vendor")
    op.drop_column("products", "product_type")
