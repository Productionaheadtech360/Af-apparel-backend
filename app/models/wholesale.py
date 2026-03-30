"""Wholesale application model."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class WholesaleApplication(BaseModel):
    """Submitted by prospective wholesale buyers."""

    __tablename__ = "wholesale_applications"

    # Applicant info
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(100))
    business_type: Mapped[str] = mapped_column(String(100), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    expected_monthly_volume: Mapped[str | None] = mapped_column(String(100))

    # Contact info
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))

    # Status: pending | approved | rejected
    status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", name="application_status"),
        default="pending",
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    admin_notes: Mapped[str | None] = mapped_column(Text)

    # Set on approval
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    company: Mapped["Company | None"] = relationship("Company", back_populates="wholesale_application")
    reviewed_by: Mapped["User | None"] = relationship("User")
