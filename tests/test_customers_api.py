import secrets

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


def _key() -> str:
    return secrets.token_hex(16)


def _device_id() -> str:
    return f"DEV-{secrets.token_hex(3)}"


TEST_KEY = _key()  # 向后兼容


@pytest.fixture(scope="session", autouse=True)
async def manage_infra():
    """Initialize Redis once for the test session, and clean up the DB engine
    afterwards so subsequent test files can create fresh connection pools."""
    await init_redis()
    yield
    await close_redis()
    # Dispose the async engine so other test files (e.g. TestClient-based)
    # can create fresh connections in their own event loops.
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


# ---------------------------------------------------------------------------
# Create Customer
# ---------------------------------------------------------------------------

class TestCreateCustomer:
    async def test_create_customer_with_secret_key(self, auth_client):
        key = _key()
        response = await auth_client.post("/api/customers", json={
            "name": "Sok Heng",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": key,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("C")
        assert data["name"] == "Sok Heng"
        assert data["secret_key"] == key
        assert data["count"] == 0

    async def test_invalid_secret_key_rejected(self, auth_client):
        response = await auth_client.post("/api/customers", json={
            "name": "Bad Key",
            "phone": "000",
            "device_id": _device_id(),
            "secret_key": "too-short",
        })
        assert response.status_code == 400
        assert "secret_key" in response.json()["detail"]

    async def test_duplicate_device_id_returns_409(self, auth_client):
        dup_device_id = _device_id()
        await auth_client.post("/api/customers", json={
            "name": "First", "phone": "1",
            "device_id": dup_device_id,
            "secret_key": _key(),
        })
        response = await auth_client.post("/api/customers", json={
            "name": "Second", "phone": "2",
            "device_id": dup_device_id,
            "secret_key": _key(),
        })
        assert response.status_code == 409
        assert dup_device_id in response.json()["detail"]

    async def test_duplicate_secret_key_returns_409(self, auth_client):
        dup_key = _key()
        await auth_client.post("/api/customers", json={
            "name": "First", "phone": "1",
            "device_id": _device_id(),
            "secret_key": dup_key,
        })
        response = await auth_client.post("/api/customers", json={
            "name": "Second", "phone": "2",
            "device_id": _device_id(),
            "secret_key": dup_key,
        })
        assert response.status_code == 409
        assert "密钥" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Get Customers
# ---------------------------------------------------------------------------

class TestGetCustomers:
    async def test_list(self, auth_client):
        response = await auth_client.get("/api/customers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_detail(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Mary Keo",
            "phone": "0966666002",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        response = await auth_client.get(f"/api/customers/{cid}")
        assert response.status_code == 200
        assert response.json()["name"] == "Mary Keo"

    async def test_not_found(self, auth_client):
        response = await auth_client.get("/api/customers/C99999")
        assert response.status_code == 404

    async def test_delete(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Delete Me",
            "phone": "000",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        response = await auth_client.delete(f"/api/customers/{cid}")
        assert response.status_code == 200
        assert response.json()["ok"] is True


# ---------------------------------------------------------------------------
# Generate Token
# ---------------------------------------------------------------------------

class TestGenerateToken:
    async def test_returns_9_digit_token(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Token Test",
            "phone": "0999999999",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        response = await auth_client.post(
            f"/api/customers/{cid}/token", json={"days": 30},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["token"]) == 9
        assert data["token"].isdigit()
        assert data["customer_id"] == cid
        assert data["days"] == 30

    async def test_two_generations_different_tokens(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Token Test 2",
            "phone": "0999999998",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        r1 = await auth_client.post(
            f"/api/customers/{cid}/token", json={"days": 30},
        )
        r2 = await auth_client.post(
            f"/api/customers/{cid}/token", json={"days": 30},
        )
        t1 = r1.json()["token"]
        t2 = r2.json()["token"]
        assert t1 != t2, f"Same device+days should produce DIFFERENT tokens: {t1}"


# ---------------------------------------------------------------------------
# List Tokens
# ---------------------------------------------------------------------------

class TestListTokens:
    async def test_list_tokens(self, auth_client):
        response = await auth_client.get("/api/tokens")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    async def test_api_requires_auth(self, client):
        response = await client.get("/api/customers")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Simulate Payment
# ---------------------------------------------------------------------------

class TestSimulatePayment:
    async def test_requires_auth(self, client):
        resp = await client.post(
            "/api/customers/C001/simulate-payment", json={"amount": 5},
        )
        assert resp.status_code == 401

    async def test_returns_9_digit_token_and_sms(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Payment Test",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        resp = await auth_client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["token"]
        assert len(token) == 9
        assert token.isdigit()
        assert data["days"] == 30
        assert "sms" in data
        assert data["sms"]["to"] == "0888888001"
        assert "PAYGO" in data["sms"]["message"]
        assert token in data["sms"]["message"]

    async def test_10_dollars_gives_60_days(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Payment Test 10",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        resp = await auth_client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["days"] == 60

    async def test_nonexistent_customer(self, auth_client):
        resp = await auth_client.post(
            "/api/customers/NOEXIST/simulate-payment",
            json={"amount": 5},
        )
        assert resp.status_code == 404

    async def test_unknown_amount(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Payment Test Unknown",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        resp = await auth_client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 999},
        )
        assert resp.status_code == 400

    async def test_two_payments_different_tokens(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "TwoPay Test",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        r1 = await auth_client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
        )
        r2 = await auth_client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
        )
        assert r1.json()["token"] != r2.json()["token"]


# ---------------------------------------------------------------------------
# Lock Device
# ---------------------------------------------------------------------------

class TestLockDevice:
    async def test_lock_device(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "Lock Test",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        resp = await auth_client.post(f"/api/customers/{cid}/lock")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        # Verify status is locked via GET
        detail = await auth_client.get(f"/api/customers/{cid}")
        assert detail.json()["status"] == "locked"

    async def test_lock_requires_auth(self, client):
        resp = await client.post("/api/customers/C001/lock")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Permanent Unlock
# ---------------------------------------------------------------------------

class TestPermanentUnlock:
    async def test_returns_9_digit_permanent_token(self, auth_client):
        resp = await auth_client.post("/api/customers", json={
            "name": "PermUnlock Test",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        cid = resp.json()["id"]
        resp = await auth_client.post(
            f"/api/customers/{cid}/permanent-unlock",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) == 9
        assert data["token"].isdigit()
        assert data["days"] == -1
        assert "sms" in data
        assert "全部结清" in data["sms"]["message"]
        # Verify status is permanent via GET
        detail = await auth_client.get(f"/api/customers/{cid}")
        assert detail.json()["status"] == "permanent"

    async def test_requires_auth(self, client):
        resp = await client.post("/api/customers/C001/permanent-unlock")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Customer 360 / Filters / Tags / MFI
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_customers_search(auth_client):
    """搜索筛选"""
    resp = await auth_client.get("/api/customers?search=Test")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_get_customer_360(auth_client):
    """客户360视图"""
    customers = (await auth_client.get("/api/customers")).json()
    if customers:
        cid = customers[0]["id"]
        resp = await auth_client.get(f"/api/customers/{cid}/360")
        assert resp.status_code == 200
        data = resp.json()
        assert "customer" in data
        assert "contracts" in data
        assert "tokens" in data

@pytest.mark.asyncio
async def test_mfi_crud(auth_client):
    """MFI 机构 CRUD"""
    resp = await auth_client.post("/api/mfis", json={"name":"LOLC","branch":"PP"})
    assert resp.status_code == 200
    mfis = (await auth_client.get("/api/mfis")).json()
    assert len(mfis) >= 1

@pytest.mark.asyncio
async def test_update_tags(auth_client):
    """客户标签更新"""
    customers = (await auth_client.get("/api/customers")).json()
    if customers:
        cid = customers[0]["id"]
        resp = await auth_client.put(f"/api/customers/{cid}/tags",
            json={"tags":["VIP","高风险"]})
        assert resp.status_code == 200
