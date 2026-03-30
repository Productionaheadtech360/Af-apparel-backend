import pytest


@pytest.mark.asyncio
async def test_order_confirmation_pdf(client, customer_headers):
    orders_resp = await client.get("/api/v1/orders", headers=customer_headers)
    orders = orders_resp.json()
    if not orders.get("items"):
        pytest.skip("No orders to test PDF")

    order_id = orders["items"][0]["id"]
    resp = await client.get(
        f"/api/v1/orders/{order_id}/pdf/confirmation",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    assert "pdf" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_order_invoice_pdf(client, customer_headers):
    orders_resp = await client.get("/api/v1/orders", headers=customer_headers)
    orders = orders_resp.json()
    if not orders.get("items"):
        pytest.skip("No orders to test PDF")

    order_id = orders["items"][0]["id"]
    resp = await client.get(
        f"/api/v1/orders/{order_id}/pdf/invoice",
        headers=customer_headers,
    )
    assert resp.status_code in [200, 400]  # 400 if not paid


@pytest.mark.asyncio
async def test_order_pack_slip_pdf(client, customer_headers):
    orders_resp = await client.get("/api/v1/orders", headers=customer_headers)
    orders = orders_resp.json()
    if not orders.get("items"):
        pytest.skip("No orders to test PDF")

    order_id = orders["items"][0]["id"]
    resp = await client.get(
        f"/api/v1/orders/{order_id}/pdf/pack-slip",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    assert "pdf" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_order_ship_confirmation_pdf_not_shipped(client, customer_headers):
    orders_resp = await client.get("/api/v1/orders", headers=customer_headers)
    orders = orders_resp.json()
    if not orders.get("items"):
        pytest.skip("No orders to test")

    pending = next((o for o in orders["items"] if o["status"] == "pending"), None)
    if not pending:
        pytest.skip("No pending orders")

    resp = await client.get(
        f"/api/v1/orders/{pending['id']}/pdf/ship-confirmation",
        headers=customer_headers,
    )
    assert resp.status_code == 400  # not shipped yet


@pytest.mark.asyncio
async def test_order_comments_list(client, customer_headers):
    orders_resp = await client.get("/api/v1/orders", headers=customer_headers)
    orders = orders_resp.json()
    if not orders.get("items"):
        pytest.skip("No orders")

    order_id = orders["items"][0]["id"]
    resp = await client.get(
        f"/api/v1/orders/{order_id}/comments",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_order_comment_add(client, customer_headers):
    orders_resp = await client.get("/api/v1/orders", headers=customer_headers)
    orders = orders_resp.json()
    if not orders.get("items"):
        pytest.skip("No orders")

    order_id = orders["items"][0]["id"]
    resp = await client.post(
        f"/api/v1/orders/{order_id}/comments",
        json={"comment": "Test comment from automated test"},
        headers=customer_headers,
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_order_comment_empty_fails(client, customer_headers):
    orders_resp = await client.get("/api/v1/orders", headers=customer_headers)
    orders = orders_resp.json()
    if not orders.get("items"):
        pytest.skip("No orders")

    order_id = orders["items"][0]["id"]
    resp = await client.post(
        f"/api/v1/orders/{order_id}/comments",
        json={"comment": ""},
        headers=customer_headers,
    )
    assert resp.status_code in [400, 422]
