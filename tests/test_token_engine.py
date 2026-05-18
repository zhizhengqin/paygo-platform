"""测试 Token 引擎（结构化编码版本）。"""
import pytest
from app.token_engine import generate_token


def test_generate_returns_15_digit_string():
    token = generate_token("Solar-001", 30)
    assert len(token) == 15
    assert token.isdigit()


def test_generate_known_device_known_days():
    token = generate_token("Solar-001", 30)
    char_sum = sum(ord(c) for c in "Solar-001")
    expected_hash = char_sum % 100000
    expected = f"{expected_hash:05d}003001{((expected_hash + 30 + 1) % 10000):04d}"
    assert token == expected


def test_same_device_same_days_same_token():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 30)
    assert t1 == t2


def test_different_device_different_hash():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-002", 30)
    assert t1[:5] != t2[:5]


def test_different_days_different_token():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 60)
    assert t1 != t2


def test_days_1():
    token = generate_token("X", 1)
    assert token[5:9] == "0001"


def test_days_365():
    token = generate_token("X", 365)
    assert token[5:9] == "0365"


class Test15DigitToken:
    """15位Token编码：{device_hash:5}{value:4}{type:2}{checksum:4}"""

    def test_generate_returns_15_digit_string(self):
        token = generate_token("Solar-001", 30)
        assert len(token) == 15
        assert token.isdigit()

    def test_known_device_30_days_15digit(self):
        token = generate_token("Solar-001", 30)
        # device_hash = sum(ord(c) for c in "Solar-001") % 100000
        char_sum = sum(ord(c) for c in "Solar-001")
        expected_hash = char_sum % 100000
        expected_value = 30
        expected_type = 1
        expected_checksum = (expected_hash + expected_value + expected_type) % 10000
        expected = f"{expected_hash:05d}{expected_value:04d}01{expected_checksum:04d}"
        assert token == expected

    def test_generate_disabled(self):
        token = generate_token("SN-KH-001", -1)  # -1 signals DISABLE_PAYG
        # type=99, value=0000
        char_sum = sum(ord(c) for c in "SN-KH-001")
        expected_hash = char_sum % 100000
        expected_checksum = (expected_hash + 0 + 99) % 10000
        expected = f"{expected_hash:05d}000099{expected_checksum:04d}"
        assert token == expected

    def test_days_boundary_1(self):
        token = generate_token("X", 1)
        assert token[5:9] == "0001"
        assert token[9:11] == "01"

    def test_days_boundary_3650(self):
        token = generate_token("X", 3650)
        assert token[5:9] == "3650"

    def test_empty_device_id_works(self):
        token = generate_token("", 30)
        assert len(token) == 15
        assert token.isdigit()
        assert token[:5] == "00000"

    def test_days_zero_raises_valueerror(self):
        with pytest.raises(ValueError):
            generate_token("X", 0)

    def test_days_3651_raises_valueerror(self):
        with pytest.raises(ValueError):
            generate_token("X", 3651)

    def test_days_negative_raises_valueerror(self):
        with pytest.raises(ValueError):
            generate_token("X", -5)
