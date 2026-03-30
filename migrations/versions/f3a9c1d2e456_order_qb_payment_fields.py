"""order_qb_payment_fields

Revision ID: f3a9c1d2e456
Revises: e114fbbfad6b
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a9c1d2e456'
down_revision: Union[str, None] = 'e114fbbfad6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('qb_payment_charge_id', sa.String(length=255), nullable=True))
    op.create_index('ix_orders_qb_payment_charge_id', 'orders', ['qb_payment_charge_id'], unique=False)
    op.add_column('orders', sa.Column('qb_payment_status', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_index('ix_orders_qb_payment_charge_id', table_name='orders')
    op.drop_column('orders', 'qb_payment_charge_id')
    op.drop_column('orders', 'qb_payment_status')
