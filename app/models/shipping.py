"""Shipping tier and bracket models."""
import uuid

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

    brackets: Mapped[list["ShippingBracket"]] = relationship(
        "ShippingBracket",
        back_populates="tier",
        cascade="all, delete-orphan",
        order_by="ShippingBracket.min_units",
    )


class ShippingBracket(BaseModel):
    """One cost bracket within a shipping tier."""

    __tablename__ = "shipping_brackets"

    tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipping_tiers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    min_units: Mapped[int] = mapped_column(Integer, nullable=False)
    max_units: Mapped[int | None] = mapped_column(Integer, comment="NULL = no upper bound")
    cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    tier: Mapped["ShippingTier"] = relationship("ShippingTier", back_populates="brackets")
