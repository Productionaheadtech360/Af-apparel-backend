import pytest


@pytest.mark.asyncio
async def test_list_abandoned_carts(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/abandoned-carts",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_abandoned_cart_fields(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/abandoned-carts",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    carts = resp.json()
    if carts:
        cart = carts[0]
        assert "id" in cart
        assert "abandoned_at" in cart
        assert "total" in cart
        assert "item_count" in cart
        assert "items" in cart
        assert "is_recovered" in cart


@pytest.mark.asyncio
async def test_recover_nonexistent_cart(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/abandoned-carts/00000000-0000-0000-0000-000000000000/recover",
        headers=customer_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_cart(client, customer_headers):
    resp = await client.delete(
        "/api/v1/account/abandoned-carts/00000000-0000-0000-0000-000000000000",
        headers=customer_headers,
    )
    assert resp.status_code in [204, 404]


@pytest.mark.asyncio
async def test_abandoned_cart_list_structure(client, customer_headers):
    """Endpoint returns a list (empty is fine if no carts exist yet)."""
    resp = await client.get(
        "/api/v1/account/abandoned-carts",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_abandoned_carts(client, admin_headers):
    resp = await client.get(
        "/api/v1/admin/abandoned-carts",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_abandoned_carts_requires_auth(client):
    resp = await client.get("/api/v1/admin/abandoned-carts")
    assert resp.status_code == 401
