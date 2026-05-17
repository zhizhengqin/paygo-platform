from app.db import get_customers, get_tokens, add_customer, add_token, get_customer, delete_customer


def test_customers_starts_empty():
    store = get_customers()
    assert store == {}


def test_add_and_get_customer():
    cid = add_customer(name="Sok Heng", phone="0888888001", device_id="Solar-001")
    assert cid.startswith("C")
    customer = get_customer(cid)
    assert customer["name"] == "Sok Heng"
    assert customer["phone"] == "0888888001"
    assert customer["device_id"] == "Solar-001"
    assert customer["remaining_days"] == 0
    assert customer["status"] == "active"


def test_get_customer_not_found():
    assert get_customer("C999") is None


def test_delete_customer():
    cid = add_customer(name="Test", phone="000", device_id="D000")
    assert delete_customer(cid) is True
    assert get_customer(cid) is None


def test_delete_customer_not_found():
    assert delete_customer("C999") is False


def test_tokens_starts_empty():
    store = get_tokens()
    assert store == []


def test_add_token():
    tid = add_token(customer_id="C001", token="12345678", days=30)
    assert tid.startswith("T")
    tokens = get_tokens()
    assert len(tokens) == 1
    assert tokens[0]["customer_id"] == "C001"
    assert tokens[0]["days"] == 30
    assert "expires_at" in tokens[0]
