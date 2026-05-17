import pytest
from controller.token_codec import generate, decode


class TestGenerate:
    def test_returns_8_digit_string(self):
        token = generate("Solar-001", 30)
        assert len(token) == 8
        assert token.isdigit()

    def test_known_device_30_days(self):
        token = generate("Solar-001", 30)
        assert token == "07030303"

    def test_different_device_different_hash(self):
        token_a = generate("Solar-001", 30)
        token_b = generate("Solar-002", 30)
        assert token_a[:4] != token_b[:4]

    def test_days_boundary_1(self):
        token = generate("X", 1)
        assert len(token) == 8
        assert token[4:7] == "001"
        assert token.isdigit()

    def test_days_boundary_365(self):
        token = generate("X", 365)
        assert token[4:7] == "365"


class TestDecode:
    def test_valid_token_returns_device_hash_and_days(self):
        result = decode("07030303")
        assert result is not None
        assert result["device_id_hash"] == 703
        assert result["days"] == 30

    def test_invalid_checksum_returns_none(self):
        assert decode("07030304") is None

    def test_wrong_length(self):
        assert decode("1234567") is None
        assert decode("123456789") is None

    def test_non_numeric(self):
        assert decode("abc12345") is None

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

    def test_multiple_devices(self):
        for device_id in ["Solar-001", "Solar-002", "ABC-999"]:
            for days in [1, 30, 365]:
                token = generate(device_id, days)
                result = decode(token)
                assert result is not None
                assert result["days"] == days
