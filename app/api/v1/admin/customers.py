"""Admin — wholesale applications and company management."""
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.order import Order
from app.schemas.wholesale import ApproveApplicationRequest, RejectApplicationRequest, WholesaleApplicationOut
from app.schemas.company import CompanyDetail, CompanyListItem, CompanyUpdate, SuspendRequest
from app.services.wholesale_service import WholesaleService
from app.services.company_service import CompanyService
from app.types.api import PaginatedResponse

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
