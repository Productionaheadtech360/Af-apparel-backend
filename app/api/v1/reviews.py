from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/recent")
async def list_recent_reviews(
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    from app.models.product import Product, ProductReview
    from app.schemas.review import ProductReviewOut

    result = await db.execute(
        select(ProductReview, Product.name.label("product_name"), Product.slug.label("product_slug"))
        .join(Product, ProductReview.product_id == Product.id)
        .where(ProductReview.is_approved == True)  # noqa: E712
        .order_by(ProductReview.created_at.desc())
        .limit(page_size)
    )
    rows = result.all()

    reviews = []
    for row in rows:
        review_out = ProductReviewOut.model_validate(row.ProductReview)
        data = review_out.model_dump()
        data["product_name"] = row.product_name
        data["product_slug"] = row.product_slug
        reviews.append(data)

    count_result = await db.execute(
        select(func.count(ProductReview.id)).where(ProductReview.is_approved == True)  # noqa: E712
    )
    total = count_result.scalar_one()

    avg_result = await db.execute(
        select(func.avg(ProductReview.rating)).where(ProductReview.is_approved == True)  # noqa: E712
    )
    avg_rating = round(float(avg_result.scalar_one() or 0), 1)

    return {"reviews": reviews, "total": total, "avg_rating": avg_rating}
