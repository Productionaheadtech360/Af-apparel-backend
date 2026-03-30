from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.shipping import ShippingTier, ShippingBracket
from app.schemas.shipping import ShippingTierCreate, ShippingTierUpdate


class ShippingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tier_by_id(self, tier_id: UUID) -> ShippingTier:
        result = await self.db.execute(
            select(ShippingTier)
            .options(selectinload(ShippingTier.brackets))
            .where(ShippingTier.id == tier_id)
        )
        tier = result.scalar_one_or_none()
        if not tier:
            raise NotFoundError(f"Shipping tier {tier_id} not found")
        return tier

    async def list_tiers(self) -> list[ShippingTier]:
        result = await self.db.execute(
            select(ShippingTier)
            .options(selectinload(ShippingTier.brackets))
            .order_by(ShippingTier.name)
        )
        return list(result.scalars().all())

    async def create_tier(self, data: ShippingTierCreate) -> ShippingTier:
        tier = ShippingTier(name=data.name, description=data.description)
        self.db.add(tier)
        await self.db.flush()

        for bracket_data in data.brackets:
            bracket = ShippingBracket(
                shipping_tier_id=tier.id,
                min_units=bracket_data.min_units,
                max_units=bracket_data.max_units,
                cost=bracket_data.cost,
            )
            self.db.add(bracket)

        await self.db.flush()
        await self.db.refresh(tier)
        return tier

    async def update_tier(self, tier_id: UUID, data: ShippingTierUpdate) -> ShippingTier:
        tier = await self.get_tier_by_id(tier_id)

        if data.name is not None:
            tier.name = data.name
        if data.description is not None:
            tier.description = data.description

        if data.brackets is not None:
            # Replace all brackets
            await self.db.execute(
                ShippingBracket.__table__.delete().where(
                    ShippingBracket.shipping_tier_id == tier_id
                )
            )
            for bracket_data in data.brackets:
                bracket = ShippingBracket(
                    shipping_tier_id=tier_id,
                    min_units=bracket_data.min_units,
                    max_units=bracket_data.max_units,
                    cost=bracket_data.cost,
                )
                self.db.add(bracket)

        await self.db.flush()
        await self.db.refresh(tier)
        return tier

    def calculate_shipping_cost(
        self,
        total_units: int,
        tier: ShippingTier,
        company_override: Decimal | None = None,
    ) -> Decimal:
        """Return shipping cost for given unit count.
        Uses company_override (fixed amount) if set, otherwise bracket lookup."""
        if company_override is not None:
            return company_override

        brackets = sorted(tier.brackets, key=lambda b: b.min_units)
        for bracket in reversed(brackets):
            if total_units >= bracket.min_units:
                if bracket.max_units is None or total_units <= bracket.max_units:
                    return bracket.cost

        # Fallback: use lowest bracket cost
        if brackets:
            return brackets[0].cost
        return Decimal("0.00")

    def get_applicable_bracket(
        self, total_units: int, tier: ShippingTier
    ) -> ShippingBracket | None:
        brackets = sorted(tier.brackets, key=lambda b: b.min_units)
        for bracket in reversed(brackets):
            if total_units >= bracket.min_units:
                if bracket.max_units is None or total_units <= bracket.max_units:
                    return bracket
        return brackets[0] if brackets else None
