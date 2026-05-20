from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import Base
from app.database import engine, get_db
from app.redis import init_redis, close_redis
from app.security import init_fernet
from app.store import seed_payment_rates, seed_loan_products, seed_alert_rules, migrate_secret_keys_to_encrypted
from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router
from app.routers.config import router as config_router
from app.routers.dashboard import router as dashboard_router
from app.routers.contracts import router as contracts_router
from app.routers.tokens import router as tokens_router
from app.routers.alerts import router as alerts_router
from app.routers.reports import router as reports_router
from app.routers.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：创建表 + 初始化 Redis + 种子数据
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 临时手动迁移：添加 tokens.amount 列（后续表创建后可移除）
        from sqlalchemy import text
        await conn.run_sync(lambda c: c.execute(text(
            "ALTER TABLE tokens ADD COLUMN IF NOT EXISTS amount NUMERIC(10,2) DEFAULT 0"
        )))
        await conn.run_sync(lambda c: c.execute(text(
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS secret_key_encrypted TEXT"
        )))
        await conn.run_sync(lambda c: c.execute(text(
            "ALTER TABLE customers ALTER COLUMN secret_key DROP NOT NULL"
        )))
        await conn.run_sync(lambda c: c.execute(text(
            "ALTER TABLE tokens ADD COLUMN IF NOT EXISTS contract_id VARCHAR(8)"
        )))
        # Token 管理字段 (Phase 2)
        for col, col_type in [
            ("status", "VARCHAR(20) DEFAULT 'UNUSED'"),
            ("superseded_by", "VARCHAR(8)"),
            ("voided_at", "TIMESTAMP WITH TIME ZONE"),
            ("voided_by", "VARCHAR(100)"),
            ("void_reason", "TEXT"),
            ("ip_address", "VARCHAR(45)"),
            ("user_agent", "TEXT"),
        ]:
            await conn.run_sync(lambda c, col=col, col_type=col_type: c.execute(text(
                f"ALTER TABLE tokens ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )))
        # Phase 3 — Customer 扩展字段 + Mfi 表
        for col, col_type in [
            ("address", "TEXT"),
            ("gps_latitude", "NUMERIC(10,8)"),
            ("gps_longitude", "NUMERIC(11,8)"),
            ("id_number", "VARCHAR(50)"),
            ("mfi_id", "VARCHAR(8)"),
            ("tags", "JSONB DEFAULT '[]'::jsonb"),
        ]:
            await conn.run_sync(lambda c, col=col, col_type=col_type: c.execute(text(
                f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )))
        # Phase 4 — 告警相关表
        await conn.run_sync(lambda c: c.execute(text(
            """CREATE TABLE IF NOT EXISTS alert_rules (
                id VARCHAR(8) PRIMARY KEY, code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL, description TEXT, level VARCHAR(4) DEFAULT 'P2',
                sla_hours INTEGER DEFAULT 24, enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )""")))
        await conn.run_sync(lambda c: c.execute(text(
            """CREATE TABLE IF NOT EXISTS alerts (
                id VARCHAR(8) PRIMARY KEY, rule_code VARCHAR(20),
                contract_id VARCHAR(8), customer_id VARCHAR(8),
                level VARCHAR(4) DEFAULT 'P2', status VARCHAR(20) DEFAULT 'pending',
                title VARCHAR(200) NOT NULL, detail TEXT,
                triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                claimed_by VARCHAR(100), claimed_at TIMESTAMP WITH TIME ZONE,
                resolved_at TIMESTAMP WITH TIME ZONE, resolution_note TEXT
            )""")))
        await conn.run_sync(lambda c: c.execute(text(
            """CREATE TABLE IF NOT EXISTS alert_logs (
                id VARCHAR(8) PRIMARY KEY, alert_id VARCHAR(8),
                action VARCHAR(50) NOT NULL, operator VARCHAR(100),
                note TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )""")))
        # Phase 8 — 用户 + SMS模板
        await conn.run_sync(lambda c: c.execute(text(
            """CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(8) PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL, role VARCHAR(30) DEFAULT 'readonly',
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )""")))
        await conn.run_sync(lambda c: c.execute(text(
            """CREATE TABLE IF NOT EXISTS sms_templates (
                id VARCHAR(8) PRIMARY KEY, code VARCHAR(30) NOT NULL,
                language VARCHAR(5) DEFAULT 'zh', content TEXT NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )""")))
    await init_redis()
    init_fernet()
    # 种子支付汇率
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_payment_rates(db)
        await seed_loan_products(db)
        await seed_alert_rules(db)
        migrated = await migrate_secret_keys_to_encrypted(db)
        if migrated > 0:
            import logging
            logging.getLogger("paygo").info(f"Migrated {migrated} secret keys to encrypted storage")
    yield
    # 关闭：释放连接池 + 关闭 Redis
    await engine.dispose()
    await close_redis()


app = FastAPI(title="Cambodia Solar PAYGO Platform", lifespan=lifespan)

from app.middleware import RateLimiterMiddleware, RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimiterMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(config_router)
app.include_router(dashboard_router)
app.include_router(contracts_router)
app.include_router(tokens_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(settings_router)


@app.get("/dashboard")
async def dashboard(request: Request):
    from app.redis import session_get
    sid = request.cookies.get("session")
    if not sid or await session_get(sid) is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html")
