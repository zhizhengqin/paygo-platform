from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router

app = FastAPI(title="Cambodia Solar PAYGO Platform")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化 Jinja2 模板引擎
templates = Jinja2Templates(directory="templates")

# 注册路由
app.include_router(auth_router)
app.include_router(customers_router)


@app.get("/dashboard")
async def dashboard(request: Request):
    """主面板：检查认证，未登录则重定向到登录页"""
    if request.cookies.get("session") != "authenticated":
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html")
