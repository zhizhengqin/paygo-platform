import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_infra():
    """Initialize Redis once for the test session, then clean up."""
    await init_redis()
    yield
    await close_redis()
    from app.database import engine
    await engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(client):
    """Login and set session cookie on the shared client for authenticated requests."""
    resp = await client.post(
        "/login", data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    cookie = resp.cookies.get("session")
    assert cookie is not None
    client.cookies.set("session", cookie, domain="test")
    return client


async def test_get_payment_rates_requires_auth(client):
    resp = await client.get("/api/config/payment-rates")
    assert resp.status_code == 401


async def test_get_payment_rates_returns_defaults(auth_client):
    resp = await auth_client.get("/api/config/payment-rates")
    assert resp.status_code == 200
    rates = resp.json()
    assert len(rates) == 2
    assert {"amount": 5, "days": 30} in rates
    assert {"amount": 10, "days": 60} in rates
