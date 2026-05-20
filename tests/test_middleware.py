"""测试中间件 — 限流 + 请求日志"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="module", autouse=True)
async def isolate_rate_limit_tests():
    """为中间件测试启用限流，并在测试结束后清理 Redis 限流/锁定键，
    避免污染后续测试模块。"""
    from app.redis import get_redis

    os.environ["RATE_LIMIT_ENABLED"] = "1"
    yield
    os.environ["RATE_LIMIT_ENABLED"] = "0"
    # 清理测试产生的 Redis 键
    r = get_redis()
    if r:
        for pattern in ("ratelimit:*", "login_failed:*", "login_locked:*"):
            keys = await r.keys(pattern)
            if keys:
                await r.delete(*keys)


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
