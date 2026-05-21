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
from app.routers.controller import router as controller_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：打印配置信息（密码已脱敏）
    import logging, re
    _log = logging.getLogger("paygo.startup")
    _mask = lambda u: re.sub(r'://[^:]+:[^@]+@', '://***:***@', u) if u else 'NOT SET'
    from app.settings import REDIS_URL
    _log.info(f"DATABASE_URL: {_mask(str(engine.url))}")
    _log.info(f"REDIS_URL: {_mask(REDIS_URL)}")

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


# API 版本化说明：
# - 所有 /api/ 端点已可用，同时作为 /api/v1/ 的兼容别名
# - 生产环境建议逐步迁移到 /api/v1/ 前缀，/api/ 保留兼容过渡期
# - /api/v1/health 健康检查端点可用于云部署探活

app = FastAPI(
    title="Cambodia Solar PAYGO Platform",
    version="1.0.0",
    lifespan=lifespan,
)

from app.middleware import RateLimiterMiddleware, RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimiterMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/screenshots", StaticFiles(directory="docs/screenshots"), name="screenshots")
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
app.include_router(controller_router)


@app.get("/api/seed")
async def api_seed_demo_data():
    """一键加载演示数据（无需 Shell）"""
    import subprocess, sys, os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, os.path.join(base, "scripts", "seed_demo_data.py")],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": base}
    )
    # 清除仪表盘缓存，确保加载种子数据后仪表盘立即刷新
    if result.returncode == 0:
        try:
            from app.redis import cache_delete
            await cache_delete("dashboard:enhanced:*")
        except Exception:
            pass
    return {"output": result.stdout, "error": result.stderr, "returncode": result.returncode}


@app.get("/api/v1/health")
async def api_v1_health():
    """API v1 健康检查（云部署探活端点）"""
    return {"status": "ok", "version": "1.0.0"}


# ---- 平台说明书 ----

import re as _re

def _md_to_html(text: str) -> str:
    """简易 Markdown → HTML，支持标题/代码块/表格/图片/链接/列表/粗体。"""
    # 代码块 (```...```)
    text = _re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', text, flags=_re.DOTALL)
    # 内联代码
    text = _re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # 图片（修正相对路径 → 绝对路径）
    def _fix_img_path(m):
        alt, src = m.group(1), m.group(2)
        # ../screenshots/... → /screenshots/...
        src = src.replace('../screenshots/', '/screenshots/')
        # docs/screenshots/... → /screenshots/...
        src = _re.sub(r'^docs/screenshots/', '/screenshots/', src)
        # bare filename without path → /screenshots/
        if not src.startswith(('http', '/', 'data:')):
            src = '/screenshots/' + src.split('/')[-1]
        return f'<img src="{src}" alt="{alt}">'
    text = _re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _fix_img_path, text)
    # 链接
    text = _re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # 粗体
    text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 标题
    text = _re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=_re.MULTILINE)
    text = _re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=_re.MULTILINE)
    text = _re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=_re.MULTILINE)
    text = _re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=_re.MULTILINE)
    # 表格（简化：|...| 行包裹为 table）
    lines = text.split('\n')
    result = []
    in_table = False
    for i, line in enumerate(lines):
        if line.startswith('|') and line.endswith('|'):
            if not in_table:
                result.append('<table>')
                in_table = True
            is_header = '---' in line
            cells = [c.strip() for c in line.split('|')[1:-1]]
            tag = 'th' if (is_header or (i > 0 and '---' in lines[i-1] if i > 0 else False)) else 'td'
            # Skip separator rows
            if all(_re.match(r'^:?-{3,}:?$', c) for c in cells):
                continue
            result.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
        else:
            if in_table:
                result.append('</table>')
                in_table = False
            # 列表
            if _re.match(r'^[-*] ', line):
                result.append('<li>' + line[2:] + '</li>')
            elif _re.match(r'^\d+\. ', line):
                result.append('<li>' + _re.sub(r'^\d+\. ', '', line) + '</li>')
            elif line.startswith('> '):
                result.append('<blockquote>' + line[2:] + '</blockquote>')
            elif line.startswith('---'):
                result.append('<hr>')
            elif line.strip() == '':
                result.append('<br>')
            else:
                result.append(line)
    if in_table:
        result.append('</table>')
    return '\n'.join(result)


@app.get("/help")
async def help_page(request: Request):
    """平台说明书 — README + 演示流程手册"""
    import os as _os
    base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

    readme_path = _os.path.join(base, "README.md")
    demo_path = _os.path.join(base, "docs", "项目文档", "平台演示流程手册.md")

    readme_html = ""
    demo_html = ""
    try:
        with open(readme_path) as f:
            readme_html = _md_to_html(f.read())
    except Exception:
        readme_html = "<p>README.md 加载失败</p>"
    try:
        with open(demo_path) as f:
            demo_html = _md_to_html(f.read())
    except Exception:
        demo_html = "<p>演示流程手册加载失败</p>"

    return templates.TemplateResponse(request, "help.html", {
        "readme_content": readme_html,
        "demo_content": demo_html,
    })


@app.get("/dashboard")
async def dashboard(request: Request):
    from app.redis import session_get
    from app.security import decode_token

    # JWT Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        payload = decode_token(auth_header[7:])
        if payload and payload.get("type") == "access":
            return templates.TemplateResponse(request, "dashboard.html")

    # JWT cookie
    jwt_cookie = request.cookies.get("access_token")
    if jwt_cookie:
        payload = decode_token(jwt_cookie)
        if payload and payload.get("type") == "access":
            return templates.TemplateResponse(request, "dashboard.html")

    # Session cookie (legacy)
    sid = request.cookies.get("session")
    if not sid or await session_get(sid) is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/controller")
async def controller_page(request: Request):
    """Web 版 PAYGO 控制器模拟器（安卓手机浏览器可访问）"""
    return templates.TemplateResponse(request, "controller.html")
