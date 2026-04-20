from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.shipping import ShippingBracket, ShippingTier
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
        tier = ShippingTier(
            name=data.name,
            description=data.description,
            calculation_type=data.calculation_type,
            cutoff_time=data.cutoff_time,
        )
        self.db.add(tier)
        await self.db.flush()

        for bracket_data in data.brackets:
            bracket = ShippingBracket(
                tier_id=tier.id,
                min_units=bracket_data.min_units,
                max_units=bracket_data.max_units,
                min_order_value=bracket_data.min_order_value,
                max_order_value=bracket_data.max_order_value,
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
        if data.calculation_type is not None:
            tier.calculation_type = data.calculation_type
        if data.cutoff_time is not None:
            tier.cutoff_time = data.cutoff_time
        if data.is_active is not None:
            tier.is_active = data.is_active

        if data.brackets is not None:
            await self.db.execute(
                delete(ShippingBracket).where(ShippingBracket.tier_id == tier_id)
            )
            for bracket_data in data.brackets:
                bracket = ShippingBracket(
                    tier_id=tier_id,
                    min_units=bracket_data.min_units,
                    max_units=bracket_data.max_units,
                    min_order_value=bracket_data.min_order_value,
                    max_order_value=bracket_data.max_order_value,
                    cost=bracket_data.cost,
                )
                self.db.add(bracket)

        await self.db.flush()
        await self.db.refresh(tier)
        return tier

    async def delete_tier(self, tier_id: UUID) -> None:
        result = await self.db.execute(
            select(ShippingTier).where(ShippingTier.id == tier_id)
        )
        tier = result.scalar_one_or_none()
        if not tier:
            raise NotFoundError(f"Shipping tier {tier_id} not found")
        await self.db.delete(tier)
        await self.db.flush()

    def calculate_shipping_cost(
        self,
        total_units: int,
        tier: ShippingTier,
        company_override: Decimal | None = None,
        order_subtotal: Decimal = Decimal("0"),
    ) -> Decimal:
        """Return shipping cost based on tier calculation type.
        company_override takes priority if set."""
        if company_override is not None:
            return company_override

        if tier.calculation_type == "free":
            return Decimal("0.00")

        brackets = sorted(tier.brackets, key=lambda b: (
            float(b.min_order_value or 0) if tier.calculation_type == "order_value"
            else b.min_units
        ))

        if tier.calculation_type == "order_value":
            for bracket in reversed(brackets):
                min_val = Decimal(str(bracket.min_order_value or 0))
                max_val = bracket.max_order_value
                if order_subtotal >= min_val:
                    if max_val is None or order_subtotal <= Decimal(str(max_val)):
                        return Decimal(str(bracket.cost))
        else:
            # Default: unit-based
            for bracket in reversed(brackets):
                if total_units >= bracket.min_units:
                    if bracket.max_units is None or total_units <= bracket.max_units:
                        return Decimal(str(bracket.cost))

        # Fallback: cheapest bracket
        if brackets:
            return Decimal(str(brackets[0].cost))
        return Decimal("0.00")

    def get_applicable_bracket(
        self, total_units: int, tier: ShippingTier, order_subtotal: Decimal = Decimal("0")
    ) -> ShippingBracket | None:
        if tier.calculation_type == "free":
            return None

        brackets = sorted(tier.brackets, key=lambda b: (
            float(b.min_order_value or 0) if tier.calculation_type == "order_value"
            else b.min_units
        ))

        if tier.calculation_type == "order_value":
            for bracket in reversed(brackets):
                min_val = Decimal(str(bracket.min_order_value or 0))
                max_val = bracket.max_order_value
                if order_subtotal >= min_val:
                    if max_val is None or order_subtotal <= Decimal(str(max_val)):
                        return bracket
        else:
            for bracket in reversed(brackets):
                if total_units >= bracket.min_units:
                    if bracket.max_units is None or total_units <= bracket.max_units:
                        return bracket

        return brackets[0] if brackets else None
