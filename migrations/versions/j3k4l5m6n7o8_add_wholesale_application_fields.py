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
    op.add_column("wholesale_applications", sa.Column("company_email", sa.String(255), nullable=True))
    op.add_column("wholesale_applications", sa.Column("address_line1", sa.String(255), nullable=True))
    op.add_column("wholesale_applications", sa.Column("address_line2", sa.String(255), nullable=True))
    op.add_column("wholesale_applications", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("state_province", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("wholesale_applications", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("how_heard", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("num_employees", sa.String(50), nullable=True))
    op.add_column("wholesale_applications", sa.Column("num_sales_reps", sa.String(50), nullable=True))
    op.add_column("wholesale_applications", sa.Column("secondary_business", sa.String(255), nullable=True))
    op.add_column("wholesale_applications", sa.Column("estimated_annual_volume", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("ppac_number", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("ppai_number", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("asi_number", sa.String(100), nullable=True))
    op.add_column("wholesale_applications", sa.Column("fax", sa.String(50), nullable=True))


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
