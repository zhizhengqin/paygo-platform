from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import Base
from app.database import engine, get_db
from app.redis import init_redis, close_redis
from app.store import seed_payment_rates
from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router
from app.routers.config import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：创建表 + 初始化 Redis + 种子数据
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    # 种子支付汇率
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_payment_rates(db)
    yield
    # 关闭：释放连接池 + 关闭 Redis
    await engine.dispose()
    await close_redis()


app = FastAPI(title="Cambodia Solar PAYGO Platform", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(config_router)


@app.get("/dashboard")
async def dashboard(request: Request):
    if request.cookies.get("session") != "authenticated":
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html")
