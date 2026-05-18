import pytest
from controller.token_codec import generate, decode


class TestGenerate:
    def test_returns_15_digit_string(self):
        token = generate("Solar-001", 30)
        assert len(token) == 15
        assert token.isdigit()

    def test_known_device_30_days(self):
        token = generate("Solar-001", 30)
        char_sum = sum(ord(c) for c in "Solar-001")
        dh = char_sum % 100000
        cs = (dh + 30 + 1) % 10000
        assert token == f"{dh:05d}003001{cs:04d}"

    def test_different_device_different_hash(self):
        token_a = generate("Solar-001", 30)
        token_b = generate("Solar-002", 30)
        assert token_a[:5] != token_b[:5]

    def test_days_boundary_1(self):
        token = generate("X", 1)
        assert len(token) == 15
        assert token[5:9] == "0001"
        assert token.isdigit()

    def test_days_boundary_3650(self):
        token = generate("X", 3650)
        assert token[5:9] == "3650"


class TestDecode:
    def test_valid_token_returns_full_dict(self):
        char_sum = sum(ord(c) for c in "Solar-001")
        dh = char_sum % 100000
        cs = (dh + 30 + 1) % 10000
        token = f"{dh:05d}003001{cs:04d}"
        result = decode(token)
        assert result is not None
        assert result["device_id_hash"] == dh
        assert result["days"] == 30
        assert result["type"] == 1

    def test_invalid_checksum_returns_none(self):
        char_sum = sum(ord(c) for c in "Solar-001")
        dh = char_sum % 100000
        cs = (dh + 30 + 1) % 10000
        bad_cs = (cs + 1) % 10000
        token = f"{dh:05d}003001{bad_cs:04d}"
        assert decode(token) is None

    def test_wrong_length(self):
        assert decode("12345678901234") is None
        assert decode("1234567890123456") is None

    def test_non_numeric(self):
        assert decode("abc123456789012") is None

    def test_empty_string(self):
        assert decode("") is None


class TestRoundtrip:
    def test_generate_then_decode(self):
        device_id = "Solar-001"
        days = 30
        token = generate(device_id, days)
        result = decode(token)
        assert result is not None
        assert result["days"] == days
        assert result["type"] == 1

    def test_multiple_devices(self):
        for device_id in ["Solar-001", "Solar-002", "ABC-999"]:
            for days in [1, 30, 365, 3650]:
                token = generate(device_id, days)
                result = decode(token)
                assert result is not None
                assert result["days"] == days
                assert result["type"] == 1


class Test15DigitCodec:
    """15位Token编解码：{device_hash:5}{value:4}{type:2}{checksum:4}"""

    def test_generate_returns_15_digit(self):
        token = generate("Solar-001", 30)
        assert len(token) == 15
        assert token.isdigit()

    def test_generate_and_decode_roundtrip_type01(self):
        token = generate("Solar-001", 30)
        result = decode(token)
        assert result is not None
        assert result["days"] == 30
        assert result["type"] == 1

    def test_generate_disable_payg(self):
        token = generate("SN-KH-001", -1)
        result = decode(token)
        assert result is not None
        assert result["days"] == 0
        assert result["type"] == 99

    def test_decode_invalid_checksum(self):
        token = generate("X", 30)
        bad_token = token[:14] + str((int(token[14]) + 1) % 10)
        assert decode(bad_token) is None

    def test_decode_wrong_length(self):
        assert decode("12345678901234") is None   # 14位
        assert decode("1234567890123456") is None  # 16位

    def test_decode_non_numeric(self):
        assert decode("a" * 15) is None

    def test_decode_invalid_type(self):
        # 构造 type=02 (非法) 的 token
        char_sum = sum(ord(c) for c in "X")
        dh = char_sum % 100000
        cs = (dh + 30 + 2) % 10000
        token = f"{dh:05d}003002{cs:04d}"
        assert decode(token) is None

    def test_roundtrip_multiple(self):
        for device_id in ["Solar-001", "SN-KH-002", "ABC-999"]:
            for days in [1, 30, 365, 3650]:
                token = generate(device_id, days)
                result = decode(token)
                assert result is not None, f"decode failed for {device_id}/{days}"
                assert result["days"] == days
                assert result["type"] == 1


class TestLegacy8Digit:
    """8位旧格式Token应该被拒绝"""

    def test_old_8_digit_rejected(self):
        assert decode("07030303") is None

    def test_old_8_digit_generate_no_longer_works(self):
        token = generate("Solar-001", 30)
        assert len(token) == 15
