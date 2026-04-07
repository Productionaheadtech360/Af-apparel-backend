from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Address snapshot
# ---------------------------------------------------------------------------

class AddressIn(BaseModel):
    label: str = "Default"
    full_name: str | None = None
    line1: str
    line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    phone: str | None = None
    is_default: bool = False


class AddressOut(BaseModel):
    id: UUID
    label: str | None = None
    full_name: str | None = None
    line1: str = Field(validation_alias="address_line1")
    line2: str | None = Field(None, validation_alias="address_line2")
    city: str
    state: str
    postal_code: str
    country: str
    phone: str | None = None
    is_default: bool

    model_config = {"from_attributes": True, "populate_by_name": True}


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

class CreatePaymentIntentRequest(BaseModel):
    cart_validated: bool = True  # client confirms cart is valid


class CheckoutConfirmRequest(BaseModel):
    # Stripe flow (legacy — kept for backward compatibility)
    payment_intent_id: str | None = None

    # QuickBooks Payments flow
    qb_token: str | None = None          # one-time charge token from QB.js or server tokenize
    saved_card_id: str | None = None     # QB card ID from customer wallet
    qb_customer_id: str | None = None    # QB customer ID (required when using saved card)
    save_card: bool = False              # attach token to QB customer wallet after charge

    address_id: UUID | None = None
    shipping_address: AddressIn | None = None
    po_number: str | None = None
    order_notes: str | None = None


# ---------------------------------------------------------------------------
# Order output
# ---------------------------------------------------------------------------

class OrderItemOut(BaseModel):
    id: UUID
    variant_id: UUID
    product_name: str
    sku: str
    color: str | None
    size: str | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: UUID
    order_number: str
    status: str
    payment_status: str
    po_number: str | None
    order_notes: str | None
    subtotal: Decimal
    shipping_cost: Decimal
    total: Decimal
    items: list[OrderItemOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    id: UUID
    order_number: str
    status: str
    payment_status: str
    po_number: str | None
    total: Decimal
    item_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Admin order management (T176 — US-14)
# ---------------------------------------------------------------------------

class AdminOrderListItem(BaseModel):
    id: UUID
    order_number: str
    company_name: str
    status: str
    payment_status: str
    po_number: str | None
    total: Decimal
    item_count: int
    created_at: datetime
    tracking_number: str | None = None
    courier: str | None = None
    courier_service: str | None = None
    shipped_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminOrderDetail(OrderOut):
    company_id: UUID
    company_name: str
    tracking_number: str | None
    courier: str | None = None
    courier_service: str | None = None
    shipped_at: datetime | None = None
    qb_invoice_id: str | None

    model_config = {"from_attributes": True}


class OrderUpdateRequest(BaseModel):
    status: str | None = None
    tracking_number: str | None = None
    courier: str | None = None
    courier_service: str | None = None
    notes: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str
    tracking_number: str | None = None
    courier: str | None = None
    courier_service: str | None = None


class CancelOrderRequest(BaseModel):
    reason: str = Field(..., min_length=1)
    refund: bool = True


class SyncResult(BaseModel):
    success: bool
    qb_invoice_id: str | None = None
    message: str


# ---------------------------------------------------------------------------
# RMA schemas (T179 — US-14)
# ---------------------------------------------------------------------------

class RMAItemCreate(BaseModel):
    order_item_id: UUID
    quantity: int = Field(..., ge=1)
    reason: str | None = None


class RMACreate(BaseModel):
    order_id: UUID
    reason: str = Field(..., min_length=1, max_length=500)
    items: list[RMAItemCreate]
    notes: str | None = None


class RMAItemOut(BaseModel):
    id: UUID
    order_item_id: UUID
    quantity: int
    reason: str | None

    model_config = {"from_attributes": True}


class RMAOut(BaseModel):
    id: UUID
    order_id: UUID
    rma_number: str
    status: str
    reason: str
    notes: str | None
    admin_notes: str | None
    items: list[RMAItemOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class RMAUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|completed)$")
    admin_notes: str | None = None
