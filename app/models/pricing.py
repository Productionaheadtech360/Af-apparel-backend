"""Pricing tier model."""
from sqlalchemy import Boolean, Float, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PricingTier(BaseModel):
    """Discount tier assigned per company. discount_percent applied to retail_price."""

    __tablename__ = "pricing_tiers"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    discount_percent: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Discount percentage off retail price (e.g. 25.00 = 25%)",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Extended tier fields
    moq: Mapped[int | None] = mapped_column(Integer, default=0, server_default="0")
    free_shipping: Mapped[bool | None] = mapped_column(Boolean, default=False, server_default="false")
    shipping_discount_percentage: Mapped[float | None] = mapped_column(Float, default=0, server_default="0")
    tax_exempt: Mapped[bool | None] = mapped_column(Boolean, default=False, server_default="false")
    tax_percentage: Mapped[float | None] = mapped_column(Float, default=0, server_default="0")
    payment_terms: Mapped[str | None] = mapped_column(String(50), default="immediate", server_default="'immediate'")
    credit_limit: Mapped[float | None] = mapped_column(Float, default=0, server_default="0")
    priority_support: Mapped[bool | None] = mapped_column(Boolean, default=False, server_default="false")
    volume_breaks: Mapped[list | None] = mapped_column(JSONB, default=list, server_default="'[]'::jsonb")
