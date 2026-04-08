"""Add tags (JSON) and admin_notes visibility to companies table.

Revision ID: a2b3c4d5e6f7
Revises: f6e5d4c3b2a1
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a2b3c4d5e6f7"
down_revision = "f6e5d4c3b2a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tags as a JSON array column (nullable, defaults to empty array)
    op.add_column(
        "companies",
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="'[]'::jsonb"),
    )


def downgrade() -> None:
    op.drop_column("companies", "tags")
