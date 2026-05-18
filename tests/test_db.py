from app.db import (
    get_customers, get_tokens, add_customer, add_token, get_customer,
    delete_customer, reset_db,
)


def test_customers_starts_empty():
    reset_db()
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
    assert customer["status"] == "locked"


def test_get_customer_not_found():
    assert get_customer("C999") is None


def test_delete_customer():
    cid = add_customer(name="Test", phone="000", device_id="D000")
    assert delete_customer(cid) is True
    assert get_customer(cid) is None


def test_delete_customer_not_found():
    assert delete_customer("C999") is False


def test_tokens_starts_empty():
    reset_db()
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


from app.db import (
    get_payment_rates, get_days_for_amount,
    add_sms_record, get_sms_records,
    update_customer_status, add_customer as add_customer_new,
)


class TestPaymentRates:
    def test_default_rates_exist(self):
        reset_db()
        rates = get_payment_rates()
        assert len(rates) == 2
        assert rates[0] == {"amount": 5, "days": 30}
        assert rates[1] == {"amount": 10, "days": 60}

    def test_get_days_for_amount(self):
        assert get_days_for_amount(5) == 30
        assert get_days_for_amount(10) == 60
        assert get_days_for_amount(999) == 0

    def test_reset_restores_defaults(self):
        reset_db()
        _payment_rates = get_payment_rates()
        _payment_rates.clear()
        reset_db()
        assert len(get_payment_rates()) == 2


class TestSmsRecords:
    def test_add_and_get_sms(self):
        reset_db()
        sid = add_sms_record("C001", "0888888001", "Test message")
        assert sid.startswith("S")
        records = get_sms_records("C001")
        assert len(records) == 1
        assert records[0]["to"] == "0888888001"
        assert records[0]["message"] == "Test message"

    def test_get_all_sms(self):
        reset_db()
        add_sms_record("C001", "0888888001", "msg1")
        add_sms_record("C002", "0888888002", "msg2")
        all_records = get_sms_records()
        assert len(all_records) == 2


class TestCustomerStatus:
    def test_new_customer_defaults_locked(self):
        reset_db()
        cid = add_customer("Test", "0880000001", "SN-KH-001")
        c = get_customer(cid)
        assert c["status"] == "locked"

    def test_update_status(self):
        reset_db()
        cid = add_customer("Test", "0880000001", "SN-KH-001")
        assert update_customer_status(cid, "active")
        assert get_customer(cid)["status"] == "active"
        assert update_customer_status(cid, "permanent")
        assert get_customer(cid)["status"] == "permanent"

    def test_lock_sets_locked_at(self):
        reset_db()
        cid = add_customer("Test", "0880000001", "SN-KH-001")
        update_customer_status(cid, "locked")
        c = get_customer(cid)
        assert c["locked_at"] is not None

    def test_update_nonexistent_customer(self):
        assert not update_customer_status("NOEXIST", "active")
