import pytest
pytestmark = pytest.mark.asyncio


async def test_change_password_wrong_current(client, customer_headers):
    resp = await client.patch(
        "/api/v1/account/change-password",
        json={"current_password": "wrongpassword", "new_password": "NewPass123!"},
        headers=customer_headers,
    )
    assert resp.status_code in [400, 422]


async def test_change_password_missing_fields(client, customer_headers):
    resp = await client.patch(
        "/api/v1/account/change-password",
        json={},
        headers=customer_headers,
    )
    assert resp.status_code == 422


async def test_change_password_endpoint_exists(client, customer_headers):
    resp = await client.patch(
        "/api/v1/account/change-password",
        json={"current_password": "test", "new_password": "short"},
        headers=customer_headers,
    )
    assert resp.status_code != 404
