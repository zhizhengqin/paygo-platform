"""集成测试 — 端到端流程验证 (async + PostgreSQL + Redis)。"""
import secrets

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _key() -> str:
    return secrets.token_hex(16)


def _device_id() -> str:
    return f"DEV-{secrets.token_hex(3)}"


@pytest.fixture(autouse=True)
async def setup_redis():
    from app.redis import init_redis, close_redis
    r = await init_redis()
    await r.flushdb()
    yield
    await r.flushdb()
    await close_redis()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client):
    resp = await client.post("/login", data={"username": "admin", "password": "admin123"})
    sid = resp.cookies.get("session")
    client.cookies.set("session", sid)
    return sid


class TestFullUserFlow:
    async def test_full_crud_and_token(self, client):
        sid = await _login(client)

        # Create customer
        resp = await client.post("/api/customers", json={
            "name": "Sok Heng",
            "phone": "0888888001",
            "device_id": _device_id(),
            "secret_key": _key(),
        })
        assert resp.status_code == 200
        cid = resp.json()["id"]

        # List customers
        resp = await client.get("/api/customers")
        customers = resp.json()
        assert any(c["id"] == cid for c in customers)

        # Get customer detail
        resp = await client.get(f"/api/customers/{cid}")
        assert resp.json()["name"] == "Sok Heng"

        # Generate token
        resp = await client.post(f"/api/customers/{cid}/token", json={
            "days": 30,
        })
        assert resp.status_code == 200
        token_data = resp.json()
        assert len(token_data["token"]) == 9
        assert token_data["days"] == 30

        # List tokens
        resp = await client.get("/api/tokens")
        tokens = resp.json()
        assert any(t["customer_id"] == cid for t in tokens)

        # Delete customer
        resp = await client.delete(f"/api/customers/{cid}")
        assert resp.json()["ok"] is True

        # Verify deleted
        resp = await client.get(f"/api/customers/{cid}")
        assert resp.status_code == 404


class TestLoginFlow:
    async def test_wrong_password_shows_error(self, client):
        resp = await client.post("/login", data={"username": "admin", "password": "wrong"})
        assert resp.status_code == 200
        assert "用户名或密码错误" in resp.text

    async def test_login_redirects_to_dashboard(self, client):
        resp = await client.post("/login", data={
            "username": "admin",
            "password": "admin123",
        }, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/dashboard"

    async def test_logout_redirects_to_login(self, client):
        sid = await _login(client)
        resp = await client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"


class TestUIPagesRender:
    async def test_login_page_renders(self, client):
        resp = await client.get("/login")
        assert resp.status_code == 200
        assert "太阳能即付即用系统" in resp.text or "login" in resp.text.lower()

    async def test_dashboard_renders_when_authenticated(self, client):
        sid = await _login(client)
        resp = await client.get("/dashboard")
        assert resp.status_code == 200
