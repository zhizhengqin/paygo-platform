from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


def test_full_user_flow():
    cookie = _login()

    # 1. 创建客户
    resp = client.post("/api/customers", json={
        "name": "Sok Heng",
        "phone": "0888888001",
        "device_id": "Solar-001",
    }, cookies={"session": cookie})
    assert resp.status_code == 200
    cid = resp.json()["id"]

    # 2. 查看客户列表
    resp = client.get("/api/customers", cookies={"session": cookie})
    customers = resp.json()
    assert any(c["id"] == cid for c in customers)

    # 3. 查看客户详情
    resp = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.json()["name"] == "Sok Heng"

    # 4. 生成 Token
    resp = client.post(f"/api/customers/{cid}/token", json={
        "days": 30,
    }, cookies={"session": cookie})
    assert resp.status_code == 200
    token_data = resp.json()
    assert len(token_data["token"]) == 15
    assert token_data["days"] == 30

    # 5. 查看 Token 历史
    resp = client.get("/api/tokens", cookies={"session": cookie})
    tokens = resp.json()
    assert len(tokens) == 1
    assert tokens[0]["customer_id"] == cid

    # 6. 删除客户
    resp = client.delete(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.json()["ok"] is True

    # 7. 确认已删除
    resp = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.status_code == 404


def test_login_flow():
    # 错误密码
    resp = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert "用户名或密码错误" in resp.text

    # 正确登录
    resp = client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"

    # 登出
    cookie = resp.cookies.get("session")
    resp = client.get("/logout", cookies={"session": cookie}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_ui_pages_render():
    # 登录页
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "PAYGO Solar" in resp.text
    assert "/static/style.css" in resp.text

    # 主界面（需登录）
    login_resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    cookie = login_resp.cookies.get("session")
    resp = client.get("/dashboard", cookies={"session": cookie})
    assert resp.status_code == 200
    assert "客户列表" in resp.text
    assert "生成激活码" in resp.text
