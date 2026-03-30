from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class PriceListRequestOut(BaseModel):
    id: UUID
    company_id: UUID
    format: str
    status: str
    file_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
