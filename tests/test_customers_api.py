from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


def test_create_customer():
    cookie = _login()
    response = client.post("/api/customers", json={
        "name": "Sok Heng",
        "phone": "0888888001",
        "device_id": "Solar-001",
    }, cookies={"session": cookie})
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("C")
    assert data["name"] == "Sok Heng"


def test_get_customers_list():
    cookie = _login()
    response = client.get("/api/customers", cookies={"session": cookie})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_customer_detail():
    cookie = _login()
    create_resp = client.post("/api/customers", json={
        "name": "Mary Keo",
        "phone": "0966666002",
        "device_id": "Solar-002",
    }, cookies={"session": cookie})
    cid = create_resp.json()["id"]
    response = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert response.status_code == 200
    assert response.json()["name"] == "Mary Keo"


def test_get_customer_not_found():
    cookie = _login()
    response = client.get("/api/customers/C999", cookies={"session": cookie})
    assert response.status_code == 404


def test_delete_customer():
    cookie = _login()
    create_resp = client.post("/api/customers", json={
        "name": "Delete Me",
        "phone": "000",
        "device_id": "D000",
    }, cookies={"session": cookie})
    cid = create_resp.json()["id"]
    response = client.delete(f"/api/customers/{cid}", cookies={"session": cookie})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_generate_token():
    cookie = _login()
    create_resp = client.post("/api/customers", json={
        "name": "Token Test",
        "phone": "0999999999",
        "device_id": "Solar-099",
    }, cookies={"session": cookie})
    cid = create_resp.json()["id"]
    response = client.post(f"/api/customers/{cid}/token", json={
        "days": 30,
    }, cookies={"session": cookie})
    assert response.status_code == 200
    data = response.json()
    assert len(data["token"]) == 15
    assert data["customer_id"] == cid
    assert data["days"] == 30


def test_get_tokens():
    cookie = _login()
    response = client.get("/api/tokens", cookies={"session": cookie})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_requires_auth():
    client.cookies.clear()
    response = client.get("/api/customers")
    assert response.status_code == 401


class TestSimulatePayment:
    def test_simulate_payment_requires_auth(self):
        resp = client.post("/api/customers/C001/simulate-payment", json={"amount": 5})
        assert resp.status_code == 401

    def test_simulate_payment_returns_token_and_sms(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) == 15
        assert data["days"] == 30
        assert "sms" in data
        assert data["sms"]["to"] == "0888888001"
        assert "PAYGO" in data["sms"]["message"]

    def test_simulate_payment_10_dollars_gives_60_days(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == 60

    def test_simulate_payment_nonexistent_customer(self):
        cookie = _login()
        resp = client.post(
            "/api/customers/NOEXIST/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 404

    def test_simulate_payment_unknown_amount(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 999},
            cookies={"session": cookie},
        )
        assert resp.status_code == 400


class TestLockDevice:
    def test_lock_device(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/lock",
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        customer = get_customer(cid)
        assert customer["status"] == "locked"

    def test_lock_requires_auth(self):
        client.cookies.clear()
        resp = client.post("/api/customers/C001/lock")
        assert resp.status_code == 401


class TestPermanentUnlock:
    def test_permanent_unlock_returns_disable_payg_token(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/permanent-unlock",
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) == 15
        # verify type=99
        assert data["token"][9:11] == "99"
        assert data["days"] == -1
        assert "sms" in data
        assert "全部结清" in data["sms"]["message"]

        customer = get_customer(cid)
        assert customer["status"] == "permanent"

    def test_permanent_unlock_requires_auth(self):
        client.cookies.clear()
        resp = client.post("/api/customers/C001/permanent-unlock")
        assert resp.status_code == 401
