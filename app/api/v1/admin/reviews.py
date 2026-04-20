"""Admin reviews router — list, approve/reject, delete reviews."""
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.product import Product, ProductReview
from app.schemas.review import ProductReviewOut

router = APIRouter(prefix="/admin/reviews", tags=["admin", "reviews"])


@router.get("")
async def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: UUID | None = Query(None),
    approved: bool | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    base = (
        select(ProductReview, Product.name.label("product_name"), Product.slug.label("product_slug"))
        .join(Product, ProductReview.product_id == Product.id)
    )
    if product_id:
        base = base.where(ProductReview.product_id == product_id)
    if approved is not None:
        base = base.where(ProductReview.is_approved == approved)
    if q:
        base = base.where(
            ProductReview.reviewer_name.ilike(f"%{q}%")
            | ProductReview.body.ilike(f"%{q}%")
        )

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(ProductReview.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()

    reviews = []
    for row in rows:
        data = ProductReviewOut.model_validate(row.ProductReview).model_dump()
        data["product_name"] = row.product_name
        data["product_slug"] = row.product_slug
        reviews.append(data)

    return {"reviews": reviews, "total": total, "page": page, "page_size": page_size}


@router.patch("/{review_id}")
async def update_review(
    review_id: UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProductReview).where(ProductReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise NotFoundError("Review not found")
    if "is_approved" in payload:
        review.is_approved = bool(payload["is_approved"])
    await db.commit()
    return ProductReviewOut.model_validate(review)


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProductReview).where(ProductReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise NotFoundError("Review not found")
    await db.delete(review)
    await db.commit()
