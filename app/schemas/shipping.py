from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class ShippingBracketIn(BaseModel):
    # Unit-based fields
    min_units: int = Field(0, ge=0)
    max_units: int | None = Field(None, ge=1)

    # Order-value-based fields (dollars)
    min_order_value: Decimal | None = Field(None, ge=0, decimal_places=2)
    max_order_value: Decimal | None = Field(None, ge=0, decimal_places=2)

    # Cost ($0 = free for this bracket)
    cost: Decimal = Field(..., ge=0, decimal_places=2)


class ShippingBracketOut(BaseModel):
    id: UUID
    min_units: int
    max_units: int | None
    min_order_value: Decimal | None
    max_order_value: Decimal | None
    cost: Decimal

    model_config = {"from_attributes": True}


class ShippingTierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    calculation_type: Literal["units", "order_value", "free"] = "units"
    cutoff_time: str | None = Field(None, max_length=20)
    brackets: list[ShippingBracketIn] = []


class ShippingTierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    calculation_type: Literal["units", "order_value", "free"] | None = None
    cutoff_time: str | None = None
    is_active: bool | None = None
    brackets: list[ShippingBracketIn] | None = None


class ShippingTierOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    calculation_type: str
    cutoff_time: str | None
    is_active: bool
    brackets: list[ShippingBracketOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
