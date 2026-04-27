"""Add shipping_method to orders; add ready_for_pickup to order_status enum."""
from alembic import op
import sqlalchemy as sa

revision = "p9q0r1s2t3u4"
down_revision = "o8p9q0r1s2t3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ready_for_pickup to the PostgreSQL enum type
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'ready_for_pickup'")

    # Add shipping_method column
    op.add_column("orders", sa.Column("shipping_method", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "shipping_method")
    # Note: PostgreSQL does not support removing values from an enum type.
    # The 'ready_for_pickup' value must be removed manually if needed.
