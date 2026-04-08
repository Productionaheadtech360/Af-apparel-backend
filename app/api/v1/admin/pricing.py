from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.pricing import PricingTier
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/admin/pricing-tiers", tags=["admin", "pricing"])

# Fields added by migration b3c4d5e6f7a8. We read them with getattr() so the
# endpoint degrades gracefully if the migration hasn't run yet on this env.
_EXTENDED = [
    "moq", "free_shipping", "shipping_discount_percentage",
    "tax_exempt", "tax_percentage", "payment_terms",
    "credit_limit", "priority_support", "volume_breaks",
]

_DEFAULTS: dict = {
    "moq": 0,
    "free_shipping": False,
    "shipping_discount_percentage": 0,
    "tax_exempt": False,
    "tax_percentage": 0,
    "payment_terms": "immediate",
    "credit_limit": 0,
    "priority_support": False,
    "volume_breaks": [],
}


def _tier_dict(t: PricingTier, customer_count: int = 0) -> dict:
    """Serialize a PricingTier ORM object to a plain dict safely."""
    # discount_percent is the canonical DB column; expose as discount_percentage
    disc = float(getattr(t, "discount_percent", 0) or 0)
    d: dict = {
        "id": str(t.id),
        "name": t.name,
        "description": getattr(t, "description", None),
        "discount_percent": disc,
        "discount_percentage": disc,
        "is_active": getattr(t, "is_active", True),
        "customer_count": customer_count,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
    for field in _EXTENDED:
        d[field] = getattr(t, field, _DEFAULTS[field]) or _DEFAULTS[field]
    return d


@router.get("")
async def list_pricing_tiers(db: AsyncSession = Depends(get_db)):
    try:
        svc = PricingService(db)
        rows = await svc.list_tiers()   # already returns list[dict] with customer_count
        # Normalise: ensure discount_percentage alias and extended field defaults
        out = []
        for r in rows:
            disc = float(r.get("discount_percent", 0) or r.get("discount_percentage", 0) or 0)
            entry: dict = {
                "id": str(r["id"]),
                "name": r["name"],
                "description": r.get("description"),
                "discount_percent": disc,
                "discount_percentage": disc,
                "is_active": r.get("is_active", True),
                "customer_count": r.get("customer_count", 0),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
            for field in _EXTENDED:
                entry[field] = r.get(field) or _DEFAULTS[field]
            out.append(entry)
        return out
    except Exception as exc:
        # Migration may not have run yet — return minimal safe list
        print(f"[pricing-tiers] list failed ({exc}), falling back to basic query")
        try:
            result = await db.execute(
                select(PricingTier.id, PricingTier.name, PricingTier.description,
                       PricingTier.discount_percent, PricingTier.is_active,
                       PricingTier.created_at, PricingTier.updated_at)
                .order_by(PricingTier.name)
            )
            rows_basic = result.all()
            return [
                {
                    "id": str(r.id), "name": r.name, "description": r.description,
                    "discount_percent": float(r.discount_percent or 0),
                    "discount_percentage": float(r.discount_percent or 0),
                    "is_active": r.is_active, "customer_count": 0,
                    "created_at": r.created_at, "updated_at": r.updated_at,
                    **{f: _DEFAULTS[f] for f in _EXTENDED},
                }
                for r in rows_basic
            ]
        except Exception as exc2:
            print(f"[pricing-tiers] basic fallback also failed: {exc2}")
            return []


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_pricing_tier(payload: dict, db: AsyncSession = Depends(get_db)):
    tier = PricingTier(
        id=uuid4(),
        name=payload.get("name", ""),
        description=payload.get("description"),
        discount_percent=payload.get("discount_percent", payload.get("discount_percentage", 0)),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    for field in _EXTENDED:
        if hasattr(tier, field) and field in payload:
            setattr(tier, field, payload[field])
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    return _tier_dict(tier, customer_count=0)


@router.patch("/{tier_id}")
async def update_pricing_tier(tier_id: UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    tier = await db.get(PricingTier, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")
    # Handle discount field name variants from frontend
    if "discount_percentage" in payload and "discount_percent" not in payload:
        payload["discount_percent"] = payload.pop("discount_percentage")
    for field, value in payload.items():
        if hasattr(tier, field):
            setattr(tier, field, value)
    tier.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tier)
    return _tier_dict(tier, customer_count=0)


@router.delete("/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pricing_tier(tier_id: UUID, db: AsyncSession = Depends(get_db)):
    tier = await db.get(PricingTier, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")
    await db.delete(tier)
    await db.commit()
