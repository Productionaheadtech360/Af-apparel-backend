from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class DiscountCodeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    discount_type: str
    discount_value: Decimal = Decimal("0")
    minimum_order_amount: Decimal | None = None
    usage_limit_total: int | None = None
    usage_limit_per_customer: int | None = None
    applicable_to: str = "all"
    applicable_ids: list[str] = []
    customer_eligibility: str = "all"
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool = True


class DiscountCodeUpdate(BaseModel):
    discount_type: str | None = None
    discount_value: Decimal | None = None
    minimum_order_amount: Decimal | None = None
    usage_limit_total: int | None = None
    usage_limit_per_customer: int | None = None
    applicable_to: str | None = None
    applicable_ids: list[str] | None = None
    customer_eligibility: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class ValidateDiscountRequest(BaseModel):
    code: str
    cart_total: Decimal
    user_id: UUID | None = None
    customer_type: str = "wholesale"


class ValidateDiscountResponse(BaseModel):
    valid: bool
    message: str
    discount_type: str | None = None
    discount_value: Decimal | None = None
    discount_amount: Decimal | None = None
    final_total: Decimal | None = None
    code: str | None = None
    discount_code_id: UUID | None = None


class ApplyDiscountRequest(BaseModel):
    code: str
    order_id: UUID | None = None
    user_id: UUID | None = None
    cart_total: Decimal
    customer_type: str = "wholesale"
