"""告警 API 测试"""
import secrets
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis

@pytest.fixture(scope="session", autouse=True)
async def manage_infra():
    await init_redis(); yield; await close_redis()
    from app.database import engine; await engine.dispose()

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac: yield ac

@pytest.fixture
async def auth_client(client):
    resp = await client.post("/login", data={"username":"admin","password":"admin123"}, follow_redirects=False)
    assert resp.status_code == 303
    cookie = resp.cookies.get("session"); assert cookie is not None
    client.cookies.set("session", cookie, domain="test"); return client

@pytest.mark.asyncio
async def test_get_alert_rules(auth_client):
    resp = await auth_client.get("/api/alerts/rules")
    assert resp.status_code == 200 and len(resp.json()) >= 3

@pytest.mark.asyncio
async def test_get_alert_stats(auth_client):
    resp = await auth_client.get("/api/alerts/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data and "pending" in data

@pytest.mark.asyncio
async def test_get_alert_list(auth_client):
    resp = await auth_client.get("/api/alerts")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_create_and_claim_alert(auth_client):
    # 创建告警
    resp = await auth_client.post("/api/alerts", json={
        "rule_code":"ALM-001","title":"测试告警","detail":"测试","level":"P2"
    })
    assert resp.status_code == 200
    aid = resp.json()["id"]
    # 认领
    resp = await auth_client.post(f"/api/alerts/{aid}/claim")
    assert resp.status_code == 200
    # 验证
    detail = (await auth_client.get(f"/api/alerts/{aid}")).json()
    assert detail["status"] == "claimed"

@pytest.mark.asyncio
async def test_escalate_alert(auth_client):
    resp = await auth_client.post("/api/alerts", json={
        "rule_code":"ALM-002","title":"P2告警","level":"P2"
    })
    aid = resp.json()["id"]
    resp = await auth_client.post(f"/api/alerts/{aid}/escalate")
    assert resp.status_code == 200
    detail = (await auth_client.get(f"/api/alerts/{aid}")).json()
    assert detail["level"] == "P1"
