from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.shipping import ShippingTierCreate, ShippingTierOut, ShippingTierUpdate
from app.services.shipping_service import ShippingService

router = APIRouter(prefix="/admin/shipping-tiers", tags=["admin", "shipping"])


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
