import pytest
pytestmark = pytest.mark.asyncio


async def test_list_contacts(client, customer_headers):
    resp = await client.get("/api/v1/account/contacts", headers=customer_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_create_contact(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/contacts",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe.test@example.com",
            "department": "Accounting",
            "time_zone": "America/New_York",
            "phone": "555-1234",
            "notify_order_confirmation": True,
            "notify_order_shipped": True,
            "notify_invoices": False,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "jane.doe.test@example.com"
    assert data["department"] == "Accounting"


async def test_contact_new_fields(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/contacts",
        json={
            "first_name": "Home",
            "last_name": "Fields",
            "email": "homefields.test@example.com",
            "home_address1": "123 Home St",
            "home_city": "Miami",
            "home_state": "FL",
            "home_postal_code": "33101",
            "home_country": "US",
            "home_phone": "555-9999",
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201


async def test_delete_contact(client, customer_headers):
    create_resp = await client.post(
        "/api/v1/account/contacts",
        json={"first_name": "Del", "last_name": "Me", "email": "del.me.test@example.com"},
        headers=customer_headers,
    )
    assert create_resp.status_code == 201
    contact_id = create_resp.json()["id"]
    resp = await client.delete(
        f"/api/v1/account/contacts/{contact_id}",
        headers=customer_headers,
    )
    assert resp.status_code == 204
