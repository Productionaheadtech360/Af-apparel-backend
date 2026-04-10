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
    ) -> tuple[list, int]:
        # Build base filter
        filters = []
        if q:
            filters.append(Company.name.ilike(f"%{q}%"))
        if status:
            filters.append(Company.status == status)

        # Subqueries for order stats
        order_count_sub = (
            select(Order.company_id, func.count(Order.id).label("order_count"))
            .group_by(Order.company_id)
            .subquery()
        )
        total_spend_sub = (
            select(
                Order.company_id,
                func.coalesce(func.sum(Order.total), 0).label("total_spend"),
            )
            .where(Order.payment_status == "paid")
            .group_by(Order.company_id)
            .subquery()
        )

        query = (
            select(
                Company,
                func.coalesce(order_count_sub.c.order_count, 0).label("order_count"),
                func.coalesce(total_spend_sub.c.total_spend, 0).label("total_spend"),
            )
            .outerjoin(order_count_sub, Company.id == order_count_sub.c.company_id)
            .outerjoin(total_spend_sub, Company.id == total_spend_sub.c.company_id)
        )
        if filters:
            query = query.where(*filters)

        count_q = select(func.count(Company.id))
        if filters:
            count_q = count_q.where(*filters)
        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Company.name)
        result = await self.db.execute(query)
        rows = result.all()

        # Build list of dicts that match CompanyListItem schema
        companies = []
        for row in rows:
            company = row[0]
            companies.append({
                "id": company.id,
                "name": company.name,
                "status": company.status,
                "pricing_tier_id": company.pricing_tier_id,
                "shipping_tier_id": company.shipping_tier_id,
                "order_count": int(row[1]),
                "total_spend": Decimal(str(row[2])),
                "created_at": company.created_at,
            })
        return companies, total

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
