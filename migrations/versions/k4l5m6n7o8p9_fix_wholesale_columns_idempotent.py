"""fix_wholesale_columns_idempotent

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-04-16

Idempotent catch-up: adds any missing columns to wholesale_applications and
companies that were introduced by migrations i2j3k4l5m6n7 and j3k4l5m6n7o8
but may not have run successfully on all environments.

Uses ADD COLUMN IF NOT EXISTS so this migration is safe to run even if some
or all columns already exist.
"""
from alembic import op

revision = "k4l5m6n7o8p9"
down_revision = "j3k4l5m6n7o8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── wholesale_applications: extended registration fields ─────────────────
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS company_email VARCHAR(255)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(255)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(255)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS city VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS state_province VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS country VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS how_heard VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS num_employees VARCHAR(50)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS num_sales_reps VARCHAR(50)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS secondary_business VARCHAR(255)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS estimated_annual_volume VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS ppac_number VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS ppai_number VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS asi_number VARCHAR(100)")
    op.execute("ALTER TABLE wholesale_applications ADD COLUMN IF NOT EXISTS fax VARCHAR(50)")

    # ── companies: registration form fields ──────────────────────────────────
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

    # ── products: tab content fields ─────────────────────────────────────────
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS care_instructions TEXT")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS print_guide JSONB")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS size_chart_data JSONB")


def downgrade() -> None:
    # No downgrade — these columns are additive and safe to leave in place.
    pass
