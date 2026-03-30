"""Communication models: Message, EmailTemplate."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.user import User


class Message(BaseModel):
    """In-platform messaging between company users and admin."""

    __tablename__ = "messages"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL")
    )
    is_read_by_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_read_by_company: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company: Mapped["Company"] = relationship("Company")
    sender: Mapped["User"] = relationship("User")


class EmailTemplate(BaseModel):
    """Admin-editable Jinja2 email templates keyed by trigger event."""

    __tablename__ = "email_templates"

    # Trigger events
    trigger_event: Mapped[str] = mapped_column(
        Enum(
            "order_confirmation",
            "order_shipped",
            "wholesale_approved",
            "wholesale_rejected",
            "password_reset",
            "email_verification",
            "welcome",
            "user_invitation",
            "rma_approved",
            "rma_rejected",
            "payment_failed",
            name="email_trigger_event",
        ),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False, comment="Jinja2 HTML template")
    body_text: Mapped[str | None] = mapped_column(Text, comment="Plain text fallback")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # JSON list of available variable names for this template
    available_variables: Mapped[str | None] = mapped_column(Text, comment="JSON array of variable names")
