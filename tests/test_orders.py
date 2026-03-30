"""Tests for GET /api/v1/orders — regression guard against ResponseValidationError
and MissingGreenlet from lazy-loaded relationships."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_orders_returns_200(client: AsyncClient, auth_headers: dict):
    """GET /orders must always return 200 with a valid paginated body."""
    resp = await client.get("/api/v1/orders?page=1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_get_orders_item_count_field_present(client: AsyncClient, auth_headers: dict):
    """Each order in the list must have item_count (computed @property, not lazy-loaded)."""
    resp = await client.get("/api/v1/orders?page=1", headers=auth_headers)
    assert resp.status_code == 200
    for order in resp.json()["items"]:
        assert "item_count" in order, f"item_count missing from order {order.get('id')}"
        assert isinstance(order["item_count"], int)


@pytest.mark.asyncio
async def test_get_orders_pagination(client: AsyncClient, auth_headers: dict):
    """page_size param must be respected; pages field must be calculated correctly."""
    resp = await client.get("/api/v1/orders?page=1&page_size=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 5
    total = data["total"]
    expected_pages = max(1, -(-total // 5))  # ceiling division
    assert data["pages"] == expected_pages


@pytest.mark.asyncio
async def test_get_orders_no_lazy_load(client: AsyncClient, auth_headers: dict):
    """Concurrent requests must not trigger MissingGreenlet (selectinload covers all relationships)."""
    import asyncio
    responses = await asyncio.gather(
        *[client.get("/api/v1/orders?page=1", headers=auth_headers) for _ in range(3)]
    )
    for resp in responses:
        assert resp.status_code == 200, f"Unexpected {resp.status_code}: {resp.text[:200]}"


@pytest.mark.asyncio
async def test_get_order_detail(client: AsyncClient, auth_headers: dict):
    """GET /orders/{id} must return 200 or 404 — never 500."""
    import uuid
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/orders/{fake_id}", headers=auth_headers)
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_get_orders_requires_auth(client: AsyncClient):
    """Unauthenticated requests must return 401 or 403."""
    resp = await client.get("/api/v1/orders")
    assert resp.status_code in (401, 403)
