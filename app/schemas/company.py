from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class CompanyListItem(BaseModel):
    id: UUID
    name: str
    status: str
    pricing_tier_id: UUID | None
    shipping_tier_id: UUID | None
    order_count: int = 0
    total_spend: Decimal = Decimal("0")
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyDetail(BaseModel):
    id: UUID
    name: str
    status: str
    tax_id: str | None
    business_type: str | None
    website: str | None
    pricing_tier_id: UUID | None
    shipping_tier_id: UUID | None
    shipping_override_amount: Decimal | None
    stripe_customer_id: str | None
    qb_customer_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    pricing_tier_id: UUID | None = None
    shipping_tier_id: UUID | None = None
    shipping_override_amount: Decimal | None = None
    status: str | None = None


class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=1)
