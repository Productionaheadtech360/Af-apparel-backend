# backend/app/api/v1/products.py
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.schemas.product import CategoryOut, FilterParams, ProductDetail, ProductListItem
from app.schemas.review import ProductReviewCreate
from app.services.product_service import ProductService
from app.types.api import PaginatedResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    svc = ProductService(db)
    return await svc.get_category_tree()


@router.get("", response_model=PaginatedResponse[ProductListItem])
async def list_products(
    request: Request,
    category: str | None = None,
    size: str | None = None,
    color: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    gender: str | None = None,
    fabric: str | None = None,
    weight: str | None = None,
    in_stock: bool | None = None,
    product_code: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    discount_percent = getattr(request.state, "tier_discount_percent", Decimal("0"))
    params = FilterParams(
        category=category,
        size=size,
        color=color,
        price_min=price_min,
        price_max=price_max,
        q=q,
        page=page,
        page_size=page_size,
        gender=gender,
        fabric=fabric,
        weight=weight,
        in_stock=in_stock,
        product_code=product_code,
    )
    svc = ProductService(db)
    items, total = await svc.list_with_filters_and_search(params, discount_percent)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{slug}", response_model=ProductDetail)
async def get_product(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    discount_percent = getattr(request.state, "tier_discount_percent", Decimal("0"))
    svc = ProductService(db)
    return await svc.get_by_slug_with_variants(slug, discount_percent)


# ── T201: Asset download endpoints ────────────────────────────────────────────

@router.get("/{product_id}/download-images")
async def download_product_images(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stream a ZIP of all product images (large size) from S3."""
    import io
    import zipfile

    import boto3
    from fastapi.responses import StreamingResponse

    from app.core.config import settings
    from app.models.product import Product, ProductImage

    result = await db.execute(
        select(Product)
        .options(selectinload(Product.images))
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not product.images:
        raise HTTPException(status_code=404, detail="No images available for this product")

    def _generate_zip():
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, img in enumerate(product.images):
                # Extract S3 key from URL
                url = img.url_large
                if url.startswith("https://"):
                    key = url.split(".amazonaws.com/", 1)[-1]
                else:
                    key = url.lstrip("/")
                try:
                    obj = s3.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
                    img_bytes = obj["Body"].read()
                    ext = key.rsplit(".", 1)[-1] if "." in key else "jpg"
                    zf.writestr(f"image_{i + 1:02d}.{ext}", img_bytes)
                except Exception:
                    pass
        buf.seek(0)
        return buf.read()

    zip_bytes = _generate_zip()
    safe_name = product.slug.replace("/", "_")

    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-images.zip"'},
    )


@router.get("/{product_id}/download-flyer")
async def download_product_flyer(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Redirect to S3 pre-signed URL for the product flyer PDF."""
    import boto3
    from app.core.config import settings
    from app.models.product import Product, ProductAsset

    result = await db.execute(
        select(Product)
        .options(selectinload(Product.assets))
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    flyer = next(
        (a for a in product.assets if a.asset_type == "flyer"),
        None,
    )
    if not flyer:
        raise HTTPException(status_code=404, detail="No flyer available for this product")

    if settings.AWS_ACCESS_KEY_ID:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        )
        url = flyer.url
        if url.startswith("https://"):
            key = url.split(".amazonaws.com/", 1)[-1]
        else:
            key = url.lstrip("/")
        presigned = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
            ExpiresIn=300,
        )
        return RedirectResponse(url=presigned)

    return RedirectResponse(url=flyer.url)


@router.post("/{product_id}/email-flyer")
async def email_product_flyer(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Queue an email task to send the product flyer to the authenticated user."""
    from app.models.product import Product, ProductAsset
    from app.models.user import User

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(
        select(Product)
        .options(selectinload(Product.assets))
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    flyer = next((a for a in product.assets if a.asset_type == "flyer"), None)
    if not flyer:
        raise HTTPException(status_code=404, detail="No flyer available for this product")

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    first_name = getattr(user, "first_name", None) or user.email.split("@")[0]
    from app.services.email_service import EmailService
    svc = EmailService(db)
    svc.send_raw(
        to_email=user.email,
        subject=f"Product Flyer — {product.name}",
        body_html=f"""
        <h2 style="font-family:sans-serif;color:#2A2830">Product Flyer</h2>
        <p>Hi {first_name},</p>
        <p>Here is the flyer for <strong>{product.name}</strong>:</p>
        <p>
          <a href="{flyer.url}" style="background:#1A5CFF;color:#fff;padding:10px 20px;border-radius:6px;
             text-decoration:none;display:inline-block;font-weight:bold">
            View / Download Flyer
          </a>
        </p>
        <p style="color:#7A7880;font-size:13px">AF Apparels Wholesale</p>
        """,
    )
    return {"message": f"Flyer for '{product.name}' sent to {user.email}"}


# ── Product Reviews ────────────────────────────────────────────────────────────

@router.get("/{product_id}/reviews")
async def list_product_reviews(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    from app.models.product import ProductReview
    from sqlalchemy import func

    result = await db.execute(
        select(ProductReview)
        .where(ProductReview.product_id == product_id, ProductReview.is_approved == True)  # noqa: E712
        .order_by(ProductReview.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    reviews = result.scalars().all()

    count_result = await db.execute(
        select(func.count(ProductReview.id))
        .where(ProductReview.product_id == product_id, ProductReview.is_approved == True)  # noqa: E712
    )
    total = count_result.scalar_one()

    avg_result = await db.execute(
        select(func.avg(ProductReview.rating))
        .where(ProductReview.product_id == product_id, ProductReview.is_approved == True)  # noqa: E712
    )
    avg_rating = float(avg_result.scalar_one() or 0)

    from app.schemas.review import ProductReviewOut, ReviewsResponse
    return ReviewsResponse(
        reviews=[ProductReviewOut.model_validate(r) for r in reviews],
        total=total,
        avg_rating=round(avg_rating, 1),
    )


@router.post("/{product_id}/reviews", status_code=201)
async def create_product_review(
    product_id: uuid.UUID,
    payload: ProductReviewCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.models.product import Product, ProductReview
    from app.schemas.review import ProductReviewOut

    product_result = await db.execute(select(Product).where(Product.id == product_id))
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    user_id = getattr(request.state, "user_id", None)

    review = ProductReview(
        product_id=product_id,
        user_id=uuid.UUID(user_id) if user_id else None,
        rating=payload.rating,
        title=payload.title,
        body=payload.body,
        reviewer_name=payload.reviewer_name,
        reviewer_company=payload.reviewer_company,
        is_verified=user_id is not None,
        is_approved=True,
        image_url=payload.image_url,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return ProductReviewOut.model_validate(review)


# ── T202: Bulk asset download ─────────────────────────────────────────────────

@router.post("/bulk-download")
async def bulk_asset_download(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Accept a list of product_ids, queue ZIP generation task, return task_id."""
    import uuid as _uuid

    product_ids: list[str] = payload.get("product_ids", [])
    if not product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided")
    if len(product_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 products per bulk download")

    task_id = str(_uuid.uuid4())

    from app.tasks.inventory_tasks import generate_bulk_asset_zip
    generate_bulk_asset_zip.delay(product_ids, task_id)

    return {"task_id": task_id, "status": "queued", "product_count": len(product_ids)}
