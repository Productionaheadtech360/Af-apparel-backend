import pytest
pytestmark = pytest.mark.asyncio


async def test_get_full_profile(client, customer_headers):
    resp = await client.get("/api/v1/account/profile/full", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "web_user" in data
    assert "company" in data
    assert "first_name" in data["web_user"]
    assert "email" in data["web_user"]


async def test_update_user_profile(client, customer_headers):
    resp = await client.patch(
        "/api/v1/account/profile/user",
        json={"first_name": "Updated", "last_name": "Name"},
        headers=customer_headers,
    )
    assert resp.status_code == 200


async def test_update_company_profile(client, customer_headers):
    resp = await client.patch(
        "/api/v1/account/profile/company",
        json={"phone": "555-1234", "website": "https://test.com"},
        headers=customer_headers,
    )
    assert resp.status_code == 200


async def test_company_profile_new_fields(client, customer_headers):
    resp = await client.patch(
        "/api/v1/account/profile/company",
        json={
            "fax": "555-0000",
            "tax_id_expiry": "12/2025",
            "estimated_annual_volume": "$10,000 - $50,000",
            "ppac_number": "PPAC123",
            "ppai_number": "PPAI456",
            "asi_number": "ASI789",
        },
        headers=customer_headers,
    )
    assert resp.status_code == 200
