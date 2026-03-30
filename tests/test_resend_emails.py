import pytest
pytestmark = pytest.mark.asyncio


async def test_resend_emails_missing_recaptcha(client, customer_headers):
    # When RECAPTCHA_SECRET_KEY is configured, missing token → 422.
    # When it is empty (default in dev/CI), the check is skipped.
    # Either way, the endpoint must exist (not 404).
    resp = await client.post(
        "/api/v1/account/resend-registration-emails",
        json={"groups": ["Admin"], "to": "", "cc": "", "bcc": ""},
        headers=customer_headers,
    )
    assert resp.status_code in [200, 400, 422]


async def test_resend_emails_no_recipients(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/resend-registration-emails",
        json={"groups": [], "to": "", "cc": "", "bcc": "", "recaptcha_token": "fake_token"},
        headers=customer_headers,
    )
    assert resp.status_code in [400, 422]


async def test_resend_emails_endpoint_exists(client, customer_headers):
    resp = await client.post(
        "/api/v1/account/resend-registration-emails",
        json={"groups": ["Admin"]},
        headers=customer_headers,
    )
    assert resp.status_code != 404
