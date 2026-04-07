"""Admin products router — full product catalog management with image processing."""
import io
import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.product import Category, Product, ProductCategory, ProductImage, ProductVariant
from app.schemas.product import (
    BulkActionRequest,
    BulkGenerateRequest,
    ImageUploadResponse,
    ImportResult,
    ProductCreate,
    ProductDetail,
    ProductListItem,
    ProductUpdate,
    VariantCreate,
    VariantOut,
)
from app.services.product_service import ProductService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/products", tags=["admin", "products"])


@router.get("", response_model=list[ProductDetail])
async def list_admin_products(
    q: str | None = None,
    status: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    svc = ProductService(db)  # noqa: F841
    from sqlalchemy.orm import selectinload
    from app.models.inventory import InventoryRecord

    query = select(Product).options(
        selectinload(Product.variants).selectinload(ProductVariant.inventory_records),
        selectinload(Product.images),
        selectinload(Product.category_links)
        .selectinload(ProductCategory.category)
        .selectinload(Category.children),
    )
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))
    if status:
        query = query.where(Product.status == status)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    products = result.scalars().all()

    # Populate stock_quantity on each variant from inventory records
    for product in products:
        for variant in product.variants:
            variant.stock_quantity = sum(
                rec.quantity for rec in variant.inventory_records if rec.quantity > 0
            )

    return products


