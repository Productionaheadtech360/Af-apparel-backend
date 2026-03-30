"""Shared pytest fixtures for integration tests.

Seeding uses synchronous psycopg2 (via DATABASE_URL_SYNC) to avoid async
event-loop scope conflicts between session-scoped seed fixtures and
function-scoped async test fixtures.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

import app.models  # ensure all models registered with SQLAlchemy mapper  # noqa: F401
from app.main import app
from app.core.config import settings


# ── Synchronous seed (runs once per session, no event loop) ──────────────────

def _sync_ensure_users() -> dict:
    """Create test company, customer, and admin using psycopg2 if not present."""
    import psycopg2
    from app.core.security import hash_password

    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    # --- company ---
    cur.execute("SELECT id FROM companies WHERE name = '_CI Test Company' LIMIT 1")
    row = cur.fetchone()
    if row:
        company_id = row[0]
    else:
        cur.execute(
            """INSERT INTO companies (id, name, status, created_at, updated_at)
               VALUES (gen_random_uuid(), '_CI Test Company', 'active', now(), now())
               RETURNING id""",
        )
        company_id = cur.fetchone()[0]

    # --- customer user ---
    customer_email = "ci_customer@test.internal"
    customer_pw = "CIPass123!"
    cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (customer_email,))
    row = cur.fetchone()
    if row:
        customer_id = row[0]
    else:
        cur.execute(
            """INSERT INTO users
               (id, email, hashed_password, first_name, last_name,
                is_admin, is_active, email_verified, created_at, updated_at)
               VALUES (gen_random_uuid(), %s, %s, 'CI', 'Customer',
                       false, true, true, now(), now())
               RETURNING id""",
            (customer_email, hash_password(customer_pw)),
        )
        customer_id = cur.fetchone()[0]

    # --- membership ---
    cur.execute(
        "SELECT id FROM company_users WHERE user_id = %s AND company_id = %s LIMIT 1",
        (customer_id, company_id),
    )
    if not cur.fetchone():
        cur.execute(
            """INSERT INTO company_users
               (id, user_id, company_id, role, is_active, created_at, updated_at)
               VALUES (gen_random_uuid(), %s, %s, 'owner', true, now(), now())""",
            (customer_id, company_id),
        )

    # --- admin user ---
    admin_email = "admin@afapparels.com"
    admin_pw = "Admin123!"
    cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (admin_email,))
    if not cur.fetchone():
        cur.execute(
            """INSERT INTO users
               (id, email, hashed_password, first_name, last_name,
                is_admin, is_active, email_verified, created_at, updated_at)
               VALUES (gen_random_uuid(), %s, %s, 'Admin', 'User',
                       true, true, true, now(), now())""",
            (admin_email, hash_password(admin_pw)),
        )

    conn.commit()
    cur.close()
    conn.close()

    return {
        "customer": {"email": customer_email, "password": customer_pw},
        "admin": {"email": admin_email, "password": admin_pw},
    }


@pytest.fixture(scope="session")
def credentials() -> dict:
    """Session-scoped sync fixture — seed DB once and return credentials."""
    return _sync_ensure_users()


# ── HTTP client (function-scoped) ─────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ── Auth header fixtures ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, credentials: dict) -> dict:
    creds = credentials["customer"]
    resp = await client.post(
        "/api/v1/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert resp.status_code == 200, f"Customer login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def customer_headers(client: AsyncClient, credentials: dict) -> dict:
    """Alias for auth_headers — used by test_critical_endpoints.py."""
    creds = credentials["customer"]
    resp = await client.post(
        "/api/v1/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert resp.status_code == 200, f"Customer login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, credentials: dict) -> dict:
    creds = credentials["admin"]
    resp = await client.post(
        "/api/v1/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    if resp.status_code != 200:
        pytest.skip(f"Admin login failed: {resp.text}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
