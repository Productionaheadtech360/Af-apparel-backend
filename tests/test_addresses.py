"""Tests for /api/v1/account/addresses — field mapping and CRUD."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_addresses_returns_200(client: AsyncClient, auth_headers: dict):
    """GET /account/addresses must return 200 with a list."""
    resp = await client.get("/api/v1/account/addresses", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_addresses_field_mapping(client: AsyncClient, auth_headers: dict):
    """API must return 'line1' (alias), not 'address_line1' (ORM column)."""
    resp = await client.get("/api/v1/account/addresses", headers=auth_headers)
    assert resp.status_code == 200
    for addr in resp.json():
        assert "line1" in addr, "API must return 'line1', not 'address_line1'"
        assert "address_line1" not in addr
        assert "is_default" in addr


@pytest.mark.asyncio
async def test_create_address(client: AsyncClient, auth_headers: dict):
    """POST /account/addresses must create and return the new address with correct fields."""
    payload = {
        "line1": "123 CI Test St",
        "city": "Los Angeles",
        "state": "CA",
        "postal_code": "90001",
        "country": "US",
    }
    resp = await client.post("/api/v1/account/addresses", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["line1"] == "123 CI Test St"
    assert data["city"] == "Los Angeles"
    assert "id" in data
    assert "is_default" in data


@pytest.mark.asyncio
async def test_create_address_missing_required(client: AsyncClient, auth_headers: dict):
    """Creating address without line1 must return 422."""
    resp = await client.post(
        "/api/v1/account/addresses",
        json={"city": "LA", "state": "CA", "postal_code": "90001"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_address(client: AsyncClient, auth_headers: dict):
    """Create then delete an address; subsequent GET must not include it."""
    # Create
    create_resp = await client.post(
        "/api/v1/account/addresses",
        json={"line1": "Delete Me St", "city": "X", "state": "CA", "postal_code": "90000"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    addr_id = create_resp.json()["id"]

    # Delete
    del_resp = await client.delete(f"/api/v1/account/addresses/{addr_id}", headers=auth_headers)
    assert del_resp.status_code in (200, 204)

    # Confirm gone
    list_resp = await client.get("/api/v1/account/addresses", headers=auth_headers)
    ids = [a["id"] for a in list_resp.json()]
    assert addr_id not in ids
