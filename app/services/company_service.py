"""CompanyService — admin management of wholesale company accounts."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.company import Company
from app.models.order import Order
from app.schemas.company import CompanyUpdate, SuspendRequest


class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_companies_paginated(
        self,
        q: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Company], int]:
        query = select(Company)
        if q:
            query = query.where(Company.name.ilike(f"%{q}%"))
        if status:
            query = query.where(Company.status == status)

        count_q = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Company.name)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_company_detail(self, company_id: UUID) -> Company:
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise NotFoundError(f"Company {company_id} not found")
        return company

    async def update_company_tiers(self, company_id: UUID, data: CompanyUpdate) -> Company:
        company = await self.get_company_detail(company_id)
        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(company, field, value)
        await self.db.flush()
        await self.db.refresh(company)
        return company

    async def suspend(self, company_id: UUID, reason: str) -> Company:
        company = await self.get_company_detail(company_id)
        company.status = "suspended"
        # Could log reason to audit log or system notes here
        await self.db.flush()
        return company

    async def reactivate(self, company_id: UUID) -> Company:
        company = await self.get_company_detail(company_id)
        company.status = "active"
        await self.db.flush()
        return company

    async def get_order_stats(self, company_id: UUID) -> dict:
        count_result = await self.db.execute(
            select(func.count(Order.id)).where(Order.company_id == company_id)
        )
        total_result = await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.company_id == company_id, Order.payment_status == "paid"
            )
        )
        return {
            "order_count": count_result.scalar_one(),
            "total_spend": total_result.scalar_one(),
        }
