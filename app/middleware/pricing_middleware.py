"""Pricing middleware — attaches the company's tier discount % to request.state.

This middleware runs AFTER auth_middleware so request.state.pricing_tier_id is
already populated.  For unauthenticated requests the tier_discount_percent is
set to Decimal("0") (retail / no discount).

IMPORTANT: Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) to
avoid the known Starlette/asyncpg incompatibility where BaseHTTPMiddleware's
call_next() breaks the asyncpg greenlet context and causes MissingGreenlet
errors in route handlers that use async SQLAlchemy.
"""
from decimal import Decimal

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.redis import redis_get, redis_set
from app.core.database import AsyncSessionLocal as async_session_factory

_CACHE_PREFIX = "pricing_tier:"
_CACHE_TTL = 3600


class PricingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        tier_id = getattr(request.state, "pricing_tier_id", None)
        company_id = getattr(request.state, "company_id", None)
        discount_percent = Decimal("0")

        # If no tier_id baked into the JWT (e.g. tier was assigned after last login),
        # fall back to a live DB lookup using company_id.
        if not tier_id and company_id:
            try:
                from app.models.company import Company
                from sqlalchemy import select
                async with async_session_factory() as session:
                    row = await session.scalar(
                        select(Company.pricing_tier_id).where(Company.id == company_id)
                    )
                    if row:
                        tier_id = str(row)
            except Exception:
                pass

        if tier_id:
            cache_key = f"{_CACHE_PREFIX}{tier_id}:discount"
            cached = await redis_get(cache_key)
            if cached is not None:
                discount_percent = Decimal(cached)
            else:
                # Lazy DB lookup — only for authenticated requests with a tier
                try:
                    from app.models.pricing import PricingTier
                    from sqlalchemy import select

                    async with async_session_factory() as session:
                        result = await session.execute(
                            select(PricingTier.discount_percent).where(
                                PricingTier.id == tier_id
                            )
                        )
                        row = result.scalar_one_or_none()
                        if row is not None:
                            discount_percent = row
                            await redis_set(
                                cache_key, str(discount_percent), expire=_CACHE_TTL
                            )
                except Exception:
                    pass  # Graceful fallback to 0%

        request.state.tier_discount_percent = discount_percent

        # Resolve DiscountGroup ID for this company (drives variant pricing overrides)
        discount_group_id: str | None = None
        if company_id:
            dg_cache_key = f"company:{company_id}:discount_group_id"
            cached_dg = await redis_get(dg_cache_key)
            if cached_dg is not None:
                discount_group_id = cached_dg if cached_dg != "none" else None
            else:
                try:
                    from app.models.company import Company
                    from app.models.discount_group import DiscountGroup
                    from sqlalchemy import select
                    async with async_session_factory() as session:
                        tags = await session.scalar(
                            select(Company.tags).where(Company.id == company_id)
                        )
                        if tags:
                            dg_id = await session.scalar(
                                select(DiscountGroup.id)
                                .where(
                                    DiscountGroup.customer_tag.in_(tags),
                                    DiscountGroup.status == "enabled",
                                )
                                .limit(1)
                            )
                            if dg_id:
                                discount_group_id = str(dg_id)
                    await redis_set(dg_cache_key, discount_group_id or "none", expire=_CACHE_TTL)
                except Exception:
                    pass

        request.state.discount_group_id = discount_group_id
        await self.app(scope, receive, send)
