"""add_courier_fields_to_orders

Revision ID: e1f2a3b4c5d6
Revises: d3e4f5a6b1c2
Create Date: 2026-04-06 00:00:00.000000

Adds courier, courier_service, and shipped_at columns to the orders table.
courier/courier_service store which carrier and service level was used for shipping.
shipped_at is set automatically when order status is changed to 'shipped'.
"""
from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "d3e4f5a6b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE orders "
        "ADD COLUMN IF NOT EXISTS courier VARCHAR(100)"
    )
    op.execute(
        "ALTER TABLE orders "
        "ADD COLUMN IF NOT EXISTS courier_service VARCHAR(100)"
    )
    op.execute(
        "ALTER TABLE orders "
        "ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMP WITH TIME ZONE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS courier")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS courier_service")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS shipped_at")
