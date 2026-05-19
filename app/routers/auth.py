import uuid

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.redis import session_create, session_get, session_delete

router = APIRouter()
templates = Jinja2Templates(directory="templates")

HARDCODED_USERNAME = "admin"
HARDCODED_PASSWORD = "admin123"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == HARDCODED_USERNAME and password == HARDCODED_PASSWORD:
        sid = str(uuid.uuid4())
        await session_create(sid, {"role": "admin", "username": username})
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session", value=sid, httponly=True)
        return response
    return templates.TemplateResponse(
        request, "login.html", {"error": "用户名或密码错误"}, status_code=200,
    )


@router.get("/logout")
async def logout(request: Request):
    sid = request.cookies.get("session")
    if sid:
        await session_delete(sid)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session")
    return response
