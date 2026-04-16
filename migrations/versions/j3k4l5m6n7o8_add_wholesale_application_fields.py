"""add_wholesale_application_fields

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-04-15

Adds extended registration form fields to wholesale_applications table.
"""
from alembic import op
import sqlalchemy as sa

revision = "j3k4l5m6n7o8"
down_revision = "i2j3k4l5m6n7"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column("wholesale_applications", "fax")
    op.drop_column("wholesale_applications", "asi_number")
    op.drop_column("wholesale_applications", "ppai_number")
    op.drop_column("wholesale_applications", "ppac_number")
    op.drop_column("wholesale_applications", "estimated_annual_volume")
    op.drop_column("wholesale_applications", "secondary_business")
    op.drop_column("wholesale_applications", "num_sales_reps")
    op.drop_column("wholesale_applications", "num_employees")
    op.drop_column("wholesale_applications", "how_heard")
    op.drop_column("wholesale_applications", "country")
    op.drop_column("wholesale_applications", "postal_code")
    op.drop_column("wholesale_applications", "state_province")
    op.drop_column("wholesale_applications", "city")
    op.drop_column("wholesale_applications", "address_line2")
    op.drop_column("wholesale_applications", "address_line1")
    op.drop_column("wholesale_applications", "company_email")
