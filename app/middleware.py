"""ASGI 中间件 — API 限流 + 请求日志"""
import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.settings import RATE_LIMIT_PER_MINUTE, LOGIN_RATE_LIMIT_PER_MINUTE

logger = logging.getLogger("paygo.middleware")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_rate_limit(path: str) -> int:
    """根据路径返回限流阈值。"""
    if "/login" in path:
        return LOGIN_RATE_LIMIT_PER_MINUTE
    return RATE_LIMIT_PER_MINUTE


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Redis 滑动窗口限流中间件。"""

    async def dispatch(self, request: Request, call_next):
        from app.redis import get_redis

        r = get_redis()
        if r is None:
            return await call_next(request)

        ip = _get_client_ip(request)
        path = request.url.path
        limit = _get_rate_limit(path)
        key = f"ratelimit:{ip}:{path}"

        current = await r.incr(key)
        if current == 1:
            await r.expire(key, 60)

        if current > limit:
            ttl = await r.ttl(key)
            return JSONResponse(
                status_code=429,
                content={"detail": f"请求过于频繁，请 {ttl} 秒后重试"},
                headers={"Retry-After": str(ttl)},
            )

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录所有 API 请求的方法、路径、状态码、耗时、IP。"""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        ip = _get_client_ip(request)
        logger.info(
            "request %s %s %s %.1fms %s",
            request.method, request.url.path,
            response.status_code, duration_ms, ip,
        )
        return response