@router.post("", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    svc = ProductService(db)
    product = await svc.create_product(payload)
    await db.commit()
    return product


@router.patch("/{product_id}", response_model=ProductDetail)
async def update_product(
    product_id: UUID, payload: ProductUpdate, db: AsyncSession = Depends(get_db)
):
    svc = ProductService(db)
    product = await svc.update_product(product_id, payload)
    await db.commit()
    return product


@router.post("/{product_id}/images", response_model=ImageUploadResponse)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
    alt_text: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Process image upload: resize to 3 sizes, convert to WebP, upload to S3."""
    # Verify product exists
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(f"Product {product_id} not found")

    content = await file.read()
    urls = await _process_and_upload_image(content, product_id, file.filename or "image")

    # Determine position
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count()).where(ProductImage.product_id == product_id)
    )
    position = count_result.scalar_one()

    image = ProductImage(
        product_id=product_id,
        url_thumbnail=urls["thumbnail"],
        url_medium=urls["medium"],
        url_large=urls["large"],
        url_thumbnail_webp=urls["thumbnail_webp"],
        url_medium_webp=urls["medium_webp"],
        url_large_webp=urls["large_webp"],
        alt_text=alt_text,
        is_primary=position == 0,
        position=position,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    return ImageUploadResponse(
        id=image.id,
        url_thumbnail=image.url_thumbnail,
        url_medium=image.url_medium,
        url_large=image.url_large,
    )


@router.patch("/{product_id}/images/reorder")
async def reorder_product_images(
    product_id: UUID,
    image_ids: list[UUID] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Reorder images by providing ordered list of image IDs."""
    for position, image_id in enumerate(image_ids):
        result = await db.execute(
            select(ProductImage).where(
                ProductImage.id == image_id,
                ProductImage.product_id == product_id,
            )
        )
        image = result.scalar_one_or_none()
        if image:
            image.position = position
            image.is_primary = position == 0

    await db.commit()
    return {"reordered": len(image_ids)}


@router.post("/{product_id}/variants", response_model=VariantOut, status_code=201)
async def add_variant(
    product_id: UUID,
    payload: VariantCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a single variant to a product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(f"Product {product_id} not found")

    variant = ProductVariant(
        product_id=product_id,
        sku=payload.sku,
        color=payload.color,
        size=payload.size,
        retail_price=payload.retail_price,
        compare_price=payload.compare_price,
        status=payload.status,
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    variant.stock_quantity = 0
    return variant


@router.post("/{product_id}/variants/bulk-generate")
async def bulk_generate_variants(
    product_id: UUID, payload: BulkGenerateRequest, db: AsyncSession = Depends(get_db)
):
    svc = ProductService(db)
    variants = await svc.bulk_generate_variants(
        product_id, payload.colors, payload.sizes, payload.base_retail_price
    )
    await db.commit()
    return {"generated": len(variants), "variants": [{"id": str(v.id), "sku": v.sku} for v in variants]}


@router.patch("/{product_id}/variants/{variant_id}")
async def update_variant(
    product_id: UUID,
    variant_id: UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
        )
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise NotFoundError("Variant not found")

    for field, value in payload.items():
        if hasattr(variant, field):
            setattr(variant, field, value)

    await db.commit()
    return {"id": str(variant.id), "sku": variant.sku}


@router.post("/categories", status_code=201)
async def create_category(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.product import CategoryOut as _CategoryOut

    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")

    slug = payload.get("slug") or name.lower().replace(" ", "-")
    cat = Category(name=name, slug=slug, description=payload.get("description"))
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": str(cat.id), "name": cat.name, "slug": cat.slug, "description": cat.description, "is_active": cat.is_active}


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise NotFoundError("Category not found")
    for field in ("name", "slug", "description", "is_active"):
        if field in payload:
            setattr(cat, field, payload[field])
    await db.commit()
    await db.refresh(cat)
    return {"id": str(cat.id), "name": cat.name, "slug": cat.slug, "description": cat.description, "is_active": cat.is_active}


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise NotFoundError("Category not found")
    await db.delete(cat)
    await db.commit()


@router.post("/bulk-action")
async def bulk_action(payload: BulkActionRequest, db: AsyncSession = Depends(get_db)):
    svc = ProductService(db)
    count = await svc.apply_bulk_action(payload.ids, payload.action)
    await db.commit()
    return {"affected": count, "action": payload.action}


@router.post("/import-csv", response_model=ImportResult)
async def import_products_csv(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    svc = ProductService(db)
    result = await svc.import_from_csv(content.decode("utf-8"))
    await db.commit()
    return ImportResult(**result)


@router.get("/export-csv")
async def export_products_csv(db: AsyncSession = Depends(get_db)):
    svc = ProductService(db)
    csv_content = await svc.export_to_csv()
    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products_export.csv"},
    )


@router.get("/{slug}", response_model=ProductDetail)
async def get_admin_product(slug: str, db: AsyncSession = Depends(get_db)):
    """Fetch single product by slug (or UUID string). Defined after /export-csv to avoid conflict."""
    from sqlalchemy.orm import selectinload
    import uuid as _uuid

    try:
        uid = _uuid.UUID(slug)
        query = select(Product).where(Product.id == uid)
    except ValueError:
        query = select(Product).where(Product.slug == slug)

    query = query.options(
        selectinload(Product.variants).selectinload(ProductVariant.inventory_records),
        selectinload(Product.images),
        selectinload(Product.category_links)
        .selectinload(ProductCategory.category)
        .selectinload(Category.children),
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(f"Product '{slug}' not found")

    for variant in product.variants:
        variant.stock_quantity = sum(
            rec.quantity for rec in variant.inventory_records if rec.quantity > 0
        )

    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(f"Product {product_id} not found")
    await db.delete(product)
    await db.commit()


@router.delete("/{product_id}/images/{image_id}", status_code=204)
async def delete_product_image(
    product_id: UUID, image_id: UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise NotFoundError("Image not found")
    await db.delete(image)
    await db.commit()


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
async def delete_product_variant(
    product_id: UUID, variant_id: UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.id == variant_id, ProductVariant.product_id == product_id
        )
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise NotFoundError("Variant not found")
    variant.status = "discontinued"
    await db.commit()


# ---------------------------------------------------------------------------
# Image processing helper
# ---------------------------------------------------------------------------

async def _process_and_upload_image(
    content: bytes, product_id: UUID, filename: str
) -> dict:
    """Resize to 150/400/800px + WebP. Uploads to S3 if configured, else saves locally."""
    from PIL import Image as PILImage
    import io as _io
    import os
    from app.core.config import get_settings

    settings = get_settings()
    use_s3 = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)

    img = PILImage.open(_io.BytesIO(content)).convert("RGB")
    sizes = {"thumbnail": 150, "medium": 400, "large": 800}
    urls: dict[str, str] = {}

    base_name = filename.rsplit(".", 1)[0]
    base_key = f"products/{product_id}/{base_name}"

    if use_s3:
        import boto3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        )
        bucket = settings.AWS_S3_BUCKET
        cdn = settings.CDN_BASE_URL.rstrip("/") if settings.CDN_BASE_URL else f"https://{bucket}.s3.amazonaws.com"
    else:
        local_dir = f"/app/media/products/{product_id}"
        os.makedirs(local_dir, exist_ok=True)

    for size_name, px in sizes.items():
        resized = img.copy()
        resized.thumbnail((px, px), PILImage.LANCZOS)

        if use_s3:
            jpeg_buf = _io.BytesIO()
            resized.save(jpeg_buf, "JPEG", quality=85, optimize=True)
            jpeg_key = f"{base_key}_{size_name}.jpg"
            s3.put_object(Bucket=bucket, Key=jpeg_key, Body=jpeg_buf.getvalue(), ContentType="image/jpeg")
            urls[size_name] = f"{cdn}/{jpeg_key}"

            webp_buf = _io.BytesIO()
            resized.save(webp_buf, "WEBP", quality=85)
            webp_key = f"{base_key}_{size_name}.webp"
            s3.put_object(Bucket=bucket, Key=webp_key, Body=webp_buf.getvalue(), ContentType="image/webp")
            urls[f"{size_name}_webp"] = f"{cdn}/{webp_key}"
        else:
            jpeg_path = f"/app/media/{base_key}_{size_name}.jpg"
            resized.save(jpeg_path, "JPEG", quality=85, optimize=True)
            urls[size_name] = f"/media/{base_key}_{size_name}.jpg"

            webp_path = f"/app/media/{base_key}_{size_name}.webp"
            resized.save(webp_path, "WEBP", quality=85)
            urls[f"{size_name}_webp"] = f"/media/{base_key}_{size_name}.webp"

    return urls
