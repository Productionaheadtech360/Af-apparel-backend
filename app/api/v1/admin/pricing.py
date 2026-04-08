from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.pricing import PricingTierCreate, PricingTierOut, PricingTierUpdate
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/admin/pricing-tiers", tags=["admin", "pricing"])


@router.get("", response_model=list[PricingTierOut])
async def list_pricing_tiers(db: AsyncSession = Depends(get_db)):
    svc = PricingService(db)
    return await svc.list_tiers()


@router.post("", response_model=PricingTierOut, status_code=status.HTTP_201_CREATED)
async def create_pricing_tier(
    payload: PricingTierCreate, db: AsyncSession = Depends(get_db)
):
    svc = PricingService(db)
    tier = await svc.create_tier(payload)
    await db.commit()
    await db.refresh(tier)
    return {"customer_count": 0, **tier.__dict__}


@router.patch("/{tier_id}", response_model=PricingTierOut)
async def update_pricing_tier(
    tier_id: UUID, payload: PricingTierUpdate, db: AsyncSession = Depends(get_db)
):
    svc = PricingService(db)
    tier = await svc.update_tier(tier_id, payload)
    await db.commit()
    await db.refresh(tier)
    # Re-fetch with customer count
    tiers = await svc.list_tiers()
    match = next((t for t in tiers if str(t["id"]) == str(tier_id)), None)
    if not match:
        raise HTTPException(status_code=404, detail="Tier not found")
    return match


@router.delete("/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pricing_tier(
    tier_id: UUID, db: AsyncSession = Depends(get_db)
):
    svc = PricingService(db)
    await svc.delete_tier(tier_id)
    await db.commit()
