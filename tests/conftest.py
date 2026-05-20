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


@pytest.fixture(autouse=True)
def clear_db():
    """No-op: test isolation is handled by per-test DB session rollback."""
    pass
