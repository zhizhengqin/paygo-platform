import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_redis():
    """Initialize Redis for the auth test session."""
    await init_redis()
    yield
    await close_redis()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_login_page_returns_html(client):
    response = await client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_login_post_success_redirects(client):
    response = await client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert "session" in response.cookies


async def test_login_post_wrong_password_shows_error(client):
    response = await client.post("/login", data={
        "username": "admin",
        "password": "wrong",
    })
    assert response.status_code == 200
    assert "用户名或密码错误" in response.text


async def test_dashboard_redirects_when_not_logged_in(client):
    client.cookies.clear()
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


async def test_dashboard_shows_when_authenticated(client):
    """Dashboard guard validates Redis sessions -- a valid session grants access."""
    client.cookies.clear()
    login_response = await client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    }, follow_redirects=False)
    session_cookie = login_response.cookies.get("session")
    assert session_cookie is not None
    client.cookies.set("session", session_cookie, domain="test")
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 200


async def test_logout_clears_session(client):
    client.cookies.clear()
    login_response = await client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    }, follow_redirects=False)
    assert "session" in login_response.cookies
    client.cookies.set("session", login_response.cookies.get("session"), domain="test")
    response = await client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
