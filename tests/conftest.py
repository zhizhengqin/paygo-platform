import os
import pytest

# pytest-asyncio: 自动识别 async 测试函数，无需 @pytest.mark.asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    config.option.asyncio_mode = "auto"
    # Set session-scoped event loop to avoid "different loop" errors
    # with SQLAlchemy async engine (created at module import time)
    config.inicfg["asyncio_default_test_loop_scope"] = "session"
    config.inicfg["asyncio_default_fixture_loop_scope"] = "session"
    # 测试模式下禁用 API 限流，避免大量测试请求触发 429
    os.environ.setdefault("RATE_LIMIT_ENABLED", "0")

# ---------------------------------------------------------------------------
# Monkey-patch openpaygo to fix None-handling bugs in _count_is_valid
# and update_used_counts.  Without these patches decode_token crashes
# with TypeError when used_counts=None (the library default).
#
# The upstream update_used_counts has a secondary bug: "if not past_used_counts"
# returns None for both None AND an empty list ([]), which breaks replay
# detection.  We fully reimplement the method to handle both cases correctly.
# ---------------------------------------------------------------------------
from openpaygo.token_decode import OpenPAYGOTokenDecoder as _Decoder
from openpaygo.token_shared import OpenPAYGOTokenShared

_orig_count_is_valid = _Decoder._count_is_valid.__func__


@classmethod
def _patched_count_is_valid(cls, count, last_count, value, type, used_counts):
    if used_counts is None:
        used_counts = []
    return _orig_count_is_valid(cls, count, last_count, value, type, used_counts)


@classmethod
def _patched_update_used_counts(cls, past_used_counts, value, new_count, type):
    if past_used_counts is None:
        past_used_counts = []
    highest_count = max(past_used_counts) if past_used_counts else 0
    if new_count > highest_count:
        highest_count = new_count
    bottom_range = highest_count - cls.MAX_UNUSED_OLDER_TOKENS
    used_counts = []
    if (
        type != 1  # TokenType.ADD_TIME
        or value == OpenPAYGOTokenShared.COUNTER_SYNC_VALUE
        or value == OpenPAYGOTokenShared.PAYG_DISABLE_VALUE
    ):
        for count in range(bottom_range, highest_count + 1):
            used_counts.append(count)
    else:
        for count in range(bottom_range, highest_count + 1):
            if count == new_count or count in past_used_counts:
                used_counts.append(count)
    return used_counts


_Decoder._count_is_valid = _patched_count_is_valid
_Decoder.update_used_counts = _patched_update_used_counts


@pytest.fixture(scope="session", autouse=True)
async def _run_app_lifespan():
    """Explicitly enter the app lifespan for the test session.
    ASGITransport in httpx 0.28 does NOT send lifespan events to the ASGI app,
    so DB tables, seed data, and Redis are never initialized unless we trigger
    the lifespan manually."""
    from app.main import lifespan, app
    async with lifespan(app):
        yield


@pytest.fixture(autouse=True)
def clear_db():
    """No-op: test isolation is handled by per-test DB session rollback."""
    pass


@pytest.fixture(scope="module", autouse=True)
async def _clean_redis_auth_state():
    """Clean Redis auth/lockout/ratelimit keys after each test module to prevent
    cross-module pollution.  Without this, test_auth.py's lockout tests leave
    login_locked:* keys with a 15-minute TTL, blocking all subsequent modules.
    """
    yield
    from app.redis import get_redis
    r = get_redis()
    if r:
        keys = []
        for pattern in ("login_failed:*", "login_locked:*", "ratelimit:*"):
            found = await r.keys(pattern)
            keys.extend(found)
        if keys:
            await r.delete(*keys)
