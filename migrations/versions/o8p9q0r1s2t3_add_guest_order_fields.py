"""Add guest order fields to orders table."""
from alembic import op
import sqlalchemy as sa

revision = "o8p9q0r1s2t3"
down_revision = "n7o8p9q0r1s2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make company_id and placed_by_id nullable so guest orders have no FK
    op.alter_column("orders", "company_id", nullable=True)
    op.alter_column("orders", "placed_by_id", nullable=True)

    # Guest-specific fields
    op.add_column("orders", sa.Column("guest_email", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("guest_name", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("guest_phone", sa.String(50), nullable=True))
    op.add_column("orders", sa.Column(
        "is_guest_order", sa.Boolean(), nullable=False, server_default="false"
    ))


def downgrade() -> None:
    op.drop_column("orders", "is_guest_order")
    op.drop_column("orders", "guest_phone")
    op.drop_column("orders", "guest_name")
    op.drop_column("orders", "guest_email")
    op.alter_column("orders", "company_id", nullable=False)
    op.alter_column("orders", "placed_by_id", nullable=False)
