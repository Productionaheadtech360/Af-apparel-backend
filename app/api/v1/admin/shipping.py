from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.shipping import ShippingTierCreate, ShippingTierOut, ShippingTierUpdate
from app.services.shipping_service import ShippingService

router = APIRouter(prefix="/admin/shipping-tiers", tags=["admin", "shipping"])

# ─── Default tiers (seeded on demand) ────────────────────────────────────────

DEFAULT_TIERS: list[dict] = [
    {
        "name": "Tier 1 — Standard Ground",
        "description": "Default unit-based shipping. Covers most orders.",
        "calculation_type": "units",
        "cutoff_time": "12PM",
        "brackets": [
            {"min_units": 1,    "max_units": 200,  "cost": "20.00"},
            {"min_units": 201,  "max_units": 500,  "cost": "30.00"},
            {"min_units": 501,  "max_units": 1000, "cost": "45.00"},
            {"min_units": 1001, "max_units": None,  "cost": "65.00"},
        ],
    },
    {
        "name": "Tier 2 — Economy",
        "description": "Budget shipping for smaller accounts.",
        "calculation_type": "units",
        "cutoff_time": "12PM",
        "brackets": [
            {"min_units": 1,   "max_units": 100,  "cost": "15.00"},
            {"min_units": 101, "max_units": 300,  "cost": "22.00"},
            {"min_units": 301, "max_units": 600,  "cost": "35.00"},
            {"min_units": 601, "max_units": None,  "cost": "48.00"},
        ],
    },
    {
        "name": "Tier 3 — Value (Order Total)",
        "description": "Shipping cost based on order dollar value. Orders over $200 ship free.",
        "calculation_type": "order_value",
        "cutoff_time": "12PM",
        "brackets": [
            {"min_order_value": "1.00",   "max_order_value": "50.00",  "cost": "20.00"},
            {"min_order_value": "50.01",  "max_order_value": "100.00", "cost": "25.00"},
            {"min_order_value": "100.01", "max_order_value": "199.99", "cost": "35.00"},
            {"min_order_value": "200.00", "max_order_value": None,      "cost": "0.00"},
        ],
    },
    {
        "name": "Tier 4 — Premium",
        "description": "Reduced flat rates for high-volume preferred accounts.",
        "calculation_type": "units",
        "cutoff_time": "12PM",
        "brackets": [
            {"min_units": 1,    "max_units": 500,  "cost": "15.00"},
            {"min_units": 501,  "max_units": 1000, "cost": "25.00"},
            {"min_units": 1001, "max_units": None,  "cost": "35.00"},
        ],
    },
    {
        "name": "Tier 5 — Express",
        "description": "Expedited shipping — higher rates for faster delivery.",
        "calculation_type": "units",
        "cutoff_time": "10AM",
        "brackets": [
            {"min_units": 1,   "max_units": 100,  "cost": "35.00"},
            {"min_units": 101, "max_units": 300,  "cost": "55.00"},
            {"min_units": 301, "max_units": 600,  "cost": "75.00"},
            {"min_units": 601, "max_units": None,  "cost": "95.00"},
        ],
    },
    {
        "name": "Tier 6 — Wholesale Plus (Order Total)",
        "description": "Value-based shipping for wholesale plus accounts. Over $500 ships free.",
        "calculation_type": "order_value",
        "cutoff_time": "12PM",
        "brackets": [
            {"min_order_value": "0.01",  "max_order_value": "100.00", "cost": "25.00"},
            {"min_order_value": "100.01","max_order_value": "250.00", "cost": "20.00"},
            {"min_order_value": "250.01","max_order_value": "499.99", "cost": "15.00"},
            {"min_order_value": "500.00","max_order_value": None,      "cost": "0.00"},
        ],
    },
    {
        "name": "Will Call / Pick Up",
        "description": "Customer picks up order from warehouse. No shipping charge.",
        "calculation_type": "free",
        "cutoff_time": "12PM",
        "brackets": [],
    },
]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ShippingTierOut])
async def list_shipping_tiers(db: AsyncSession = Depends(get_db)):
    svc = ShippingService(db)
    return await svc.list_tiers()


@router.post("", response_model=ShippingTierOut, status_code=status.HTTP_201_CREATED)
async def create_shipping_tier(
    payload: ShippingTierCreate, db: AsyncSession = Depends(get_db)
):
    svc = ShippingService(db)
    tier = await svc.create_tier(payload)
    await db.commit()
    return tier


@router.patch("/{tier_id}", response_model=ShippingTierOut)
async def update_shipping_tier(
    tier_id: UUID, payload: ShippingTierUpdate, db: AsyncSession = Depends(get_db)
):
    svc = ShippingService(db)
    tier = await svc.update_tier(tier_id, payload)
    await db.commit()
    return tier


@router.delete("/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipping_tier(
    tier_id: UUID, db: AsyncSession = Depends(get_db)
):
    svc = ShippingService(db)
    await svc.delete_tier(tier_id)
    await db.commit()


@router.post("/seed-defaults", status_code=status.HTTP_201_CREATED)
async def seed_default_tiers(db: AsyncSession = Depends(get_db)):
    """Create the pre-defined default shipping tiers. Skips tiers that already exist by name."""
    svc = ShippingService(db)
    existing = await svc.list_tiers()
    existing_names = {t.name for t in existing}

    created = []
    for tier_def in DEFAULT_TIERS:
        if tier_def["name"] in existing_names:
            continue
        payload = ShippingTierCreate(**tier_def)
        tier = await svc.create_tier(payload)
        created.append(tier.name)

    await db.commit()
    return {"created": created, "skipped": len(DEFAULT_TIERS) - len(created)}
