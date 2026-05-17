from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="templates")

HARDCODED_USERNAME = "admin"
HARDCODED_PASSWORD = "admin123"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """渲染登录页"""
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    """验证用户名密码，设置 session cookie，重定向到 dashboard"""
    if username == HARDCODED_USERNAME and password == HARDCODED_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session", value="authenticated")
        return response
    # 密码错误，重新渲染登录页并显示错误
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "用户名或密码错误"},
        status_code=200,
    )


@router.get("/logout")
async def logout():
    """登出：删除 session cookie，重定向到登录页"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session")
    return response
