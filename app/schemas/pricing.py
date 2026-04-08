from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, computed_field, field_validator


class VolumeBreak(BaseModel):
    min_qty: int = 0
    discount: float = 0.0


class PricingTierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    discount_percent: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    description: str | None = None
    moq: int = 0
    free_shipping: bool = False
    shipping_discount_percentage: float = 0.0
    tax_exempt: bool = False
    tax_percentage: float = 0.0
    payment_terms: str = "immediate"
    credit_limit: float = 0.0
    priority_support: bool = False
    volume_breaks: list[dict[str, Any]] = []


class PricingTierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    discount_percent: Decimal | None = Field(None, ge=0, le=100, decimal_places=2)
    description: str | None = None
    moq: int | None = None
    free_shipping: bool | None = None
    shipping_discount_percentage: float | None = None
    tax_exempt: bool | None = None
    tax_percentage: float | None = None
    payment_terms: str | None = None
    credit_limit: float | None = None
    priority_support: bool | None = None
    volume_breaks: list[dict[str, Any]] | None = None


class PricingTierOut(BaseModel):
    id: UUID
    name: str
    discount_percent: Decimal
    description: str | None
    is_active: bool = True
    moq: int = 0
    free_shipping: bool = False
    shipping_discount_percentage: float = 0.0
    tax_exempt: bool = False
    tax_percentage: float = 0.0
    payment_terms: str = "immediate"
    credit_limit: float = 0.0
    priority_support: bool = False
    volume_breaks: list[dict[str, Any]] = []
    customer_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[misc]
    @property
    def discount_percentage(self) -> float:
        """Alias for discount_percent as a plain float — used by frontend."""
        return float(self.discount_percent)

    @field_validator("volume_breaks", mode="before")
    @classmethod
    def coerce_volume_breaks(cls, v: object) -> list:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []

    @field_validator("moq", mode="before")
    @classmethod
    def coerce_moq(cls, v: object) -> int:
        return int(v) if v is not None else 0

    @field_validator("free_shipping", "tax_exempt", "priority_support", mode="before")
    @classmethod
    def coerce_bool(cls, v: object) -> bool:
        return bool(v) if v is not None else False

    @field_validator("shipping_discount_percentage", "tax_percentage", "credit_limit", mode="before")
    @classmethod
    def coerce_float(cls, v: object) -> float:
        return float(v) if v is not None else 0.0
