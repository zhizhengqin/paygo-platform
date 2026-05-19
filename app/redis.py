"""Redis 客户端 — session 管理 + API 响应缓存 + Token 防重放。"""
import json
from typing import Optional

import redis.asyncio as aioredis

from app.settings import REDIS_URL, CACHE_TTL_API, SESSION_TTL, ANTIREPLAY_TTL

_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    global _client
    _client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _client


async def close_redis():
    global _client
    if _client:
        await _client.aclose()
        _client = None


def get_redis() -> Optional[aioredis.Redis]:
    return _client


# ---- Session ----

async def session_create(sid: str, data: dict) -> str:
    """创建 Redis session，返回 session_id。"""
    r = get_redis()
    if r:
        await r.setex(f"session:{sid}", SESSION_TTL, json.dumps(data))
    return sid


async def session_get(sid: str) -> Optional[dict]:
    """读取 session，命中则自动续期 TTL。"""
    r = get_redis()
    if r is None:
        return None
    key = f"session:{sid}"
    data = await r.get(key)
    if data is None:
        return None
    await r.expire(key, SESSION_TTL)
    return json.loads(data)


async def session_delete(sid: str):
    r = get_redis()
    if r:
        await r.delete(f"session:{sid}")


# ---- API Cache ----

async def cache_get(key: str) -> Optional[dict]:
    r = get_redis()
    if r is None:
        return None
    data = await r.get(f"cache:{key}")
    return json.loads(data) if data else None


async def cache_set(key: str, value, ttl: int = CACHE_TTL_API):
    r = get_redis()
    if r:
        await r.setex(f"cache:{key}", ttl, json.dumps(value, default=str))


async def cache_delete(pattern: str):
    """删除匹配模式的所有缓存 key。"""
    r = get_redis()
    if r:
        keys = await r.keys(f"cache:{pattern}")
        if keys:
            await r.delete(*keys)


# ---- Antireplay ----

async def antireplay_check_and_mark(device_id: str, count: int) -> bool:
    """检查 (device_id, count) 是否已使用。首次使用返回 True 并标记，重放返回 False。"""
    r = get_redis()
    if r is None:
        return True  # Redis 不可用时降级放行
    key = f"antireplay:{device_id}:{count}"
    was_set = await r.setnx(key, "1")
    if was_set:
        await r.expire(key, ANTIREPLAY_TTL)
    return was_set
