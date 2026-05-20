import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from app.main import app
from app.database import AsyncSessionLocal
from app.redis import init_redis, close_redis, get_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_infra():
    await init_redis()
    yield
    await close_redis()
    from app.database import engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_db():
    async with AsyncSessionLocal() as db:
        # 按 FK 依赖倒序删除，避免外键约束冲突
        await db.execute(text("DELETE FROM repayment_records"))
        await db.execute(text("DELETE FROM repayment_schedules"))
        await db.execute(text("DELETE FROM contracts"))
        await db.execute(text("DELETE FROM alert_logs"))
        await db.execute(text("DELETE FROM alerts"))
        await db.execute(text("DELETE FROM tokens"))
        await db.execute(text("DELETE FROM sms_records"))
        await db.execute(text("DELETE FROM customers"))
        await db.execute(text("DELETE FROM loan_products"))
        await db.commit()

    # 清空 Redis 缓存，避免测试间缓存碰撞
    r = get_redis()
    if r:
        keys = await r.keys("dashboard:*")
        if keys:
            await r.delete(*keys)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(client):
    resp = await client.post(
        "/login", data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    cookie = resp.cookies.get("session")
    assert cookie is not None
    client.cookies.set("session", cookie, domain="test")
    return client


class TestDashboardStatsEmpty:
    async def test_dashboard_stats_empty(self, auth_client):
        resp = await auth_client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_customers"] == 0
        assert data["active_devices"] == 0
        assert data["monthly_revenue"] == 0
        assert data["locked_devices"] == 0
        assert data["permanent_devices"] == 0
        assert data["total_tokens"] == 0
        assert data["recent_transactions"] == []


class TestDashboardStatsWithData:
    async def test_dashboard_stats_with_data(self, auth_client):
        resp1 = await auth_client.post("/api/customers", json={
            "name": "Alice", "phone": "011222333", "device_id": "DEV-STATS-01",
            "secret_key": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        })
        assert resp1.status_code == 200, f"create Alice failed: {resp1.text}"

        resp2 = await auth_client.post("/api/customers", json={
            "name": "Bob", "phone": "044555666", "device_id": "DEV-STATS-02",
            "secret_key": "b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        })
        assert resp2.status_code == 200, f"create Bob failed: {resp2.text}"

        customers = (await auth_client.get("/api/customers")).json()
        alice = next(c for c in customers if c["name"] == "Alice")
        await auth_client.post(f"/api/customers/{alice['id']}/simulate-payment", json={"amount": 5})

        resp = await auth_client.get("/api/dashboard/stats")
        data = resp.json()
        assert data["total_customers"] == 2
        assert data["active_devices"] == 1
        assert data["monthly_revenue"] == 5.0
        assert data["total_tokens"] == 1
        assert len(data["recent_transactions"]) == 1
        assert data["recent_transactions"][0]["customer_name"] == "Alice"
        assert data["recent_transactions"][0]["amount"] == 5.0


class TestEnhancedDashboardStats:
    async def test_enhanced_dashboard_stats_empty(self, auth_client):
        resp = await auth_client.get("/api/dashboard/enhanced-stats?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "kpi" in data
        assert "revenue_trend" in data
        assert "token_trend" in data
        assert "alert_by_level" in data
        assert "alert_trend" in data
        assert len(data["revenue_trend"]) == 7
        assert len(data["token_trend"]) == 7
        assert len(data["alert_trend"]) == 7
        assert data["kpi"]["total_customers"] == 0
        assert data["alert_by_level"] == {"P0": 0, "P1": 0, "P2": 0}

    async def test_enhanced_dashboard_stats_with_data(self, auth_client):
        # Create a customer and simulate payment
        resp1 = await auth_client.post("/api/customers", json={
            "name": "Alice", "phone": "011222333", "device_id": "DEV-ENH-01",
            "secret_key": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        })
        assert resp1.status_code == 200
        customers = (await auth_client.get("/api/customers")).json()
        alice = next(c for c in customers if c["name"] == "Alice")
        await auth_client.post(
            f"/api/customers/{alice['id']}/simulate-payment",
            json={"amount": 5},
        )

        # Use days=14 to avoid cache collision with the empty test (days=7)
        resp = await auth_client.get("/api/dashboard/enhanced-stats?days=14")
        assert resp.status_code == 200
        data = resp.json()
        assert data["kpi"]["total_customers"] == 1
        assert data["kpi"]["active_devices"] == 1
        assert data["kpi"]["monthly_revenue"] == 5.0
        assert data["kpi"]["token_month"] == 1
        assert len(data["revenue_trend"]) == 14
