from app.token_engine import generate_token


def test_generate_token_returns_8_digit_string():
    token = generate_token(device_id="Solar-001", days=30)
    assert isinstance(token, str)
    assert len(token) == 8
    assert token.isdigit()


def test_generate_token_is_random():
    t1 = generate_token(device_id="Solar-001", days=30)
    t2 = generate_token(device_id="Solar-001", days=30)
    # Both should be valid 8-digit strings
    assert isinstance(t1, str)
    assert isinstance(t2, str)
    assert len(t1) == 8
    assert len(t2) == 8
