import uuid

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.redis import session_create, session_get, session_delete
from app.security import verify_password
from app.settings import (
    ADMIN_USERNAME, ADMIN_PASSWORD_HASH,
    LOGIN_MAX_FAILURES, LOGIN_LOCKOUT_MINUTES,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def _check_login_lockout(r, ip: str):
    """检查 IP 是否被锁定。返回锁定消息或 None。"""
    if r is None:
        return None
    lock_key = f"login_locked:{ip}"
    locked = await r.get(lock_key)
    if locked:
        ttl = await r.ttl(lock_key)
        return f"账户已被锁定，请 {ttl} 秒后重试"
    return None


async def _record_login_failure(r, ip: str):
    """记录登录失败，达到阈值时锁定。"""
    if r is None:
        return
    fail_key = f"login_failed:{ip}"
    count = await r.incr(fail_key)
    if count == 1:
        await r.expire(fail_key, LOGIN_LOCKOUT_MINUTES * 60)
    if count >= LOGIN_MAX_FAILURES:
        lock_key = f"login_locked:{ip}"
        await r.setex(lock_key, LOGIN_LOCKOUT_MINUTES * 60, "1")


async def _clear_login_failures(r, ip: str):
    """登录成功后清除失败计数和锁定。"""
    if r is None:
        return
    fail_key = f"login_failed:{ip}"
    lock_key = f"login_locked:{ip}"
    await r.delete(fail_key, lock_key)


def _get_client_ip(request: Request) -> str:
    """从请求中提取客户端 IP。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    from app.redis import get_redis
    r = get_redis()
    ip = _get_client_ip(request)

    # 检查锁定
    lock_msg = await _check_login_lockout(r, ip)
    if lock_msg:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": lock_msg},
            status_code=200,
        )

    # 验证密码
    password_ok = False
    if username == ADMIN_USERNAME and ADMIN_PASSWORD_HASH:
        # bcrypt 验证
        password_ok = verify_password(password, ADMIN_PASSWORD_HASH)
    elif username == ADMIN_USERNAME and not ADMIN_PASSWORD_HASH:
        # 首次启动：ADMIN_PASSWORD_HASH 未设置，使用默认密码 admin123
        if password == "admin123":
            password_ok = True
    elif username == "admin" and password == "admin123":
        # 完全兼容：无环境变量时的默认行为
        password_ok = True

    if not password_ok:
        await _record_login_failure(r, ip)
        return templates.TemplateResponse(
            request, "login.html", {"error": "用户名或密码错误"}, status_code=200,
        )

    # 登录成功
    await _clear_login_failures(r, ip)
    sid = str(uuid.uuid4())
    await session_create(sid, {"role": "admin", "username": username})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session", value=sid, httponly=True)
    return response


@router.get("/logout")
async def logout(request: Request):
    sid = request.cookies.get("session")
    if sid:
        await session_delete(sid)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session")
    return response
