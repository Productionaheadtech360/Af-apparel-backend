"""Shipping tier and bracket models."""
import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ShippingTier(BaseModel):
    """Bracket-based shipping cost table. Assigned per company."""

    __tablename__ = "shipping_tiers"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # 'units'       → cost based on total piece count
    # 'order_value' → cost based on order subtotal ($)
    # 'free'        → always $0 (e.g. Will Call Pick)
    calculation_type: Mapped[str] = mapped_column(String(20), default="units", nullable=False)

    # e.g. "12PM", "3PM" — informational, shown on checkout
    cutoff_time: Mapped[str | None] = mapped_column(String(20))

    brackets: Mapped[list["ShippingBracket"]] = relationship(
        "ShippingBracket",
        back_populates="tier",
        cascade="all, delete-orphan",
    )


class ShippingBracket(BaseModel):
    """One cost bracket within a shipping tier."""

    __tablename__ = "shipping_brackets"

    tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipping_tiers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Unit-based tiers use these
    min_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_units: Mapped[int | None] = mapped_column(Integer, comment="NULL = no upper bound")

    # Order-value-based tiers use these (dollars)
    min_order_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_order_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), comment="NULL = no upper bound")

    # 0 = free shipping for this bracket
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    tier: Mapped["ShippingTier"] = relationship("ShippingTier", back_populates="brackets")
