import pytest


@pytest.mark.asyncio
async def test_inventory_report_base(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/inventory-report",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "warehouses" in data
    assert "products" in data
    assert "colors" in data


@pytest.mark.asyncio
async def test_inventory_report_warehouse_filter(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/inventory-report",
        headers=customer_headers,
    )
    data = resp.json()
    if not data["warehouses"]:
        pytest.skip("No warehouses")

    warehouse_id = data["warehouses"][0]["id"]
    resp2 = await client.get(
        f"/api/v1/account/inventory-report?warehouse_id={warehouse_id}",
        headers=customer_headers,
    )
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_inventory_report_product_filter(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/inventory-report",
        headers=customer_headers,
    )
    data = resp.json()
    if not data["products"]:
        pytest.skip("No products")

    product_id = data["products"][0]["id"]
    resp2 = await client.get(
        f"/api/v1/account/inventory-report?product_id={product_id}",
        headers=customer_headers,
    )
    assert resp2.status_code == 200
    for item in resp2.json()["items"]:
        assert item["product_id"] == product_id


@pytest.mark.asyncio
async def test_inventory_report_item_fields(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/inventory-report",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    if items:
        item = items[0]
        assert "variant_id" in item
        assert "sku" in item
        assert "product_name" in item
        assert "color" in item
        assert "size" in item
        assert "available" in item
        assert "warehouse_name" in item


@pytest.mark.asyncio
async def test_inventory_report_requires_auth(client):
    resp = await client.get("/api/v1/account/inventory-report")
    assert resp.status_code == 401
