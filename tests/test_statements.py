import pytest


@pytest.mark.asyncio
async def test_list_statements(client, customer_headers):
    resp = await client.get("/api/v1/account/statements", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "summary" in data
    assert "total_charges" in data["summary"]
    assert "total_payments" in data["summary"]
    assert "current_balance" in data["summary"]


@pytest.mark.asyncio
async def test_statements_summary_fields(client, customer_headers):
    resp = await client.get("/api/v1/account/statements", headers=customer_headers)
    assert resp.status_code == 200
    summary = resp.json()["summary"]
    assert isinstance(summary["total_charges"], (int, float))
    assert isinstance(summary["current_balance"], (int, float))


@pytest.mark.asyncio
async def test_statements_date_filter(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/statements?date_from=2026-01-01&date_to=2026-12-31",
        headers=customer_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_statements_pdf_endpoint(client, customer_headers):
    resp = await client.get(
        "/api/v1/account/statements/pdf",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_statements_email_no_contacts(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/statements/email",
        json={"date_from": None, "date_to": None},
        headers=customer_headers,
    )
    assert resp.status_code in [200, 400, 422]  # never 500


@pytest.mark.asyncio
async def test_statements_sync_qb(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/statements/sync-qb",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "synced" in data
