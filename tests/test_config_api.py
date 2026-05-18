from fastapi.testclient import TestClient
from app.main import app
from app.db import reset_db

client = TestClient(app)


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


def test_get_payment_rates_requires_auth():
    resp = client.get("/api/config/payment-rates")
    assert resp.status_code == 401


def test_get_payment_rates_returns_defaults():
    reset_db()
    cookie = _login()
    resp = client.get("/api/config/payment-rates", cookies={"session": cookie})
    assert resp.status_code == 200
    rates = resp.json()
    assert len(rates) == 2
    assert {"amount": 5, "days": 30} in rates
    assert {"amount": 10, "days": 60} in rates
