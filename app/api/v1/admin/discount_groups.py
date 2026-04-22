from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.discount_group import DiscountGroup, VariantPricingOverride

router = APIRouter(prefix="/admin", tags=["admin", "discount-groups"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class DiscountGroupIn(BaseModel):
    title: str
    customer_tag: str | None = None
    applies_to: str = "store"
    min_req_type: str = "none"
    min_req_value: float | None = None
    shipping_type: str = "store_default"
    shipping_amount: float = 0
    status: str = "enabled"


class VariantPricingIn(BaseModel):
    overrides: dict[str, dict[str, dict[str, str | None]]]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_out(g: DiscountGroup) -> dict:
    return {
        "id": str(g.id),
        "title": g.title,
        "customer_tag": g.customer_tag or "",
        "applies_to": g.applies_to,
        "min_req_type": g.min_req_type,
        "min_req_value": float(g.min_req_value) if g.min_req_value is not None else 0,
        "shipping_type": g.shipping_type,
        "shipping_amount": float(g.shipping_amount) if g.shipping_amount is not None else 0,
        "status": g.status,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


# ── Discount Group CRUD ───────────────────────────────────────────────────────

@router.get("/discount-groups")
async def list_discount_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DiscountGroup).order_by(DiscountGroup.created_at.desc()))
    groups = result.scalars().all()
    return [_group_out(g) for g in groups]


@router.post("/discount-groups", status_code=status.HTTP_201_CREATED)
async def create_discount_group(body: DiscountGroupIn, db: AsyncSession = Depends(get_db)):
    g = DiscountGroup(
        title=body.title,
        customer_tag=body.customer_tag,
        applies_to=body.applies_to,
        min_req_type=body.min_req_type,
        min_req_value=body.min_req_value,
        shipping_type=body.shipping_type,
        shipping_amount=body.shipping_amount,
        status=body.status,
    )
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return _group_out(g)


@router.patch("/discount-groups/{group_id}")
async def update_discount_group(
    group_id: UUID, body: DiscountGroupIn, db: AsyncSession = Depends(get_db)
):
    g = await db.get(DiscountGroup, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(g, field, val)
    await db.commit()
    await db.refresh(g)
    return _group_out(g)


@router.delete("/discount-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discount_group(group_id: UUID, db: AsyncSession = Depends(get_db)):
    g = await db.get(DiscountGroup, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(g)
    await db.commit()


# ── Variant Pricing Overrides ─────────────────────────────────────────────────

@router.get("/variant-pricing")
async def get_variant_pricing(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VariantPricingOverride))
    rows = result.scalars().all()
    out: dict = {}
    for row in rows:
        pid = row.product_id
        tid = row.tier_id
        if pid not in out:
            out[pid] = {}
        out[pid][tid] = {
            "price": str(row.price) if row.price is not None else "",
            "discount": str(row.discount_percent) if row.discount_percent is not None else "",
        }
    return out


@router.post("/variant-pricing")
async def save_variant_pricing(body: VariantPricingIn, db: AsyncSession = Depends(get_db)):
    for product_id, tier_map in body.overrides.items():
        for tier_id, vals in tier_map.items():
            price_str = (vals.get("price") or "").strip()
            disc_str = (vals.get("discount") or "").strip()
            price = float(price_str) if price_str else None
            discount = float(disc_str) if disc_str else None

            result = await db.execute(
                select(VariantPricingOverride).where(
                    and_(
                        VariantPricingOverride.product_id == product_id,
                        VariantPricingOverride.tier_id == tier_id,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if price is None and discount is None:
                if existing:
                    await db.delete(existing)
            elif existing:
                existing.price = price
                existing.discount_percent = discount
            else:
                db.add(VariantPricingOverride(
                    product_id=product_id,
                    tier_id=tier_id,
                    price=price,
                    discount_percent=discount,
                ))

    await db.commit()
    return {"ok": True}
