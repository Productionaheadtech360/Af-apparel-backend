"""Wholesale application Pydantic schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class WholesaleApplicationOut(BaseModel):
    id: uuid.UUID
    company_name: str
    tax_id: str | None
    business_type: str
    website: str | None
    expected_monthly_volume: str | None
    first_name: str
    last_name: str
    email: str
    phone: str | None
    status: str
    rejection_reason: str | None
    admin_notes: str | None
    company_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveApplicationRequest(BaseModel):
    pricing_tier_id: uuid.UUID
    shipping_tier_id: uuid.UUID
    admin_notes: str | None = None


class RejectApplicationRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=10, max_length=1000)
    admin_notes: str | None = None
