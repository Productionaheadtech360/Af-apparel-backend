"""Admin — order management and RMA."""
import csv
import io
import json as _json
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.company import Company
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.rma import RMAItem, RMARequest
from app.schemas.order import (
    AdminOrderDetail,
    AdminOrderListItem,
    CancelOrderRequest,
    OrderItemOut,
    OrderStatusUpdate,
    OrderUpdateRequest,
    RMACreate,
    RMAOut,
    RMAUpdateRequest,
)
from app.types.api import PaginatedResponse

router = APIRouter(prefix="/admin", tags=["admin-orders"])


# ---------------------------------------------------------------------------
# Email helper
# ---------------------------------------------------------------------------

async def _send_order_status_email(order: Order, new_status: str, db: AsyncSession) -> None:
    """Send email when order status changes."""
    try:
        from sqlalchemy import select as _select
        from app.models.user import User
        from app.models.company import Company as _Company
        from app.models.company import CompanyUser
        from app.services.email_service import EmailService
        from app.core.config import settings

        user_result = await db.execute(
            _select(User)
            .join(CompanyUser, CompanyUser.user_id == User.id)
            .where(CompanyUser.company_id == order.company_id, CompanyUser.is_active == True)
            .limit(1)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return

        email_svc = EmailService(db)

        if new_status == "shipped":
            await email_svc.send(
                trigger_event="order_shipped",
                to_email=user.email,
                variables={
                    "first_name": user.first_name or "there",
                    "order_number": order.order_number,
                    "courier": order.courier or "Carrier",
                    "tracking_number": order.tracking_number or "N/A",
                },
            )
            if settings.ADMIN_NOTIFICATION_EMAIL:
                email_svc.send_raw(
                    to_email=settings.ADMIN_NOTIFICATION_EMAIL,
                    subject=f"Order Shipped — {order.order_number}",
                    body_html=f"<p>Order <b>{order.order_number}</b> marked as shipped. Tracking: {order.tracking_number or 'N/A'}</p>",
                )

        elif new_status == "cancelled":
            email_svc.send_raw(
                to_email=user.email,
                subject=f"Order {order.order_number} Cancelled",
                body_html=f"""
                    <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
                    <div style="background:#080808;padding:24px;text-align:center">
                        <span style="font-size:36px;font-weight:900;color:#1A5CFF">A</span>
                        <span style="font-size:36px;font-weight:900;color:#E8242A">F</span>
                        <span style="color:#fff;font-size:14px;margin-left:8px">APPARELS</span>
                    </div>
                    <div style="padding:32px;background:#fff">
                        <h2>Order Cancelled</h2>
                        <p>Hi {user.first_name or 'there'},</p>
                        <p>Your order <b>{order.order_number}</b> has been cancelled.</p>
                        <p>Questions? Call (214) 272-7213</p>
                        <p>— AF Apparels Team</p>
                    </div>
                    </div>
                """,
            )

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Order status email failed: %s", e)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@router.post("/orders/draft", status_code=201)
async def create_draft_order(
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create an empty draft (pending) order for admin to fill in."""
    from uuid import UUID as _UUID
    from app.models.company import Company as _Company, CompanyUser as _CompanyUser
    import string, random

    company_id_str = payload.get("company_id")
    if not company_id_str:
        raise HTTPException(status_code=422, detail="company_id is required")

    company_id = _UUID(str(company_id_str))

    # Verify company exists
    company = (await db.execute(select(_Company).where(_Company.id == company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Find an owner/user for placed_by_id (required FK)
    member = (await db.execute(
        select(_CompanyUser).where(_CompanyUser.company_id == company_id, _CompanyUser.is_active == True)
        .limit(1)
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=422, detail="Company has no active users — add a user first")

    # Generate order number
    suffix = "".join(random.choices(string.digits, k=6))
    order_number = f"DRAFT-{suffix}"

    order = Order(
        company_id=company_id,
        placed_by_id=member.user_id,
        order_number=order_number,
        status="pending",
        payment_status="unpaid",
        po_number=payload.get("po_number"),
        notes=payload.get("notes"),
        subtotal=0,
        shipping_cost=0,
        tax_amount=0,
        total=0,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return {"id": str(order.id), "order_number": order.order_number}


@router.get("/orders", response_model=PaginatedResponse[AdminOrderListItem])
async def list_admin_orders(
    q: str | None = None,
    status: str | None = None,
    payment_status: str | None = None,
    company_id: str | None = None,
    date_from: date | None = Query(None, description="Filter orders created on or after this date"),
    date_to: date | None = Query(None, description="Filter orders created on or before this date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order, Company.name.label("company_name")).join(
        Company, Order.company_id == Company.id
    )
    if q:
        query = query.where(
            (Order.order_number.ilike(f"%{q}%")) | (Order.po_number.ilike(f"%{q}%"))
        )
    if status:
        query = query.where(Order.status == status)
    if payment_status:
        query = query.where(Order.payment_status == payment_status)
    if company_id:
        query = query.where(Order.company_id == company_id)
    if date_from:
        query = query.where(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.all()

    items = []
    for row in rows:
        order, company_name = row
        item_count = (await db.execute(
            select(func.count(OrderItem.id)).where(OrderItem.order_id == order.id)
        )).scalar_one()
        items.append(AdminOrderListItem(
            id=order.id,
            order_number=order.order_number,
            company_name=company_name,
            status=order.status,
            payment_status=order.payment_status,
            po_number=order.po_number,
            total=order.total,
            item_count=item_count,
            created_at=order.created_at,
            tracking_number=order.tracking_number,
            courier=order.courier,
            courier_service=order.courier_service,
            shipped_at=order.shipped_at,
        ))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=(total + page_size - 1) // page_size)


@router.get("/orders/export-csv")
async def export_orders_csv(
    q: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Order, Company.name.label("company_name")).join(Company, Order.company_id == Company.id)
    if q:
        query = query.where(Order.order_number.ilike(f"%{q}%"))
    if status:
        query = query.where(Order.status == status)
    result = await db.execute(query.order_by(Order.created_at.desc()))
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order #", "Company", "Status", "Payment", "PO Number", "Total", "Created"])
    for row in rows:
        order, company_name = row
        writer.writerow([
            order.order_number, company_name, order.status, order.payment_status,
            order.po_number or "", str(order.total), order.created_at.isoformat(),
        ])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"},
    )


@router.get("/orders/{order_id}", response_model=AdminOrderDetail)
async def get_admin_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order, Company.name.label("company_name"))
        .join(Company, Order.company_id == Company.id)
        .where(Order.id == order_id)
    )
    row = result.one_or_none()
    if not row:
        raise NotFoundError(f"Order {order_id} not found")
    order, company_name = row

    items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    items = items_result.scalars().all()

    # Enrich with customer contact from placing user
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    try:
        user_result = await db.execute(select(User).where(User.id == order.placed_by_id))
        user = user_result.scalar_one_or_none()
        if user:
            customer_name = f"{user.first_name} {user.last_name}".strip() or None
            customer_email = user.email
            customer_phone = user.phone
    except Exception:
        pass

    # Parse shipping address snapshot
    shipping_address: dict | None = None
    if order.shipping_address_snapshot:
        try:
            raw = _json.loads(order.shipping_address_snapshot)
            # Normalize to frontend-expected keys
            shipping_address = {
                "full_name": raw.get("full_name") or raw.get("label"),
                "address_line1": raw.get("address_line1") or raw.get("line1"),
                "address_line2": raw.get("address_line2") or raw.get("line2"),
                "city": raw.get("city"),
                "state": raw.get("state"),
                "postal_code": raw.get("postal_code"),
                "zip_code": raw.get("postal_code"),
                "country": raw.get("country"),
            }
        except Exception:
            pass

    return AdminOrderDetail(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        po_number=order.po_number,
        order_notes=order.notes,
        subtotal=order.subtotal,
        shipping_cost=order.shipping_cost,
        tax_amount=order.tax_amount,
        total=order.total,
        company_id=order.company_id,
        company_name=company_name,
        tracking_number=order.tracking_number,
        courier=order.courier,
        courier_service=order.courier_service,
        shipped_at=order.shipped_at,
        qb_invoice_id=order.qb_invoice_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[OrderItemOut.model_validate(i) for i in items],
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        shipping_address=shipping_address,
    )


@router.post("/orders/{order_id}/items", status_code=201)
async def add_order_item(
    order_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a line item to a pending/draft order."""
    from uuid import UUID as _UUID
    from app.models.product import ProductVariant

    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=422, detail="Can only add items to pending orders")

    variant_id_str = payload.get("variant_id")
    quantity = int(payload.get("quantity", 1))
    if not variant_id_str or quantity < 1:
        raise HTTPException(status_code=422, detail="variant_id and quantity required")

    variant_id = _UUID(str(variant_id_str))
    variant = (await db.execute(
        select(ProductVariant).where(ProductVariant.id == variant_id)
    )).scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Product variant not found")

    # Use provided unit_price or fall back to variant retail price
    unit_price = float(payload.get("unit_price") or variant.retail_price or 0)
    line_total = unit_price * quantity

    # Fetch product info for denormalized fields
    from app.models.product import Product
    product = (await db.execute(
        select(Product).where(Product.id == variant.product_id)
    )).scalar_one_or_none()

    item = OrderItem(
        order_id=order_id,
        variant_id=variant_id,
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
        product_name=product.name if product else "Unknown",
        sku=variant.sku or "",
        color=variant.color,
        size=variant.size,
    )
    db.add(item)

    # Recalculate order totals
    order.subtotal = float(order.subtotal or 0) + line_total
    order.total = float(order.subtotal) + float(order.shipping_cost or 0) + float(order.tax_amount or 0)

    await db.commit()
    return {"message": "Item added", "item_id": str(item.id), "subtotal": float(order.subtotal), "total": float(order.total)}


@router.delete("/orders/{order_id}/items/{item_id}", status_code=200)
async def remove_order_item(
    order_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a line item from a pending/draft order."""
    item = (await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if order and order.status in ("pending", "confirmed"):
        order.subtotal = max(0, float(order.subtotal or 0) - float(item.line_total or 0))
        order.total = float(order.subtotal) + float(order.shipping_cost or 0) + float(order.tax_amount or 0)

    await db.delete(item)
    await db.commit()
    return {"message": "Item removed"}


@router.patch("/orders/{order_id}", response_model=dict)
async def update_admin_order(
    order_id: UUID,
    payload: OrderUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise NotFoundError(f"Order {order_id} not found")

    old_status = order.status
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.commit()

    if payload.status and payload.status != old_status:
        await _send_order_status_email(order, payload.status, db)

    return {"message": "Order updated"}


@router.patch("/orders/{order_id}/status", response_model=dict)
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    order.status = payload.status

    if payload.tracking_number is not None:
        order.tracking_number = payload.tracking_number
    if payload.courier is not None:
        order.courier = payload.courier
    if payload.courier_service is not None:
        order.courier_service = payload.courier_service
    if payload.status == "shipped" and not order.shipped_at:
        order.shipped_at = datetime.now(timezone.utc)

    await db.commit()

    if payload.status != old_status:
        await _send_order_status_email(order, payload.status, db)

    return {"success": True, "status": order.status}


@router.post("/orders/{order_id}/cancel", response_model=dict)
async def cancel_admin_order(
    order_id: UUID,
    payload: CancelOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        raise NotFoundError(f"Order {order_id} not found")
    order.status = "cancelled"
    if hasattr(order, "notes"):
        order.notes = f"Cancelled: {payload.reason}"
    await db.commit()

    await _send_order_status_email(order, "cancelled", db)

    return {"message": "Order cancelled"}


@router.post("/orders/{order_id}/sync-quickbooks", response_model=dict)
async def sync_order_to_quickbooks(order_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.tasks.quickbooks_tasks import sync_order_to_qb
    sync_order_to_qb.delay(str(order_id))
    return {"message": "QuickBooks sync queued", "order_id": str(order_id)}


# ---------------------------------------------------------------------------
# Admin RMA management
# ---------------------------------------------------------------------------

@router.get("/rma")
async def list_admin_rma(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(RMARequest)
    if status:
        query = query.where(RMARequest.status == status)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    result = await db.execute(
        query.order_by(RMARequest.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    return PaginatedResponse(
        items=list(result.scalars().all()),
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.patch("/rma/{rma_id}", response_model=dict)
async def update_rma(
    rma_id: UUID,
    payload: RMAUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    rma = (await db.execute(select(RMARequest).where(RMARequest.id == rma_id))).scalar_one_or_none()
    if not rma:
        raise NotFoundError(f"RMA {rma_id} not found")
    rma.status = payload.status
    if payload.admin_notes:
        rma.admin_notes = payload.admin_notes
    await db.commit()

    return {"message": f"RMA {payload.status}"}


# ---------------------------------------------------------------------------
# Abandoned Carts — admin view
# ---------------------------------------------------------------------------

@router.get("/abandoned-carts")
async def admin_list_abandoned_carts(
    db: AsyncSession = Depends(get_db),
):
    import json
    from app.models.order import AbandonedCart

    result = await db.execute(
        select(AbandonedCart)
        .order_by(AbandonedCart.abandoned_at.desc())
        .limit(200)
    )
    carts = result.scalars().all()

    out = []
    for c in carts:
        company = (await db.execute(
            select(Company).where(Company.id == c.company_id)
        )).scalar_one_or_none()
        out.append({
            "id": str(c.id),
            "company_name": company.name if company else "Unknown",
            "company_id": str(c.company_id),
            "abandoned_at": c.abandoned_at,
            "total": float(c.total),
            "item_count": c.item_count,
            "items": json.loads(c.items_snapshot),
            "is_recovered": c.is_recovered,
            "recovered_at": c.recovered_at,
        })
    return out