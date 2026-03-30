"""Cart Celery tasks — T208: abandoned cart detection."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from app.core.celery import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def detect_abandoned_carts() -> dict:
    """T208: Periodic task — snapshot company carts inactive >24h to abandoned_carts.

    Algorithm:
    1. Find all companies with cart_items not updated in >24h
    2. For each company, skip if an unrecovered AbandonedCart already exists
    3. Serialize cart items (with product/variant info) as JSON snapshot
    4. Insert AbandonedCart record
    5. Return counts
    """

    async def _run() -> dict:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.core.database import AsyncSessionLocal
        from app.models.order import AbandonedCart, CartItem
        from app.models.product import Product, ProductVariant

        threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        async with AsyncSessionLocal() as db:
            # Find companies with stale cart items
            stale_q = (
                select(CartItem.company_id)
                .where(CartItem.updated_at <= threshold)
                .distinct()
            )
            company_ids = [r[0] for r in (await db.execute(stale_q)).all()]

            created = 0
            for company_id in company_ids:
                # Skip if already have an unrecovered snapshot for this company
                existing = (await db.execute(
                    select(AbandonedCart).where(
                        AbandonedCart.company_id == company_id,
                        AbandonedCart.is_recovered.is_(False),
                    ).limit(1)
                )).scalar_one_or_none()
                if existing:
                    continue

                # Load stale cart items with variants
                items = (await db.execute(
                    select(CartItem)
                    .options(selectinload(CartItem.variant))
                    .where(
                        CartItem.company_id == company_id,
                        CartItem.updated_at <= threshold,
                    )
                )).scalars().all()
                if not items:
                    continue

                # Build snapshot with product names
                snapshot = []
                total = 0.0
                for item in items:
                    variant = item.variant
                    product_name = "Unknown"
                    if variant:
                        product = (await db.execute(
                            select(Product).where(Product.id == variant.product_id)
                        )).scalar_one_or_none()
                        if product:
                            product_name = product.name

                    unit_price = float(item.unit_price or 0)
                    line_total = unit_price * item.quantity
                    total += line_total

                    snapshot.append({
                        "variant_id": str(item.variant_id),
                        "product_name": product_name,
                        "sku": variant.sku if variant else "",
                        "color": variant.color if variant else "",
                        "size": variant.size if variant else "",
                        "quantity": item.quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    })

                db.add(AbandonedCart(
                    company_id=company_id,
                    items_snapshot=json.dumps(snapshot),
                    total=round(total, 2),
                    item_count=sum(i.quantity for i in items),
                    abandoned_at=datetime.now(timezone.utc).isoformat(),
                ))
                created += 1

            await db.commit()

        logger.info("Abandoned cart detection: %d new snapshots", created)
        return {"created": created, "checked": len(company_ids)}

    return asyncio.get_event_loop().run_until_complete(_run())
