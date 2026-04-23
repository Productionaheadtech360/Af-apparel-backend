"""Admin discount code management (CRUD + usage history)."""
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.discount import DiscountCode, DiscountUsage
from app.schemas.discount import DiscountCodeCreate, DiscountCodeUpdate

router = APIRouter(prefix="/admin/discounts", tags=["admin", "discounts"])


def _code_out(dc: DiscountCode, usage_count: int = 0) -> dict:
    try:
        applicable_ids = json.loads(dc.applicable_ids) if dc.applicable_ids else []
    except Exception:
        applicable_ids = []
    return {
        "id": str(dc.id),
        "code": dc.code,
        "discount_type": dc.discount_type,
        "discount_value": float(dc.discount_value),
        "minimum_order_amount": float(dc.minimum_order_amount) if dc.minimum_order_amount is not None else None,
        "usage_limit_total": dc.usage_limit_total,
        "usage_limit_per_customer": dc.usage_limit_per_customer,
        "applicable_to": dc.applicable_to,
        "applicable_ids": applicable_ids,
        "customer_eligibility": dc.customer_eligibility,
        "starts_at": dc.starts_at.isoformat() if dc.starts_at else None,
        "expires_at": dc.expires_at.isoformat() if dc.expires_at else None,
        "is_active": dc.is_active,
        "created_at": dc.created_at.isoformat(),
        "updated_at": dc.updated_at.isoformat(),
        "usage_count": usage_count,
    }


@router.get("")
async def list_discounts(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    filters = []
    if q:
        filters.append(DiscountCode.code.ilike(f"%{q}%"))

    count_q = select(func.count(DiscountCode.id))
    if filters:
        count_q = count_q.where(*filters)
    total = (await db.execute(count_q)).scalar_one()

    query = select(DiscountCode)
    if filters:
        query = query.where(*filters)
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(DiscountCode.created_at.desc())
    rows = (await db.execute(query)).scalars().all()

    usage_map: dict = {}
    if rows:
        ids = [r.id for r in rows]
        usage_result = await db.execute(
            select(DiscountUsage.discount_code_id, func.count(DiscountUsage.id).label("cnt"))
            .where(DiscountUsage.discount_code_id.in_(ids))
            .group_by(DiscountUsage.discount_code_id)
        )
        usage_map = {row[0]: row[1] for row in usage_result.all()}

    items = [_code_out(r, usage_map.get(r.id, 0)) for r in rows]
    pages = (total + page_size - 1) // page_size
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_discount(
    payload: DiscountCodeCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = (await db.execute(
        select(DiscountCode).where(func.lower(DiscountCode.code) == payload.code.strip().lower())
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A discount code with this code already exists.")

    dc = DiscountCode(
        code=payload.code.strip().upper(),
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        minimum_order_amount=payload.minimum_order_amount,
        usage_limit_total=payload.usage_limit_total,
        usage_limit_per_customer=payload.usage_limit_per_customer,
        applicable_to=payload.applicable_to,
        applicable_ids=json.dumps(payload.applicable_ids) if payload.applicable_ids else None,
        customer_eligibility=payload.customer_eligibility,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
        is_active=payload.is_active,
    )
    db.add(dc)
    await db.commit()
    await db.refresh(dc)
    return _code_out(dc, 0)


@router.put("/{discount_id}")
async def update_discount(
    discount_id: UUID,
    payload: DiscountCodeUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    dc = (await db.execute(
        select(DiscountCode).where(DiscountCode.id == discount_id)
    )).scalar_one_or_none()
    if not dc:
        raise HTTPException(status_code=404, detail="Discount code not found.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "applicable_ids":
            setattr(dc, "applicable_ids", json.dumps(value) if value else None)
        else:
            setattr(dc, field, value)

    await db.commit()
    await db.refresh(dc)

    usage_count = (await db.execute(
        select(func.count(DiscountUsage.id)).where(DiscountUsage.discount_code_id == dc.id)
    )).scalar_one()
    return _code_out(dc, usage_count)


@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discount(
    discount_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    dc = (await db.execute(
        select(DiscountCode).where(DiscountCode.id == discount_id)
    )).scalar_one_or_none()
    if not dc:
        raise HTTPException(status_code=404, detail="Discount code not found.")
    dc.is_active = False
    await db.commit()


@router.get("/{discount_id}/usage")
async def get_discount_usage(
    discount_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    dc = (await db.execute(
        select(DiscountCode).where(DiscountCode.id == discount_id)
    )).scalar_one_or_none()
    if not dc:
        raise HTTPException(status_code=404, detail="Discount code not found.")

    total = (await db.execute(
        select(func.count(DiscountUsage.id)).where(DiscountUsage.discount_code_id == discount_id)
    )).scalar_one()

    usages = (await db.execute(
        select(DiscountUsage)
        .where(DiscountUsage.discount_code_id == discount_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .order_by(DiscountUsage.used_at.desc())
    )).scalars().all()

    items = [{
        "id": str(u.id),
        "order_id": str(u.order_id) if u.order_id else None,
        "user_id": str(u.user_id) if u.user_id else None,
        "used_at": u.used_at.isoformat() if u.used_at else None,
        "discount_amount_applied": float(u.discount_amount_applied),
    } for u in usages]

    pages = (total + page_size - 1) // page_size
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}
