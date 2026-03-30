from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class PricingTierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    discount_percent: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    description: str | None = None


class PricingTierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    discount_percent: Decimal | None = Field(None, ge=0, le=100, decimal_places=2)
    description: str | None = None


class PricingTierOut(BaseModel):
    id: UUID
    name: str
    discount_percent: Decimal
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
