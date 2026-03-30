from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class ShippingBracketIn(BaseModel):
    min_units: int = Field(..., ge=0)
    max_units: int | None = Field(None, ge=1)
    cost: Decimal = Field(..., ge=0, decimal_places=2)


class ShippingBracketOut(BaseModel):
    id: UUID
    min_units: int
    max_units: int | None
    cost: Decimal

    model_config = {"from_attributes": True}


class ShippingTierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    brackets: list[ShippingBracketIn] = Field(..., min_length=1)


class ShippingTierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    brackets: list[ShippingBracketIn] | None = None


class ShippingTierOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    brackets: list[ShippingBracketOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
