from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class ProductReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: str | None = Field(None, max_length=255)
    body: str = Field(..., min_length=10, max_length=2000)
    reviewer_name: str = Field(..., min_length=1, max_length=150)
    reviewer_company: str | None = Field(None, max_length=150)
    image_url: str | None = Field(None, max_length=1000)


class ProductReviewOut(BaseModel):
    id: UUID
    product_id: UUID
    rating: int
    title: str | None
    body: str
    reviewer_name: str
    reviewer_company: str | None
    is_verified: bool
    image_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewsResponse(BaseModel):
    reviews: list[ProductReviewOut]
    total: int
    avg_rating: float
