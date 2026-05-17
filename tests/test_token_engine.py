"""测试 Token 引擎（结构化编码版本）。"""
from app.token_engine import generate_token


def test_generate_returns_8_digit_string():
    token = generate_token("Solar-001", 30)
    assert len(token) == 8
    assert token.isdigit()


def test_generate_known_device_known_days():
    token = generate_token("Solar-001", 30)
    assert token == "07030303"


def test_same_device_same_days_same_token():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 30)
    assert t1 == t2


def test_different_device_different_hash():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-002", 30)
    assert t1[:4] != t2[:4]


def test_different_days_different_token():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 60)
    assert t1 != t2


def test_days_1():
    token = generate_token("X", 1)
    assert token[4:7] == "001"


def test_days_365():
    token = generate_token("X", 365)
    assert token[4:7] == "365"
