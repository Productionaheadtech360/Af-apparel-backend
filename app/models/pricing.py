"""Pricing tier model."""
from sqlalchemy import Numeric, String, Text
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
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
