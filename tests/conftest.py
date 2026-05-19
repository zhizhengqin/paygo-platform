import pytest
from app.db import reset_db

# pytest-asyncio: 自动识别 async 测试函数，无需 @pytest.mark.asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    config.option.asyncio_mode = "auto"

# ---------------------------------------------------------------------------
# Monkey-patch openpaygo to fix None-handling bug in _count_is_valid
# and update_used_counts.  Without these patches decode_token crashes
# with TypeError when used_counts=None (the library default).
# ---------------------------------------------------------------------------
from openpaygo.token_decode import OpenPAYGOTokenDecoder as _Decoder

_orig_count_is_valid = _Decoder._count_is_valid.__func__
_orig_update_used_counts = _Decoder.update_used_counts.__func__


@classmethod
def _patched_count_is_valid(cls, count, last_count, value, type, used_counts):
    if used_counts is None:
        used_counts = []
    return _orig_count_is_valid(cls, count, last_count, value, type, used_counts)


@classmethod
def _patched_update_used_counts(cls, past_used_counts, value, new_count, type):
    if not past_used_counts:
        past_used_counts = []
    return _orig_update_used_counts(cls, past_used_counts, value, new_count, type)


_Decoder._count_is_valid = _patched_count_is_valid
_Decoder.update_used_counts = _patched_update_used_counts


@pytest.fixture(autouse=True)
def clear_db():
    reset_db()
