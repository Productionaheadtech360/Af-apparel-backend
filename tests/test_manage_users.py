import pytest
pytestmark = pytest.mark.asyncio


async def test_list_users(client, customer_headers):
    resp = await client.get("/api/v1/account/users", headers=customer_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_users_has_required_fields(client, customer_headers):
    resp = await client.get("/api/v1/account/users", headers=customer_headers)
    assert resp.status_code == 200
    users = resp.json()
    if users:
        user = users[0]
        assert "email" in user
        assert "first_name" in user
        assert "last_name" in user
        assert "role" in user
        assert "user_group" in user
        assert "is_active" in user


async def test_invite_user_missing_fields(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/users/invite",
        json={},
        headers=customer_headers,
    )
    assert resp.status_code in [403, 422]


async def test_update_user_role(client, customer_headers):
    users_resp = await client.get("/api/v1/account/users", headers=customer_headers)
    users = users_resp.json()
    if len(users) > 1:
        non_owner = next((u for u in users if u.get("role") != "owner"), None)
        if non_owner:
            user_id = non_owner.get("user_id") or non_owner.get("id")
            resp = await client.patch(
                f"/api/v1/account/users/{user_id}",
                json={"user_group": "Accounting"},
                headers=customer_headers,
            )
            assert resp.status_code == 200
