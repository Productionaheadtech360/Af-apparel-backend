"""Admin — wholesale applications and company management."""
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.company import Company, CompanyUser
from app.models.order import Order
from app.models.user import User
from app.schemas.wholesale import ApproveApplicationRequest, RejectApplicationRequest, WholesaleApplicationOut
from app.schemas.company import CompanyDetail, CompanyListItem, CompanyUpdate, SuspendRequest
from app.services.wholesale_service import WholesaleService
from app.services.company_service import CompanyService
from app.types.api import PaginatedResponse


class CreateCompanyRequest(BaseModel):
    name: str
    business_type: str = "retailer"
    tax_id: str | None = None
    website: str | None = None
    phone: str | None = None
    company_email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_province: str | None = None
    postal_code: str | None = None
    country: str | None = None
    # Contact person (creates/links a user account)
    contact_first_name: str | None = None
    contact_last_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    pricing_tier_id: uuid.UUID | None = None
    shipping_tier_id: uuid.UUID | None = None
    admin_notes: str | None = None

router = APIRouter()


@router.get("/wholesale-applications", response_model=list[WholesaleApplicationOut])
async def list_wholesale_applications(
    status: str | None = None,
    page: int = 1,
    per_page: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[WholesaleApplicationOut]:
    service = WholesaleService(db)
    applications, _ = await service.list_applications(status=status, page=page, per_page=per_page)
    return [WholesaleApplicationOut.model_validate(a) for a in applications]


@router.post("/wholesale-applications/{application_id}/approve", status_code=200)
async def approve_application(
    application_id: uuid.UUID,
    data: ApproveApplicationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = WholesaleService(db)
    company = await service.approve(
        application_id=application_id,
        data=data,
        admin_user_id=uuid.UUID(request.state.user_id),
    )
    return {"message": "Application approved", "company_id": str(company.id)}


@router.post("/wholesale-applications/{application_id}/reject", status_code=200)
async def reject_application(
    application_id: uuid.UUID,
    data: RejectApplicationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = WholesaleService(db)
    await service.reject(
        application_id=application_id,
        data=data,
        admin_user_id=uuid.UUID(request.state.user_id),
    )
    return {"message": "Application rejected"}


# ---------------------------------------------------------------------------
# Companies (T117 — US-15)
# ---------------------------------------------------------------------------

@router.post("/companies", status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CreateCompanyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a wholesale company account directly from admin (bypasses application flow)."""
    from app.core.security import hash_password as get_password_hash

    # Create the company
    company = Company(
        name=payload.name,
        business_type=payload.business_type,
        tax_id=payload.tax_id,
        website=payload.website,
        phone=payload.phone,
        company_email=payload.company_email,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        state_province=payload.state_province,
        postal_code=payload.postal_code,
        country=payload.country or "US",
        status="active",
        pricing_tier_id=payload.pricing_tier_id,
        shipping_tier_id=payload.shipping_tier_id,
        admin_notes=payload.admin_notes,
    )
    db.add(company)
    await db.flush()

    # Optionally create/link a user account for the contact person
    user_created = False
    if payload.contact_email:
        existing = (await db.execute(
            select(User).where(User.email == payload.contact_email)
        )).scalar_one_or_none()

        if existing:
            user = existing
        else:
            # Create a new user with a temporary password (they'll need to reset it)
            import secrets
            temp_password = secrets.token_urlsafe(16)
            user = User(
                email=payload.contact_email,
                first_name=payload.contact_first_name or "",
                last_name=payload.contact_last_name or "",
                phone=payload.contact_phone,
                hashed_password=get_password_hash(temp_password),
                is_active=True,
                email_verified=True,
            )
            db.add(user)
            await db.flush()
            user_created = True

        membership = CompanyUser(
            company_id=company.id,
            user_id=user.id,
            role="owner",
            is_active=True,
        )
        db.add(membership)

    await db.commit()
    return {
        "message": "Company created",
        "company_id": str(company.id),
        "user_created": user_created,
    }


@router.get("/companies/export-csv")
async def export_companies_csv(
    q: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    import csv
    import io
    from fastapi.responses import StreamingResponse

    svc = CompanyService(db)
    companies, _ = await svc.list_companies_paginated(q=q, status=status, page=1, page_size=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Company", "Contact", "Email", "Phone", "Status", "Orders", "Total Spent", "Joined"])
    for c in companies:
        writer.writerow([
            c["name"], c.get("contact_name") or "", c.get("email") or "",
            c.get("phone") or "", c["status"], c["order_count"],
            str(c["total_spend"]), c["created_at"].isoformat(),
        ])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@router.get("/companies", response_model=PaginatedResponse[CompanyListItem])
async def list_companies(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    svc = CompanyService(db)
    companies, total = await svc.list_companies_paginated(q=q, status=status, page=page, page_size=page_size)
    return PaginatedResponse(
        items=companies,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/companies/{company_id}", response_model=CompanyDetail)
async def get_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = CompanyService(db)
    return await svc.get_company_detail(company_id)


@router.patch("/companies/{company_id}", response_model=CompanyDetail)
async def update_company(
    company_id: UUID, payload: CompanyUpdate, db: AsyncSession = Depends(get_db)
):
    svc = CompanyService(db)
    company = await svc.update_company_tiers(company_id, payload)
    await db.commit()
    return company


@router.post("/companies/{company_id}/suspend", status_code=status.HTTP_200_OK)
async def suspend_company(
    company_id: UUID, payload: SuspendRequest, db: AsyncSession = Depends(get_db)
):
    svc = CompanyService(db)
    await svc.suspend(company_id, payload.reason)
    await db.commit()
    return {"message": "Company suspended"}


@router.post("/companies/{company_id}/reactivate", status_code=status.HTTP_200_OK)
async def reactivate_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = CompanyService(db)
    await svc.reactivate(company_id)
    await db.commit()
    return {"message": "Company reactivated"}


@router.get("/companies/{company_id}/stats")
async def get_customer_stats(company_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total), 0).label("total_spent"),
            func.max(Order.created_at).label("last_order_date"),
        ).where(Order.company_id == company_id)
    )
    row = result.one()
    return {
        "total_orders": row.total_orders or 0,
        "total_spent": float(row.total_spent or 0),
        "last_order_date": row.last_order_date,
    }
