"""Add gender column to products; merge branch heads.

Revision ID: h1i2j3k4l5m6
Revises: c4d5e6f7a8b9, g7f6e5d4c3b2
Create Date: 2026-04-14

Merges:
  - c4d5e6f7a8b9 (add_category_image_url branch)
  - g7f6e5d4c3b2 (seed_email_templates branch)
"""
from alembic import op
import sqlalchemy as sa

revision = "h1i2j3k4l5m6"
down_revision = ("c4d5e6f7a8b9", "g7f6e5d4c3b2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("gender", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "gender")
