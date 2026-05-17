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
    assert len(data["token"]) == 8
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
