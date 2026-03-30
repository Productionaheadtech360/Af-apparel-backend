from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_delete, redis_get, redis_set
from app.core.exceptions import NotFoundError
from app.models.pricing import PricingTier
from app.schemas.pricing import PricingTierCreate, PricingTierUpdate

_CACHE_PREFIX = "pricing_tier:"
_CACHE_TTL = 3600  # 1 hour


class PricingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tier_by_id(self, tier_id: UUID) -> PricingTier:
        cached = await redis_get(f"{_CACHE_PREFIX}{tier_id}")
        if cached:
            # Return ORM-like namedtuple from cache is complex; fetch from DB with cache skip
            pass

        result = await self.db.execute(
            select(PricingTier).where(PricingTier.id == tier_id)
        )
        tier = result.scalar_one_or_none()
        if not tier:
            raise NotFoundError(f"Pricing tier {tier_id} not found")
        return tier

    async def list_tiers(self) -> list[PricingTier]:
        result = await self.db.execute(
            select(PricingTier).order_by(PricingTier.discount_percent)
        )
        return list(result.scalars().all())

    async def create_tier(self, data: PricingTierCreate) -> PricingTier:
        tier = PricingTier(
            name=data.name,
            discount_percent=data.discount_percent,
            description=data.description,
        )
        self.db.add(tier)
        await self.db.flush()
        await self.db.refresh(tier)
        await self.invalidate_tier_cache(tier.id)
        return tier

    async def update_tier(self, tier_id: UUID, data: PricingTierUpdate) -> PricingTier:
        tier = await self.get_tier_by_id(tier_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tier, field, value)
        await self.db.flush()
        await self.db.refresh(tier)
        await self.invalidate_tier_cache(tier_id)
        return tier

    async def invalidate_tier_cache(self, tier_id: UUID) -> None:
        await redis_delete(f"{_CACHE_PREFIX}{tier_id}")

    def calculate_effective_price(
        self, retail_price: Decimal, discount_percent: Decimal
    ) -> Decimal:
        """Apply tier discount to retail price, rounded to 2 decimal places."""
        if discount_percent <= 0:
            return retail_price
        multiplier = Decimal("1") - (discount_percent / Decimal("100"))
        effective = retail_price * multiplier
        return effective.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def apply_tier_to_product_list(
        self, products: list[dict], discount_percent: Decimal
    ) -> list[dict]:
        """Attach effective_price to each product variant dict in-place."""
        for product in products:
            for variant in product.get("variants", []):
                retail = Decimal(str(variant.get("retail_price", "0")))
                variant["effective_price"] = str(
                    self.calculate_effective_price(retail, discount_percent)
                )
        return products
