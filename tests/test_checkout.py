"""Tests for checkout endpoints — tokenize and confirm."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_checkout_tokenize_endpoint_exists(client: AsyncClient, auth_headers: dict):
    """POST /checkout/tokenize must exist (200 or 503/422 for missing QB token — never 404)."""
    resp = await client.post(
        "/api/v1/checkout/tokenize",
        json={
            "card_number": "4111111111111111",
            "exp_month": "12",
            "exp_year": "2026",
            "cvc": "123",
            "name": "Test User",
        },
        headers=auth_headers,
    )
    # 200 = QB available in test env; 422/503 = QB unavailable or validation error — never 404 or 500
    assert resp.status_code != 404, "Tokenize endpoint is missing"
    assert resp.status_code != 500, f"Tokenize returned 500: {resp.text[:300]}"


@pytest.mark.asyncio
async def test_checkout_confirm_rejects_empty_body(client: AsyncClient, auth_headers: dict):
    """POST /checkout/confirm with no payment info must return 422, not 500."""
    resp = await client.post("/api/v1/checkout/confirm", json={}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_checkout_confirm_rejects_missing_payment(client: AsyncClient, auth_headers: dict):
    """Supplying address but no payment token must return 422."""
    import uuid
    resp = await client.post(
        "/api/v1/checkout/confirm",
        json={"address_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_checkout_confirm_requires_auth(client: AsyncClient):
    """Unauthenticated confirm must return 401 or 403."""
    resp = await client.post(
        "/api/v1/checkout/confirm",
        json={"qb_token": "fake-token"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_checkout_intent_endpoint_exists(client: AsyncClient, auth_headers: dict):
    """POST /checkout/intent must exist (400/422 for empty cart — never 404)."""
    resp = await client.post(
        "/api/v1/checkout/intent",
        json={"cart_validated": True},
        headers=auth_headers,
    )
    assert resp.status_code != 404, "Intent endpoint is missing"
    assert resp.status_code != 500, f"Intent returned 500: {resp.text[:300]}"
