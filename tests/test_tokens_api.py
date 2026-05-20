"""Token 管理 API 测试"""
import secrets
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_infra():
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
async def test_get_token_stats(auth_client):
    """Token 统计接口"""
    resp = await auth_client.get("/api/tokens/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "today" in data
    assert "this_month" in data


@pytest.mark.asyncio
async def test_get_token_list(auth_client):
    """Token 列表"""
    resp = await auth_client.get("/api/tokens?limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_token_detail(auth_client):
    """Token 详情"""
    tokens = (await auth_client.get("/api/tokens?limit=1")).json()
    if tokens:
        tid = tokens[0]["id"]
        resp = await auth_client.get(f"/api/tokens/{tid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "customer_name" in data


@pytest.mark.asyncio
async def test_void_token(auth_client):
    """作废 Token"""
    resp = await auth_client.post("/api/customers", json={
        "name": "VoidTest", "phone": "010000300",
        "device_id": f"DEV-{secrets.token_hex(3)}",
        "secret_key": secrets.token_hex(16),
    })
    cid = resp.json()["id"]
    await auth_client.post(f"/api/customers/{cid}/simulate-payment", json={"amount": 5.0})
    tokens = (await auth_client.get("/api/tokens?limit=10")).json()
    tid = tokens[0]["id"]

    resp = await auth_client.post(f"/api/tokens/{tid}/void", json={"reason": "测试作废"})
    assert resp.status_code == 200
    detail = (await auth_client.get(f"/api/tokens/{tid}")).json()
    assert detail["status"] == "SUPERSEDED"


@pytest.mark.asyncio
async def test_reissue_token(auth_client):
    """补发 Token"""
    resp = await auth_client.post("/api/customers", json={
        "name": "ReissueTest", "phone": "010000400",
        "device_id": f"DEV-{secrets.token_hex(3)}",
        "secret_key": secrets.token_hex(16),
    })
    cid = resp.json()["id"]
    await auth_client.post(f"/api/customers/{cid}/simulate-payment", json={"amount": 5.0})
    tokens = (await auth_client.get("/api/tokens?limit=10")).json()
    tid = tokens[0]["id"]

    resp = await auth_client.post(f"/api/tokens/{tid}/reissue", json={"reason": "SMS 未送达"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] is not None
    assert data["token"] != tokens[0]["token"]


@pytest.mark.asyncio
async def test_get_token_detail_nonexistent(auth_client):
    """不存在的 Token 返回 404"""
    resp = await auth_client.get("/api/tokens/NONEXIST")
    assert resp.status_code == 404
