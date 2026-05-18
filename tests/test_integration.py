from fastapi.testclient import TestClient
from app.main import app
from app.db import reset_db

client = TestClient(app)

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


def test_full_user_flow():
    from app.db import reset_db
    reset_db()
    cookie = _login()

    resp = client.post("/api/customers", json={
        "name": "Sok Heng",
        "phone": "0888888001",
        "device_id": "Solar-001",
        "secret_key": TEST_KEY,
    }, cookies={"session": cookie})
    assert resp.status_code == 200
    cid = resp.json()["id"]

    resp = client.get("/api/customers", cookies={"session": cookie})
    customers = resp.json()
    assert any(c["id"] == cid for c in customers)

    resp = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.json()["name"] == "Sok Heng"

    resp = client.post(f"/api/customers/{cid}/token", json={
        "days": 30,
    }, cookies={"session": cookie})
    assert resp.status_code == 200
    token_data = resp.json()
    assert len(token_data["token"]) == 9
    assert token_data["days"] == 30

    resp = client.get("/api/tokens", cookies={"session": cookie})
    tokens = resp.json()
    assert len(tokens) == 1
    assert tokens[0]["customer_id"] == cid

    resp = client.delete(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.json()["ok"] is True

    resp = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.status_code == 404


def test_login_flow():
    resp = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert "用户名或密码错误" in resp.text

    resp = client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"

    cookie = resp.cookies.get("session")
    resp = client.get("/logout", cookies={"session": cookie}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_ui_pages_render():
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "PAYGO Solar" in resp.text
    assert "/static/style.css" in resp.text

    login_resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    cookie = login_resp.cookies.get("session")
    resp = client.get("/dashboard", cookies={"session": cookie})
    assert resp.status_code == 200
    assert "客户列表" in resp.text
    assert "模拟支付" in resp.text
    assert "锁定设备" in resp.text
    assert "永久解锁" in resp.text
