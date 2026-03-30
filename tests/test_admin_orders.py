"""Tests for admin orders endpoints — regression guard for ResponseValidationError."""
import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_orders_list_returns_200(client: AsyncClient, admin_headers: dict):
    """GET /admin/orders must return 200 with paginated response."""
    resp = await client.get("/api/v1/admin/orders?page=1", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_admin_orders_item_count(client: AsyncClient, admin_headers: dict):
    """Each order in admin list must have item_count field."""
    resp = await client.get("/api/v1/admin/orders?page=1", headers=admin_headers)
    assert resp.status_code == 200
    for order in resp.json()["items"]:
        assert "item_count" in order


@pytest.mark.asyncio
async def test_admin_order_detail_not_500(client: AsyncClient, admin_headers: dict):
    """GET /admin/orders/{id} must never return 500 — only 200 or 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/admin/orders/{fake_id}", headers=admin_headers)
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_admin_orders_requires_admin(client: AsyncClient, auth_headers: dict):
    """Non-admin users must be denied access to admin orders."""
    resp = await client.get("/api/v1/admin/orders", headers=auth_headers)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_orders_unauthenticated(client: AsyncClient):
    """Unauthenticated requests to admin orders must return 401 or 403."""
    resp = await client.get("/api/v1/admin/orders")
    assert resp.status_code in (401, 403)
