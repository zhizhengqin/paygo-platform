"""合同与贷款产品 API 测试"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_infra():
    """Initialize Redis once for the test session."""
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
    """Login and set session cookie for authenticated requests."""
    resp = await client.post(
        "/login", data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    cookie = resp.cookies.get("session")
    assert cookie is not None
    client.cookies.set("session", cookie, domain="test")
    return client


@pytest.mark.asyncio
async def test_get_loan_products(auth_client):
    """获取贷款产品列表 — 种子数据有 5 个产品"""
    resp = await auth_client.get("/api/loan-products")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5


@pytest.mark.asyncio
async def test_create_loan_product(auth_client):
    """新增贷款产品"""
    resp = await auth_client.post("/api/loan-products", json={
        "name": "Test-6kW",
        "capacity_kw": 6.0,
        "term_months": 12,
        "interest_rate": 10.0,
        "down_payment_pct": 20.0,
        "total_amount": 690.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"].startswith("LP")
    assert data["name"] == "Test-6kW"


@pytest.mark.asyncio
async def test_create_contract(auth_client):
    """创建合同 — draft 状态"""
    products = (await auth_client.get("/api/loan-products")).json()
    customers = (await auth_client.get("/api/customers")).json()

    # 如果还没有客户，先创建一个
    if not customers:
        import secrets
        resp = await auth_client.post("/api/customers", json={
            "name": "Test Cust",
            "phone": "010000000",
            "device_id": f"DEV-{secrets.token_hex(3)}",
            "secret_key": secrets.token_hex(16),
        })
        assert resp.status_code == 200
        customers = [resp.json()]

    resp = await auth_client.post("/api/contracts", json={
        "customer_id": customers[0]["id"],
        "product_id": products[0]["id"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["contract_no"].startswith("KH-")
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_approve_contract(auth_client):
    """审批合同 → 生成还款计划，状态变 active"""
    products = (await auth_client.get("/api/loan-products")).json()
    customers = (await auth_client.get("/api/customers")).json()

    if not customers:
        import secrets
        resp = await auth_client.post("/api/customers", json={
            "name": "Test Cust",
            "phone": "010000001",
            "device_id": f"DEV-{secrets.token_hex(3)}",
            "secret_key": secrets.token_hex(16),
        })
        assert resp.status_code == 200
        customers = [resp.json()]

    c_resp = await auth_client.post("/api/contracts", json={
        "customer_id": customers[0]["id"],
        "product_id": products[0]["id"],
    })
    contract_id = c_resp.json()["id"]

    resp = await auth_client.put(f"/api/contracts/{contract_id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert len(data["schedules"]) > 0


@pytest.mark.asyncio
async def test_contract_status_change(auth_client):
    """修改合同状态"""
    products = (await auth_client.get("/api/loan-products")).json()
    customers = (await auth_client.get("/api/customers")).json()

    if not customers:
        import secrets
        resp = await auth_client.post("/api/customers", json={
            "name": "Test Cust",
            "phone": "010000002",
            "device_id": f"DEV-{secrets.token_hex(3)}",
            "secret_key": secrets.token_hex(16),
        })
        assert resp.status_code == 200
        customers = [resp.json()]

    c_resp = await auth_client.post("/api/contracts", json={
        "customer_id": customers[0]["id"],
        "product_id": products[0]["id"],
    })
    cid = c_resp.json()["id"]

    resp = await auth_client.put(f"/api/contracts/{cid}/status", json={"status": "overdue"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "overdue"


@pytest.mark.asyncio
async def test_get_contract_list(auth_client):
    """获取合同列表"""
    resp = await auth_client.get("/api/contracts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
