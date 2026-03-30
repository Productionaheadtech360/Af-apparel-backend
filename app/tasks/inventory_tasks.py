"""Inventory Celery tasks — low-stock detection and bulk asset generation."""
import asyncio
import logging

from app.core.celery import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def check_low_stock_levels() -> dict:
    """Periodic task: scan all variants below low_stock_threshold; log alerts."""
    async def _run():
        from sqlalchemy import func, select
        from app.core.database import AsyncSessionLocal
        from app.models.inventory import InventoryRecord
        from app.models.product import ProductVariant

        async with AsyncSessionLocal() as db:
            # Get per-variant summed quantities
            stock_q = (
                select(
                    InventoryRecord.variant_id,
                    func.coalesce(func.sum(InventoryRecord.quantity), 0).label("total"),
                )
                .group_by(InventoryRecord.variant_id)
                .subquery()
            )
            # Get per-variant minimum low_stock_threshold from inventory records
            threshold_q = (
                select(
                    InventoryRecord.variant_id,
                    func.coalesce(func.min(InventoryRecord.low_stock_threshold), 10).label("threshold"),
                )
                .group_by(InventoryRecord.variant_id)
                .subquery()
            )
            low_stock = await db.execute(
                select(ProductVariant.sku, stock_q.c.total)
                .join(stock_q, ProductVariant.id == stock_q.c.variant_id)
                .join(threshold_q, ProductVariant.id == threshold_q.c.variant_id)
                .where(stock_q.c.total <= threshold_q.c.threshold)
                .where(ProductVariant.status == "active")
            )
            alerts = [{"sku": row.sku, "quantity": int(row.total)} for row in low_stock]

        if alerts:
            logger.warning("Low stock alert: %d variant(s) below threshold: %s", len(alerts), alerts[:5])
        return {"alerts": len(alerts), "items": alerts}

    return asyncio.get_event_loop().run_until_complete(_run())


@celery_app.task(bind=True, max_retries=2)
def generate_bulk_asset_zip(self, product_ids: list[str], task_id: str) -> dict:
    """T203: Collect images/flyers for selected products, ZIP them, upload to S3, return URL."""
    import io
    import uuid
    import zipfile

    import boto3

    async def _fetch_assets():
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.core.database import AsyncSessionLocal
        from app.models.product import Product

        async with AsyncSessionLocal() as db:
            results = []
            for pid in product_ids:
                try:
                    pid_uuid = uuid.UUID(pid)
                except ValueError:
                    continue
                result = await db.execute(
                    select(Product)
                    .options(selectinload(Product.images), selectinload(Product.assets))
                    .where(Product.id == pid_uuid)
                )
                p = result.scalar_one_or_none()
                if p:
                    results.append(p)
            return results

    try:
        from app.core.config import settings

        products = asyncio.get_event_loop().run_until_complete(_fetch_assets())

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        ) if settings.AWS_ACCESS_KEY_ID else None

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for product in products:
                folder = product.slug[:30]

                # Images (large format)
                for i, img in enumerate(product.images):
                    if not s3:
                        continue
                    url = img.url_large
                    key = url.split(".amazonaws.com/", 1)[-1] if "amazonaws.com/" in url else url.lstrip("/")
                    try:
                        obj = s3.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
                        img_bytes = obj["Body"].read()
                        ext = key.rsplit(".", 1)[-1] if "." in key else "jpg"
                        zf.writestr(f"{folder}/images/image_{i + 1:02d}.{ext}", img_bytes)
                    except Exception:
                        pass

                # Flyer PDF
                for asset in product.assets:
                    if asset.asset_type != "flyer" or not s3:
                        continue
                    url = asset.url
                    key = url.split(".amazonaws.com/", 1)[-1] if "amazonaws.com/" in url else url.lstrip("/")
                    try:
                        obj = s3.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
                        zf.writestr(f"{folder}/{asset.file_name}", obj["Body"].read())
                    except Exception:
                        pass

        buf.seek(0)
        zip_bytes = buf.read()

        # Upload ZIP to S3
        download_url = None
        if s3 and zip_bytes:
            zip_key = f"bulk-downloads/{task_id}.zip"
            s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=zip_key,
                Body=zip_bytes,
                ContentType="application/zip",
            )
            download_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_S3_BUCKET, "Key": zip_key},
                ExpiresIn=3600,
            )

        return {"status": "complete", "task_id": task_id, "download_url": download_url}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
