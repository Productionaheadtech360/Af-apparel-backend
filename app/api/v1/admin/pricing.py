from uuid import UUID

from fastapi import APIRouter, Depends, status
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
    return tier


@router.patch("/{tier_id}", response_model=PricingTierOut)
async def update_pricing_tier(
    tier_id: UUID, payload: PricingTierUpdate, db: AsyncSession = Depends(get_db)
):
    svc = PricingService(db)
    tier = await svc.update_tier(tier_id, payload)
    await db.commit()
    return tier
