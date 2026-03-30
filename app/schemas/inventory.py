from uuid import UUID
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class WarehouseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"


class WarehouseOut(BaseModel):
    id: UUID
    name: str
    code: str
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryAdjustRequest(BaseModel):
    variant_id: UUID
    warehouse_id: UUID
    quantity_delta: int  # positive = add, negative = remove
    reason: str  # received | damaged | returned | correction | sold | migration
    notes: str | None = None


class AdjustmentResult(BaseModel):
    variant_id: UUID
    warehouse_id: UUID
    quantity_after: int


class BulkImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
