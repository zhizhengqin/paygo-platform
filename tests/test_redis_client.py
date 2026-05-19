"""redis.py 测试 — 连接、session 读写、API 缓存、防重放。"""
import pytest
from app.redis import (
    get_redis, init_redis, close_redis,
    session_create, session_get,
    cache_get, cache_set, cache_delete,
    antireplay_check_and_mark,
)


@pytest.fixture(autouse=True)
async def clean_redis():
    r = await init_redis()
    await r.flushdb()
    yield
    await r.flushdb()
    await close_redis()


class TestRedisConnection:
    async def test_redis_ping(self):
        r = get_redis()
        assert r is not None
        pong = await r.ping()
        assert pong is True


class TestSessionStore:
    async def test_session_create_and_get(self):
        await session_create("sess-1", {"role": "admin"})
        data = await session_get("sess-1")
        assert data == {"role": "admin"}

    async def test_session_not_found(self):
        data = await session_get("nonexistent")
        assert data is None

    async def test_session_expire(self):
        await session_create("sess-2", {"role": "admin"})
        r = get_redis()
        await r.expire("session:sess-2", 0)  # 立即过期
        data = await session_get("sess-2")
        assert data is None


class TestApiCache:
    async def test_cache_set_and_get(self):
        await cache_set("test:key", {"name": "value"})
        result = await cache_get("test:key")
        assert result == {"name": "value"}

    async def test_cache_miss(self):
        result = await cache_get("nonexistent:key")
        assert result is None

    async def test_cache_delete(self):
        await cache_set("test:del", "x")
        await cache_delete("test:del")
        assert await cache_get("test:del") is None


class TestAntireplay:
    async def test_first_use_allowed(self):
        allowed = await antireplay_check_and_mark("device-1", 1)
        assert allowed is True

    async def test_replay_blocked(self):
        await antireplay_check_and_mark("device-2", 1)
        allowed = await antireplay_check_and_mark("device-2", 1)
        assert allowed is False

    async def test_different_count_allowed(self):
        await antireplay_check_and_mark("device-3", 1)
        allowed = await antireplay_check_and_mark("device-3", 2)
        assert allowed is True
