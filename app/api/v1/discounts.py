"""Public discount code validation and application endpoints."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.discount import DiscountCode, DiscountUsage
from app.schemas.discount import (
    ApplyDiscountRequest,
    ValidateDiscountRequest,
    ValidateDiscountResponse,
)

router = APIRouter(prefix="/discounts", tags=["discounts"])


def compute_discount_amount(dc: DiscountCode, cart_total: float) -> float:
    if dc.discount_type == "free_shipping":
        return 0.0
    if dc.discount_type == "percentage":
        return round(cart_total * float(dc.discount_value) / 100, 2)
    return min(float(dc.discount_value), cart_total)


async def validate_discount_code(
    code: str,
    cart_total: float,
    user_id: UUID | None,
    customer_type: str,
    db: AsyncSession,
) -> tuple["DiscountCode | None", str]:
    result = await db.execute(
        select(DiscountCode).where(func.lower(DiscountCode.code) == code.strip().lower())
    )
    dc = result.scalar_one_or_none()
    if not dc:
        return None, "Discount code not found."
    if not dc.is_active:
        return None, "This discount code is no longer active."

    now = datetime.now(timezone.utc)
    if dc.starts_at and dc.starts_at > now:
        return None, "This discount code is not yet valid."
    if dc.expires_at and dc.expires_at < now:
        return None, "This discount code has expired."

    if dc.minimum_order_amount and cart_total < float(dc.minimum_order_amount):
        return None, f"Minimum order of ${dc.minimum_order_amount:.2f} required."

    if dc.customer_eligibility != "all" and dc.customer_eligibility != customer_type:
        return None, "This discount code is not applicable to your account type."

    if dc.usage_limit_total is not None:
        total_used = (await db.execute(
            select(func.count(DiscountUsage.id)).where(DiscountUsage.discount_code_id == dc.id)
        )).scalar_one()
        if total_used >= dc.usage_limit_total:
            return None, "This discount code has reached its usage limit."

    if dc.usage_limit_per_customer is not None and user_id:
        per_user_used = (await db.execute(
            select(func.count(DiscountUsage.id)).where(
                DiscountUsage.discount_code_id == dc.id,
                DiscountUsage.user_id == user_id,
            )
        )).scalar_one()
        if per_user_used >= dc.usage_limit_per_customer:
            return None, "You have already used this discount code the maximum number of times."

    return dc, ""


@router.post("/validate", response_model=ValidateDiscountResponse)
async def validate_discount(
    payload: ValidateDiscountRequest,
    db: AsyncSession = Depends(get_db),
) -> ValidateDiscountResponse:
    dc, error = await validate_discount_code(
        payload.code,
        float(payload.cart_total),
        payload.user_id,
        payload.customer_type,
        db,
    )
    if error:
        return ValidateDiscountResponse(valid=False, message=error)

    discount_amount = compute_discount_amount(dc, float(payload.cart_total))
    final_total = max(0.0, float(payload.cart_total) - discount_amount)

    return ValidateDiscountResponse(
        valid=True,
        message="Discount applied successfully!",
        discount_type=dc.discount_type,
        discount_value=dc.discount_value,
        discount_amount=round(Decimal(str(discount_amount)), 2),
        final_total=round(Decimal(str(final_total)), 2),
        code=dc.code,
        discount_code_id=dc.id,
    )


@router.post("/apply")
async def apply_discount(
    payload: ApplyDiscountRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    dc, error = await validate_discount_code(
        payload.code,
        float(payload.cart_total),
        payload.user_id,
        payload.customer_type,
        db,
    )
    if error:
        return {"success": False, "message": error}

    discount_amount = compute_discount_amount(dc, float(payload.cart_total))
    final_total = max(0.0, float(payload.cart_total) - discount_amount)

    usage = DiscountUsage(
        discount_code_id=dc.id,
        order_id=payload.order_id,
        user_id=payload.user_id,
        discount_amount_applied=Decimal(str(discount_amount)),
    )
    db.add(usage)
    await db.commit()

    return {
        "success": True,
        "discount_amount": discount_amount,
        "final_total": final_total,
    }
