from fastapi.testclient import TestClient
from app.main import app
from app.db import reset_db

client = TestClient(app)

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


class TestCreateCustomer:
    def test_create_customer_with_secret_key(self):
        from app.db import reset_db
        reset_db()
        cookie = _login()
        response = client.post("/api/customers", json={
            "name": "Sok Heng",
            "phone": "0888888001",
            "device_id": "Solar-001",
            "secret_key": TEST_KEY,
        }, cookies={"session": cookie})
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("C")
        assert data["name"] == "Sok Heng"
        assert data["secret_key"] == TEST_KEY
        assert data["count"] == 0

    def test_invalid_secret_key_rejected(self):
        cookie = _login()
        response = client.post("/api/customers", json={
            "name": "Bad Key",
            "phone": "000",
            "device_id": "D000",
            "secret_key": "too-short",
        }, cookies={"session": cookie})
        assert response.status_code == 400
        assert "secret_key" in response.json()["detail"]


class TestGetCustomers:
    def test_list(self):
        cookie = _login()
        response = client.get("/api/customers", cookies={"session": cookie})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_detail(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Mary Keo", "0966666002", "Solar-002", TEST_KEY)
        cookie = _login()
        response = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
        assert response.status_code == 200
        assert response.json()["name"] == "Mary Keo"

    def test_not_found(self):
        cookie = _login()
        response = client.get("/api/customers/C999", cookies={"session": cookie})
        assert response.status_code == 404

    def test_delete(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Delete Me", "000", "D000", TEST_KEY)
        cookie = _login()
        response = client.delete(f"/api/customers/{cid}", cookies={"session": cookie})
        assert response.status_code == 200
        assert response.json()["ok"] is True


class TestGenerateToken:
    def test_returns_9_digit_token(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Token Test", "0999999999", "Solar-099", TEST_KEY)
        cookie = _login()
        response = client.post(f"/api/customers/{cid}/token", json={
            "days": 30,
        }, cookies={"session": cookie})
        assert response.status_code == 200
        data = response.json()
        assert len(data["token"]) == 9
        assert data["token"].isdigit()
        assert data["customer_id"] == cid
        assert data["days"] == 30

    def test_two_generations_different_tokens(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Token Test", "0999999999", "Solar-099", TEST_KEY)
        cookie = _login()
        r1 = client.post(f"/api/customers/{cid}/token", json={
            "days": 30,
        }, cookies={"session": cookie})
        r2 = client.post(f"/api/customers/{cid}/token", json={
            "days": 30,
        }, cookies={"session": cookie})
        t1 = r1.json()["token"]
        t2 = r2.json()["token"]
        assert t1 != t2, f"Same device+days should produce DIFFERENT tokens: {t1}"


class TestListTokens:
    def test_list_tokens(self):
        cookie = _login()
        response = client.get("/api/tokens", cookies={"session": cookie})
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestAuth:
    def test_api_requires_auth(self):
        client.cookies.clear()
        response = client.get("/api/customers")
        assert response.status_code == 401


class TestSimulatePayment:
    def test_requires_auth(self):
        resp = client.post("/api/customers/C001/simulate-payment", json={"amount": 5})
        assert resp.status_code == 401

    def test_returns_9_digit_token_and_sms(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["token"]
        assert len(token) == 9
        assert token.isdigit()
        assert data["days"] == 30
        assert "sms" in data
        assert data["sms"]["to"] == "0888888001"
        assert "PAYGO" in data["sms"]["message"]
        assert token in data["sms"]["message"]

    def test_10_dollars_gives_60_days(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["days"] == 60

    def test_nonexistent_customer(self):
        cookie = _login()
        resp = client.post(
            "/api/customers/NOEXIST/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 404

    def test_unknown_amount(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 999},
            cookies={"session": cookie},
        )
        assert resp.status_code == 400

    def test_two_payments_different_tokens(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        r1 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        r2 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        assert r1.json()["token"] != r2.json()["token"]


class TestLockDevice:
    def test_lock_device(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(f"/api/customers/{cid}/lock", cookies={"session": cookie})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        customer = get_customer(cid)
        assert customer["status"] == "locked"

    def test_lock_requires_auth(self):
        client.cookies.clear()
        resp = client.post("/api/customers/C001/lock")
        assert resp.status_code == 401


class TestPermanentUnlock:
    def test_returns_9_digit_permanent_token(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/permanent-unlock",
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) == 9
        assert data["token"].isdigit()
        assert data["days"] == -1
        assert "sms" in data
        assert "全部结清" in data["sms"]["message"]

        customer = get_customer(cid)
        assert customer["status"] == "permanent"

    def test_requires_auth(self):
        client.cookies.clear()
        resp = client.post("/api/customers/C001/permanent-unlock")
        assert resp.status_code == 401
