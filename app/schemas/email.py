from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EmailTemplateOut(BaseModel):
    id: UUID
    trigger_event: str
    name: str
    subject: str
    body_html: str
    body_text: str | None
    is_active: bool
    available_variables: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    is_active: bool | None = None


class PreviewRequest(BaseModel):
    variables: dict = {}


class PreviewResponse(BaseModel):
    subject: str
    body_html: str
    body_text: str | None
