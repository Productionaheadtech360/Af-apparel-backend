"""DiscountCode and DiscountUsage models."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DiscountCode(BaseModel):
    __tablename__ = "discount_codes"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    minimum_order_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    usage_limit_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_limit_per_customer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicable_to: Mapped[str] = mapped_column(String(30), nullable=False, server_default="'all'")
    applicable_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_eligibility: Mapped[str] = mapped_column(String(20), nullable=False, server_default="'all'")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    usages: Mapped[list["DiscountUsage"]] = relationship("DiscountUsage", back_populates="discount_code")


class DiscountUsage(BaseModel):
    __tablename__ = "discount_usage"

    discount_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discount_codes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False,
    )
    discount_amount_applied: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    discount_code: Mapped["DiscountCode"] = relationship("DiscountCode", back_populates="usages")
