import pytest
pytestmark = pytest.mark.asyncio


async def test_tokenize_endpoint_exists(client, customer_headers):
    resp = await client.post(
        "/api/v1/checkout/tokenize",
        json={"card": {
            "number": "4111111111111111",
            "expMonth": "12",
            "expYear": "2026",
            "cvc": "123",
            "name": "Test User",
        }},
        headers=customer_headers,
    )
    assert resp.status_code in [200, 400, 422, 503]  # never 404


async def test_tokenize_missing_card_field(client, customer_headers):
    resp = await client.post(
        "/api/v1/checkout/tokenize",
        json={},
        headers=customer_headers,
    )
    assert resp.status_code in [400, 422]


async def test_tokenize_nested_card_format(client, customer_headers):
    resp = await client.post(
        "/api/v1/checkout/tokenize",
        json={"card": {"number": "4111111111111111", "expMonth": "12", "expYear": "2026", "cvc": "123"}},
        headers=customer_headers,
    )
    assert resp.status_code != 422
