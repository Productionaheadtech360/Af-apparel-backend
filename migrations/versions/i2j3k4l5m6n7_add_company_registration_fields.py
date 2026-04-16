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
    # ── Companies: registration form fields (IF NOT EXISTS — idempotent) ─────
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS company_email VARCHAR(255)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(255)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(255)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS city VARCHAR(100)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS state_province VARCHAR(100)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS country VARCHAR(100)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS how_heard VARCHAR(100)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS num_employees VARCHAR(50)")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS num_sales_reps VARCHAR(50)")

    # ── Products: tab content fields (IF NOT EXISTS — idempotent) ────────────
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS care_instructions TEXT")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS print_guide JSONB")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS size_chart_data JSONB")


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
