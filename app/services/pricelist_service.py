"""PriceListService — triggers async generation and polls status."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.system import PriceListRequest


class PriceListService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_generation(
        self, company_id: UUID, format: str = "pdf"
    ) -> PriceListRequest:
        """Queue a new price list generation task and return the request record."""
        from app.tasks.pricelist_tasks import generate_price_list_task

        req = PriceListRequest(
            company_id=company_id,
            format=format,
            status="pending",
        )
        self.db.add(req)
        await self.db.flush()
        await self.db.refresh(req)

        # Enqueue Celery task
        generate_price_list_task.delay(str(req.id), str(company_id), format)
        return req

    async def get_request_status(
        self, request_id: UUID, company_id: UUID
    ) -> PriceListRequest:
        result = await self.db.execute(
            select(PriceListRequest).where(
                PriceListRequest.id == request_id,
                PriceListRequest.company_id == company_id,
            )
        )
        req = result.scalar_one_or_none()
        if not req:
            raise NotFoundError(f"Price list request {request_id} not found")
        return req
