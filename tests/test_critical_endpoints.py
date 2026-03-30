"""Critical endpoint smoke tests — regression guard for the most important routes."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_orders_list_returns_200(client: AsyncClient, customer_headers: dict):
    resp = await client.get("/api/v1/orders?page=1", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_cart_returns_200(client: AsyncClient, customer_headers: dict):
    resp = await client.get("/api/v1/cart", headers=customer_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_addresses_field_mapping(client: AsyncClient, customer_headers: dict):
    resp = await client.get("/api/v1/account/addresses", headers=customer_headers)
    assert resp.status_code == 200
    addresses = resp.json()
    if addresses:
        assert "line1" in addresses[0]
        assert "address_line1" not in addresses[0]


@pytest.mark.asyncio
async def test_admin_orders_list(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/admin/orders?page=1", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_companies_list(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/admin/companies?page=1", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_products_list(client: AsyncClient, customer_headers: dict):
    resp = await client.get("/api/v1/products?page=1", headers=customer_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_checkout_tokenize_exists(client: AsyncClient, customer_headers: dict):
    """Tokenize endpoint must exist (200 or 503 from QB, never 404 or 500)."""
    resp = await client.post(
        "/api/v1/checkout/tokenize",
        json={"card": {"number": "4111111111111111", "expMonth": "12",
                       "expYear": "2026", "cvc": "123", "name": "Test"}},
        headers=customer_headers,
    )
    assert resp.status_code in (200, 422, 503)  # 422 = schema validation, 503 = QB unavailable


@pytest.mark.asyncio
async def test_payment_status_never_uppercase(client: AsyncClient, admin_headers: dict):
    """All orders must have valid lowercase payment_status enum values."""
    resp = await client.get("/api/v1/admin/orders?page=1", headers=admin_headers)
    assert resp.status_code == 200
    for order in resp.json().get("items", []):
        assert order["payment_status"] in ("unpaid", "pending", "paid", "refunded", "failed")


@pytest.mark.asyncio
async def test_full_profile_endpoint(client: AsyncClient, customer_headers: dict):
    resp = await client.get("/api/v1/account/profile/full", headers=customer_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_payment_methods_endpoint(client: AsyncClient, customer_headers: dict):
    resp = await client.get("/api/v1/account/payment-methods", headers=customer_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resend_emails_endpoint(client: AsyncClient, customer_headers: dict):
    resp = await client.post(
        "/api/v1/account/resend-registration-emails",
        json={"groups": []},
        headers=customer_headers,
    )
    assert resp.status_code != 404


@pytest.mark.asyncio
async def test_tokenize_endpoint(client: AsyncClient, customer_headers: dict):
    resp = await client.post(
        "/api/v1/checkout/tokenize",
        json={"card": {"number": "4111111111111111", "expMonth": "12", "expYear": "2026", "cvc": "123"}},
        headers=customer_headers,
    )
    assert resp.status_code not in [404, 500]
