from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


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
    phone: str | None = None
    pricing_tier_id: UUID | None
    shipping_tier_id: UUID | None
    shipping_override_amount: Decimal | None
    stripe_customer_id: str | None
    qb_customer_id: str | None
    admin_notes: str | None = None
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(t) for t in v]
        return []


class CompanyUpdate(BaseModel):
    pricing_tier_id: UUID | None = None
    shipping_tier_id: UUID | None = None
    shipping_override_amount: Decimal | None = None
    status: str | None = None
    admin_notes: str | None = None
    tags: list[str] | None = None


class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=1)
