from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login_page_returns_html():
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_login_post_success_redirects():
    response = client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "session" in response.cookies


def test_login_post_wrong_password_shows_error():
    response = client.post("/login", data={
        "username": "admin",
        "password": "wrong",
    })
    assert response.status_code == 200
    assert "用户名或密码错误" in response.text


def test_dashboard_redirects_when_not_logged_in():
    client.cookies.clear()
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_dashboard_accessible_when_logged_in():
    login_response = client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    })
    session_cookie = login_response.cookies.get("session")
    response = client.get("/dashboard", cookies={"session": session_cookie})
    assert response.status_code == 200


def test_logout_clears_session():
    login_response = client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    })
    session_cookie = login_response.cookies.get("session")
    response = client.get("/logout", cookies={"session": session_cookie},
                          follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
