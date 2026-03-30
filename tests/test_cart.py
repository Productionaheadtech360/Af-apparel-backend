"""Tests for GET /api/v1/cart — regression guard for company_id-scoped cart."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cart_returns_200(client: AsyncClient, auth_headers: dict):
    """GET /cart must return 200 for authenticated company users."""
    resp = await client.get("/api/v1/cart", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cart_has_required_fields(client: AsyncClient, auth_headers: dict):
    """Cart response must include items, subtotal, and validation block."""
    resp = await client.get("/api/v1/cart", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "subtotal" in data
    assert "validation" in data
    assert "is_valid" in data["validation"]


@pytest.mark.asyncio
async def test_cart_requires_auth(client: AsyncClient):
    """Unauthenticated cart access must return 401 or 403."""
    resp = await client.get("/api/v1/cart")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_add_to_cart_bad_variant(client: AsyncClient, auth_headers: dict):
    """Adding a non-existent variant must return 404 or 422, not 500."""
    import uuid
    resp = await client.post(
        "/api/v1/cart/items",
        json={"variant_id": str(uuid.uuid4()), "quantity": 1},
        headers=auth_headers,
    )
    assert resp.status_code in (404, 422, 400)
