"""add_company_registration_fields

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-04-15

Adds wholesale registration form fields to companies table and
tab-content fields (care_instructions, print_guide, size_chart_data)
to products table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "i2j3k4l5m6n7"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Companies: registration form fields ─────────────────────────────────
    op.add_column("companies", sa.Column("company_email", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("address_line1", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("address_line2", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("state_province", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("companies", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("how_heard", sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("num_employees", sa.String(50), nullable=True))
    op.add_column("companies", sa.Column("num_sales_reps", sa.String(50), nullable=True))

    # ── Products: tab content fields ─────────────────────────────────────────
    op.add_column("products", sa.Column("care_instructions", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("print_guide", JSONB(), nullable=True))
    op.add_column("products", sa.Column("size_chart_data", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "size_chart_data")
    op.drop_column("products", "print_guide")
    op.drop_column("products", "care_instructions")
    op.drop_column("companies", "num_sales_reps")
    op.drop_column("companies", "num_employees")
    op.drop_column("companies", "how_heard")
    op.drop_column("companies", "country")
    op.drop_column("companies", "postal_code")
    op.drop_column("companies", "state_province")
    op.drop_column("companies", "city")
    op.drop_column("companies", "address_line2")
    op.drop_column("companies", "address_line1")
    op.drop_column("companies", "company_email")
