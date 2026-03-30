import pytest
pytestmark = pytest.mark.asyncio


async def test_list_payment_methods(client, customer_headers):
    resp = await client.get("/api/v1/account/payment-methods", headers=customer_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_payment_methods_fields(client, customer_headers):
    resp = await client.get("/api/v1/account/payment-methods", headers=customer_headers)
    assert resp.status_code == 200
    methods = resp.json()
    if methods:
        method = methods[0]
        assert "id" in method
        assert "brand" in method
        assert "last4" in method
        assert "exp_month" in method
        assert "exp_year" in method
        assert "is_default" in method


async def test_set_default_payment_method_endpoint(client, customer_headers):
    resp = await client.patch(
        "/api/v1/account/payment-methods/fake-id/set-default",
        json={},
        headers=customer_headers,
    )
    assert resp.status_code in [200, 404, 400]  # never 500


async def test_delete_payment_method_endpoint(client, customer_headers):
    resp = await client.delete(
        "/api/v1/account/payment-methods/fake-id",
        headers=customer_headers,
    )
    assert resp.status_code in [204, 404, 400]  # never 500
