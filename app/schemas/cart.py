from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Cart item
# ---------------------------------------------------------------------------

class CartItemAdd(BaseModel):
    variant_id: UUID
    quantity: int = Field(..., ge=1)


class MatrixAddRequest(BaseModel):
    product_id: UUID
    items: list[CartItemAdd] = Field(..., min_length=1)


class CartItemOut(BaseModel):
    id: UUID
    variant_id: UUID
    product_id: UUID
    product_name: str
    product_slug: str = ""
    product_image_url: str | None = None
    sku: str
    color: str | None
    size: str | None
    quantity: int
    retail_price: Decimal = Decimal("0")
    unit_price: Decimal
    line_total: Decimal
    moq: int
    moq_satisfied: bool
    stock_quantity: int

    model_config = {"from_attributes": True}


class CartValidation(BaseModel):
    is_valid: bool
    moq_violations: list[dict]   # [{variant_id, sku, required, current}]
    mov_violation: bool
    mov_required: Decimal
    mov_current: Decimal
    estimated_shipping: Decimal


class CartResponse(BaseModel):
    items: list[CartItemOut]
    subtotal: Decimal
    item_count: int
    total_units: int
    validation: CartValidation
    discount_percent: Decimal = Decimal("0")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Quick order (T137 — Phase 14)
# ---------------------------------------------------------------------------

class SkuQuantityPair(BaseModel):
    sku: str
    quantity: int = Field(..., ge=1)


class QuickOrderRequest(BaseModel):
    items: list[SkuQuantityPair]


class ValidationResultItem(BaseModel):
    sku: str
    quantity: int
    status: str  # valid | not_found | insufficient_stock
    product_name: str | None = None
    variant_id: UUID | None = None
    available_quantity: int | None = None


class QuickOrderResult(BaseModel):
    valid: list[ValidationResultItem]
    invalid: list[ValidationResultItem]
    insufficient_stock: list[ValidationResultItem]
    added_to_cart: int
