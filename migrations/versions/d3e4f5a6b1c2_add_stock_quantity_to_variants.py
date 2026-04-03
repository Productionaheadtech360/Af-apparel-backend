"""add_stock_quantity_to_variants

Revision ID: d3e4f5a6b1c2
Revises: c2d3e4f5a6b1
Create Date: 2026-04-03 00:00:00.000000

Adds an optional stock_quantity column to product_variants.
NULL means unlimited stock — the order service skips the stock check
when this column is NULL or when no inventory records exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "d3e4f5a6b1c2"
down_revision = "c2d3e4f5a6b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE product_variants "
        "ADD COLUMN IF NOT EXISTS stock_quantity INTEGER DEFAULT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE product_variants "
        "DROP COLUMN IF EXISTS stock_quantity"
    )
