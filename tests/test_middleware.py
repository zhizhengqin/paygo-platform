"""测试中间件 — 限流 + 请求日志"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_redis():
    await init_redis()
    yield
    await close_redis()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRateLimiter:
    async def test_rate_limited_after_100_requests(self, client):
        """超过 100 次/分钟后返回 429。"""
        resp = await client.post("/login", data={
            "username": "admin", "password": "admin123",
        }, follow_redirects=False)
        cookie = resp.cookies.get("session")
        if cookie:
            client.cookies.set("session", cookie, domain="test")

        responses = []
        for _ in range(101):
            r = await client.get("/api/customers")
            responses.append(r.status_code)

        assert 429 in responses

    async def test_login_endpoint_has_stricter_limit(self, client):
        """登录接口 10 次/min 限流更严格。"""
        responses = []
        for _ in range(15):
            r = await client.post("/login", data={
                "username": "admin", "password": "wrong",
            })
            responses.append(r.status_code)

        assert 429 in responses
