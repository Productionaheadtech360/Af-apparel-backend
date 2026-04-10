"""add image_url to categories

Revision ID: a1b2c3d4e5f6
Revises: f6e5d4c3b2a1
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f6e5d4c3b2a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("image_url", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("categories", "image_url")
