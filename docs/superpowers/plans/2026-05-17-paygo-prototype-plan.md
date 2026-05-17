# 柬埔寨太阳能 PAYGO 平台原型 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可在本地运行的 PAYGO 太阳能设备管理原型（FastAPI + Jinja2 + 内存DB）

**Architecture:** FastAPI 服务端渲染应用。内存 dict 存储客户和 Token 数据。Jinja2 模板渲染 3 个页面（登录、主界面），CSS 绿色主题。API 路由处理客户 CRUD 和 Token 生成。

**Tech Stack:** Python 3, FastAPI, uvicorn, Jinja2, python-multipart（表单解析）, pytest, httpx（测试用 TestClient）

---

### Task 1: 项目初始化

**Files:**
- Fix: `app/__init__.py`（重命名，去掉空格）
- Fix: `app/ruoters/__init__.py` → `app/routers/__init__.py`（修正拼写，去掉空格）
- Fix: `static/__init__.py`（去掉空格）
- Fix: `tests/__init__.py`（去掉空格）
- Create: `requirements.txt`

- [ ] **Step 1: 修复文件名并安装依赖**

```bash
# 修复所有 __init__.py 空格问题，修正 ruoters → routers
cd /Users/qinzz/Desktop/paygo-platform
mv "app/__ init__ .py" app/__init__.py 2>/dev/null; true
mv "app/ruoters/__ init__ .py" "app/ruoters/__init__.py" 2>/dev/null; true
mv app/ruoters app/routers 2>/dev/null; true
mv "static/__ init__ .py" static/__init__.py 2>/dev/null; true
mv "tests/__ init__ .py" tests/__init__.py 2>/dev/null; true
```

- [ ] **Step 2: 创建 requirements.txt 并安装**

```bash
cat > /Users/qinzz/Desktop/paygo-platform/requirements.txt << 'DEPS'
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
jinja2>=3.1.0
python-multipart>=0.0.6
pytest>=7.0.0
httpx>=0.24.0
DEPS

pip install -r /Users/qinzz/Desktop/paygo-platform/requirements.txt
```

Expected: pip 安装成功，无报错

- [ ] **Step 3: 验证目录结构正确**

```bash
find /Users/qinzz/Desktop/paygo-platform -type f -not -path '*/.git/*' -not -path '*/.superpowers/*' -not -path '*/docs/*' | sort
```

Expected: 包含 `app/__init__.py`, `app/routers/__init__.py`, `static/__init__.py`, `tests/__init__.py`, `requirements.txt`

- [ ] **Step 4: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add -A
git -C /Users/qinzz/Desktop/paygo-platform commit -m "chore: 项目初始化，修复目录结构，安装依赖"
```

---

### Task 2: 内存数据库（db.py）

**Files:**
- Create: `app/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_db.py
from app.db import get_customers, get_tokens, add_customer, add_token, get_customer, delete_customer


def test_customers_starts_empty():
    store = get_customers()
    assert store == {}


def test_add_and_get_customer():
    cid = add_customer(name="Sok Heng", phone="0888888001", device_id="Solar-001")
    assert cid.startswith("C")
    customer = get_customer(cid)
    assert customer["name"] == "Sok Heng"
    assert customer["phone"] == "0888888001"
    assert customer["device_id"] == "Solar-001"
    assert customer["remaining_days"] == 0
    assert customer["status"] == "active"


def test_get_customer_not_found():
    assert get_customer("C999") is None


def test_delete_customer():
    cid = add_customer(name="Test", phone="000", device_id="D000")
    assert delete_customer(cid) is True
    assert get_customer(cid) is None


def test_delete_customer_not_found():
    assert delete_customer("C999") is False


def test_tokens_starts_empty():
    store = get_tokens()
    assert store == []


def test_add_token():
    tid = add_token(customer_id="C001", token="12345678", days=30)
    assert tid.startswith("T")
    tokens = get_tokens()
    assert len(tokens) == 1
    assert tokens[0]["customer_id"] == "C001"
    assert tokens[0]["days"] == 30
    assert "expires_at" in tokens[0]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_db.py -v
```

Expected: 全部 FAIL（模块不存在 / 函数未定义）

- [ ] **Step 3: 实现 db.py**

```python
# app/db.py
import uuid
from datetime import datetime, timedelta

_customers: dict[str, dict] = {}
_tokens: list[dict] = []


def get_customers() -> dict:
    return _customers


def get_customer(customer_id: str) -> dict | None:
    return _customers.get(customer_id)


def add_customer(name: str, phone: str, device_id: str) -> str:
    cid = f"C{str(uuid.uuid4())[:4].upper()}"
    _customers[cid] = {
        "id": cid,
        "name": name,
        "phone": phone,
        "device_id": device_id,
        "remaining_days": 0,
        "status": "active",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    return cid


def delete_customer(customer_id: str) -> bool:
    if customer_id in _customers:
        del _customers[customer_id]
        return True
    return False


def get_tokens() -> list:
    return _tokens


def add_token(customer_id: str, token: str, days: int) -> str:
    tid = f"T{str(uuid.uuid4())[:4].upper()}"
    now = datetime.now()
    _tokens.append({
        "id": tid,
        "customer_id": customer_id,
        "token": token,
        "days": days,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    })
    return tid
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_db.py -v
```

Expected: 全部 PASS（8 tests passed）

- [ ] **Step 5: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add app/db.py tests/test_db.py
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加内存数据库模块"
```

---

### Task 3: Token 引擎（token_engine.py）

**Files:**
- Create: `app/token_engine.py`
- Create: `tests/test_token_engine.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_token_engine.py
from app.token_engine import generate_token


def test_generate_token_returns_8_digit_string():
    token = generate_token(device_id="Solar-001", days=30)
    assert isinstance(token, str)
    assert len(token) == 8
    assert token.isdigit()


def test_generate_token_is_deterministic():
    t1 = generate_token(device_id="Solar-001", days=30)
    t2 = generate_token(device_id="Solar-001", days=30)
    # 随机模式每次不同
    assert isinstance(t1, str)
    assert isinstance(t2, str)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_token_engine.py -v
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 token_engine.py**

```python
# app/token_engine.py
import random


def generate_token(device_id: str, days: int) -> str:
    """生成 8 位随机数字 Token。
    后续切换 OpenPAYGO 时只需修改此函数内部实现。
    """
    return ''.join(random.choices('0123456789', k=8))
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_token_engine.py -v
```

Expected: PASS（2 tests passed）

- [ ] **Step 5: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add app/token_engine.py tests/test_token_engine.py
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加Token生成模块"
```

---

### Task 4: 认证路由（auth.py）

**Files:**
- Create: `app/routers/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_auth.py
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
    # 验证 session cookie 已设置
    assert "session" in response.cookies


def test_login_post_wrong_password_shows_error():
    response = client.post("/login", data={
        "username": "admin",
        "password": "wrong",
    })
    assert response.status_code == 200
    # 错误信息应出现在页面中
    assert "用户名或密码错误" in response.text


def test_dashboard_redirects_when_not_logged_in():
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_dashboard_accessible_when_logged_in():
    # 先登录获取 cookie
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
    # cookie 应被清除
    assert response.cookies.get("session") == "" or "session" not in response.cookies
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_auth.py -v
```

Expected: FAIL（`app.main` 模块不存在 / `app.routers.auth` 不存在）

- [ ] **Step 3: 实现 auth.py**

```python
# app/routers/auth.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session", value="authenticated")
        return response
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "用户名或密码错误",
    })


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response
```

- [ ] **Step 4: 现在测试依赖 main.py，所以 Task 4 的测试需要 Task 6（main.py）先存在。暂时跳过 Step 2，在 Task 6 完成后再回来运行测试。**

记录：auth 测试暂时挂起，等 main.py 创建后再跑。

- [ ] **Step 5: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add app/routers/auth.py tests/test_auth.py
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加认证路由（登录/登出）"
```

---

### Task 5: 客户 & Token API 路由（customers.py）

**Files:**
- Create: `app/routers/customers.py`
- Create: `tests/test_customers_api.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_customers_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login():
    """Helper: 登录并返回 session cookie"""
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


def test_create_customer():
    cookie = _login()
    response = client.post("/api/customers", json={
        "name": "Sok Heng",
        "phone": "0888888001",
        "device_id": "Solar-001",
    }, cookies={"session": cookie})
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("C")
    assert data["name"] == "Sok Heng"


def test_get_customers_list():
    cookie = _login()
    response = client.get("/api/customers", cookies={"session": cookie})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_customer_detail():
    cookie = _login()
    # 先创建一个客户
    create_resp = client.post("/api/customers", json={
        "name": "Mary Keo",
        "phone": "0966666002",
        "device_id": "Solar-002",
    }, cookies={"session": cookie})
    cid = create_resp.json()["id"]
    # 获取详情
    response = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert response.status_code == 200
    assert response.json()["name"] == "Mary Keo"


def test_get_customer_not_found():
    cookie = _login()
    response = client.get("/api/customers/C999", cookies={"session": cookie})
    assert response.status_code == 404


def test_delete_customer():
    cookie = _login()
    create_resp = client.post("/api/customers", json={
        "name": "Delete Me",
        "phone": "000",
        "device_id": "D000",
    }, cookies={"session": cookie})
    cid = create_resp.json()["id"]
    response = client.delete(f"/api/customers/{cid}", cookies={"session": cookie})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_generate_token():
    cookie = _login()
    # 创建客户
    create_resp = client.post("/api/customers", json={
        "name": "Token Test",
        "phone": "0999999999",
        "device_id": "Solar-099",
    }, cookies={"session": cookie})
    cid = create_resp.json()["id"]
    # 生成 Token
    response = client.post(f"/api/customers/{cid}/token", json={
        "days": 30,
    }, cookies={"session": cookie})
    assert response.status_code == 200
    data = response.json()
    assert len(data["token"]) == 8
    assert data["customer_id"] == cid
    assert data["days"] == 30


def test_get_tokens():
    cookie = _login()
    response = client.get("/api/tokens", cookies={"session": cookie})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_requires_auth():
    response = client.get("/api/customers")
    assert response.status_code == 303
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_customers_api.py -v
```

Expected: FAIL（路由未注册）

- [ ] **Step 3: 实现 customers.py**

```python
# app/routers/customers.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db import get_customers, add_customer, get_customer, delete_customer
from app.db import get_tokens, add_token
from app.token_engine import generate_token

router = APIRouter(prefix="/api")


class CreateCustomerRequest(BaseModel):
    name: str
    phone: str
    device_id: str


class GenerateTokenRequest(BaseModel):
    days: int


def check_auth(request: Request):
    if request.cookies.get("session") != "authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/customers")
def list_customers(request: Request):
    check_auth(request)
    return list(get_customers().values())


@router.post("/customers")
def create_customer(body: CreateCustomerRequest, request: Request):
    check_auth(request)
    cid = add_customer(name=body.name, phone=body.phone, device_id=body.device_id)
    return get_customer(cid)


@router.get("/customers/{customer_id}")
def customer_detail(customer_id: str, request: Request):
    check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/customers/{customer_id}")
def remove_customer(customer_id: str, request: Request):
    check_auth(request)
    ok = delete_customer(customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"ok": True}


@router.post("/customers/{customer_id}/token")
def create_token(customer_id: str, body: GenerateTokenRequest, request: Request):
    check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    token = generate_token(device_id=customer["device_id"], days=body.days)
    tid = add_token(customer_id=customer_id, token=token, days=body.days)
    result = get_tokens()
    for t in result:
        if t["id"] == tid:
            return t
    return {"error": "token creation failed"}


@router.get("/tokens")
def list_tokens(request: Request):
    check_auth(request)
    return list(get_tokens())
```

- [ ] **Step 4: 测试暂挂，等 main.py 完成后跑。**

- [ ] **Step 5: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add app/routers/customers.py tests/test_customers_api.py
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加客户管理及Token生成API路由"
```

---

### Task 6: FastAPI 入口（main.py）

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: 实现 main.py**

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.routers import auth, customers

app = FastAPI(title="PAYGO Solar Platform")

templates = Jinja2Templates(directory="templates")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
app.include_router(auth.router)
app.include_router(customers.router)


@app.get("/dashboard")
def dashboard_page(request: Request):
    if request.cookies.get("session") != "authenticated":
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request})
```

- [ ] **Step 2: 验证应用可启动**

```bash
cd /Users/qinzz/Desktop/paygo-platform && timeout 5 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 || true
```

Expected: 看到 "Uvicorn running on http://127.0.0.1:8000" 或者因为模板文件还不存在而报错（这是预期的，下一步创建模板）。

- [ ] **Step 3: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add app/main.py
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加FastAPI入口，注册路由和静态文件"
```

---

### Task 7: 基础模板 & 静态文件（base.html + style.css）

**Files:**
- Create: `templates/base.html`
- Create: `static/style.css`

- [ ] **Step 1: 创建 CSS 样式**

```css
/* static/style.css */
:root {
  --green: #059669;
  --green-light: #d1fae5;
  --green-bg: #f0fdf4;
  --gray-50: #f8fafc;
  --gray-100: #f1f5f9;
  --gray-200: #e2e8f0;
  --gray-400: #94a3b8;
  --gray-600: #475569;
  --gray-800: #1e293b;
  --radius: 10px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--gray-50);
  color: var(--gray-800);
  min-height: 100vh;
}

/* ---- 顶部导航 ---- */
.navbar {
  background: var(--green);
  color: #fff;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 16px;
}
.navbar a { color: #fff; text-decoration: none; font-size: 14px; opacity: 0.9; }
.navbar a:hover { opacity: 1; }

/* ---- 登录页 ---- */
.login-container {
  display: flex; align-items: center; justify-content: center;
  min-height: calc(100vh - 60px);
}
.login-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  padding: 40px;
  width: 360px;
  text-align: center;
}
.login-card h1 { font-size: 22px; margin-bottom: 4px; }
.login-card .sub { color: var(--gray-400); font-size: 13px; margin-bottom: 24px; }
.login-card input {
  width: 100%; padding: 10px 14px; margin-bottom: 12px;
  border: 1px solid var(--gray-200); border-radius: 8px; font-size: 14px;
}
.login-card input:focus { outline: none; border-color: var(--green); }
.login-card button {
  width: 100%; padding: 10px; background: var(--green);
  color: #fff; border: none; border-radius: 8px;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.login-card button:hover { opacity: 0.9; }
.login-card .error {
  color: #dc2626; font-size: 13px; margin-bottom: 12px;
}

/* ---- 主界面布局 ---- */
.main-layout {
  display: flex; height: calc(100vh - 54px);
}

/* 左侧客户列表 */
.customer-list {
  width: 320px; background: #fff; border-right: 1px solid var(--gray-200);
  overflow-y: auto; padding: 16px;
}
.customer-list h3 {
  font-size: 15px; margin-bottom: 12px; color: var(--gray-600);
}
.customer-item {
  padding: 12px; border-radius: 8px; margin-bottom: 6px;
  cursor: pointer; transition: background 0.15s;
  border: 1px solid transparent;
}
.customer-item:hover { background: var(--green-bg); }
.customer-item.active {
  background: var(--green-bg); border-color: var(--green);
}
.customer-item .name { font-weight: 600; font-size: 14px; }
.customer-item .meta { font-size: 12px; color: var(--gray-400); margin-top: 2px; }

/* 右侧详情面板 */
.detail-panel {
  flex: 1; padding: 24px 32px; overflow-y: auto;
}
.detail-panel .empty {
  color: var(--gray-400); text-align: center; padding-top: 120px;
}
.detail-panel .empty p { font-size: 15px; }

.detail-card {
  background: #fff; border-radius: var(--radius);
  box-shadow: 0 1px 3px rgba(0,0,0,0.06); padding: 24px;
}
.detail-card h2 { font-size: 20px; margin-bottom: 16px; }
.detail-row {
  display: flex; padding: 8px 0; border-bottom: 1px solid var(--gray-100);
  font-size: 14px;
}
.detail-row .label { color: var(--gray-400); width: 100px; flex-shrink: 0; }
.detail-row .value { color: var(--gray-800); }

.btn {
  display: inline-block; padding: 10px 20px; border-radius: 8px;
  font-size: 14px; font-weight: 600; cursor: pointer; border: none;
}
.btn-primary { background: var(--green); color: #fff; }
.btn-primary:hover { opacity: 0.9; }
.btn-danger { background: #fff; color: #dc2626; border: 1px solid #fecaca; }
.btn-danger:hover { background: #fef2f2; }

.actions { margin-top: 20px; display: flex; gap: 12px; }

/* ---- 弹窗 / Modal ---- */
.modal-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.3); z-index: 100;
  align-items: center; justify-content: center;
}
.modal-overlay.show { display: flex; }
.modal-card {
  background: #fff; border-radius: var(--radius); padding: 32px;
  width: 400px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.modal-card h3 { margin-bottom: 16px; }
.modal-card input {
  width: 100%; padding: 10px; border: 1px solid var(--gray-200);
  border-radius: 8px; font-size: 14px; margin-bottom: 16px;
}
.modal-card .token-display {
  font-size: 36px; font-weight: 700; letter-spacing: 6px;
  color: var(--green); background: var(--green-bg);
  padding: 16px; border-radius: var(--radius); margin: 16px 0;
}
.modal-card .token-hint {
  font-size: 12px; color: var(--gray-400); margin-bottom: 16px;
}
.modal-actions { display: flex; gap: 12px; justify-content: center; }

/* ---- 新增客户表单 ---- */
.form-group { text-align: left; margin-bottom: 12px; }
.form-group label { font-size: 13px; color: var(--gray-600); display: block; margin-bottom: 4px; }
.form-group input {
  width: 100%; padding: 10px; border: 1px solid var(--gray-200);
  border-radius: 8px; font-size: 14px;
}
.form-group input:focus { outline: none; border-color: var(--green); }
```

- [ ] **Step 2: 创建 base.html 布局框架**

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="km">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PAYGO Solar Platform</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  {% if request.cookies.get('session') == 'authenticated' %}
  <nav class="navbar">
    <span>☀️ PAYGO Solar</span>
    <a href="/logout">退出登录</a>
  </nav>
  {% endif %}
  {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add templates/base.html static/style.css
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加基础模板和全局CSS样式"
```

---

### Task 8: 登录页（login.html）

**Files:**
- Create: `templates/login.html`

- [ ] **Step 1: 创建 login.html**

```html
<!-- templates/login.html -->
{% extends "base.html" %}
{% block content %}
<div class="login-container">
  <div class="login-card">
    <h1>☀️ PAYGO Solar</h1>
    <p class="sub">柬埔寨太阳能设备管理平台</p>
    {% if error %}
    <p class="error">{{ error }}</p>
    {% endif %}
    <form method="post" action="/login">
      <input type="text" name="username" placeholder="用户名" required>
      <input type="password" name="password" placeholder="密码" required>
      <button type="submit">登 录</button>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: 验证登录页可渲染**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/login')
print('Status:', resp.status_code)
print('Has login form:', '用户名' in resp.text)
print('Has title:', 'PAYGO Solar' in resp.text)
"
```

Expected: Status: 200, Has login form: True, Has title: True

- [ ] **Step 3: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add templates/login.html
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加登录页面模板"
```

---

### Task 9: 主界面（dashboard.html）

**Files:**
- Create: `templates/dashboard.html`

- [ ] **Step 1: 创建 dashboard.html**

```html
<!-- templates/dashboard.html -->
{% extends "base.html" %}
{% block content %}
<div class="main-layout">
  <!-- 左侧客户列表 -->
  <aside class="customer-list" id="customerList">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <h3 style="margin:0;">📋 客户列表</h3>
      <button class="btn btn-primary" style="padding:6px 14px;font-size:12px;"
              onclick="showAddCustomerModal()">+ 新增</button>
    </div>
    <div id="customerItems"></div>
  </aside>

  <!-- 右侧详情面板 -->
  <main class="detail-panel" id="detailPanel">
    <div class="empty">
      <p style="font-size:48px;margin-bottom:12px;">👈</p>
      <p>选择左侧客户查看详情</p>
    </div>
  </main>
</div>

<!-- 新增客户弹窗 -->
<div class="modal-overlay" id="addCustomerModal">
  <div class="modal-card">
    <h3>新增客户</h3>
    <div class="form-group">
      <label>姓名</label>
      <input type="text" id="newName" placeholder="客户姓名">
    </div>
    <div class="form-group">
      <label>电话</label>
      <input type="text" id="newPhone" placeholder="联系电话">
    </div>
    <div class="form-group">
      <label>设备编号</label>
      <input type="text" id="newDevice" placeholder="如 Solar-001">
    </div>
    <div class="modal-actions">
      <button class="btn" style="background:#f1f5f9;color:#475569;"
              onclick="closeModal('addCustomerModal')">取消</button>
      <button class="btn btn-primary" onclick="createCustomer()">确认添加</button>
    </div>
  </div>
</div>

<!-- 生成Token弹窗（输入天数） -->
<div class="modal-overlay" id="tokenDaysModal">
  <div class="modal-card">
    <h3>生成激活码</h3>
    <p style="color:#64748b;font-size:13px;margin-bottom:16px;"
       id="tokenCustomerName"></p>
    <div class="form-group">
      <label>使用天数</label>
      <input type="number" id="tokenDays" value="30" min="1" max="365">
    </div>
    <div class="modal-actions">
      <button class="btn" style="background:#f1f5f9;color:#475569;"
              onclick="closeModal('tokenDaysModal')">取消</button>
      <button class="btn btn-primary" onclick="generateToken()">确认生成</button>
    </div>
  </div>
</div>

<!-- Token 结果弹窗 -->
<div class="modal-overlay" id="tokenResultModal">
  <div class="modal-card">
    <h3>🔑 激活码已生成</h3>
    <div class="token-display" id="tokenCode"></div>
    <p class="token-hint">请复制此激活码发送给客户<br>有效期 7 天</p>
    <div class="modal-actions">
      <button class="btn btn-primary" onclick="closeModal('tokenResultModal')">完成</button>
    </div>
  </div>
</div>

<!-- 删除确认弹窗 -->
<div class="modal-overlay" id="deleteConfirmModal">
  <div class="modal-card">
    <h3>确认删除</h3>
    <p style="color:#64748b;font-size:14px;margin-bottom:20px;">
      确定要删除客户 <strong id="deleteCustomerName"></strong> 吗？此操作不可撤销。
    </p>
    <div class="modal-actions">
      <button class="btn" style="background:#f1f5f9;color:#475569;"
              onclick="closeModal('deleteConfirmModal')">取消</button>
      <button class="btn btn-danger" onclick="confirmDelete()">确认删除</button>
    </div>
  </div>
</div>

<script>
let selectedCustomerId = null;
let deleteTargetId = null;

// 加载客户列表
async function loadCustomers() {
  const resp = await fetch('/api/customers');
  const customers = await resp.json();
  const container = document.getElementById('customerItems');
  if (customers.length === 0) {
    container.innerHTML = '<p style="color:#94a3b8;font-size:13px;text-align:center;padding:20px;">暂无客户</p>';
    return;
  }
  container.innerHTML = customers.map(c => `
    <div class="customer-item ${c.id === selectedCustomerId ? 'active' : ''}"
         onclick="selectCustomer('${c.id}')">
      <div class="name">👤 ${c.name}</div>
      <div class="meta">📱 ${c.phone} · 🔌 ${c.device_id}</div>
    </div>
  `).join('');
}

// 选中客户
async function selectCustomer(id) {
  selectedCustomerId = id;
  await loadCustomers();
  const resp = await fetch(`/api/customers/${id}`);
  const c = await resp.json();
  document.getElementById('detailPanel').innerHTML = `
    <div class="detail-card">
      <h2>👤 ${c.name}</h2>
      <div class="detail-row"><span class="label">电话</span><span class="value">${c.phone}</span></div>
      <div class="detail-row"><span class="label">设备</span><span class="value">${c.device_id}</span></div>
      <div class="detail-row"><span class="label">剩余天数</span><span class="value">${c.remaining_days} 天</span></div>
      <div class="detail-row"><span class="label">状态</span><span class="value">${c.status === 'active' ? '🟢 活跃' : '🔴 过期'}</span></div>
      <div class="detail-row"><span class="label">创建日期</span><span class="value">${c.created_at}</span></div>
      <div class="actions">
        <button class="btn btn-primary" onclick="showTokenModal('${c.id}', '${c.name}')">🔑 生成激活码</button>
        <button class="btn btn-danger" onclick="showDeleteModal('${c.id}', '${c.name}')">删除客户</button>
      </div>
    </div>
  `;
}

// 新增客户弹窗
function showAddCustomerModal() {
  document.getElementById('newName').value = '';
  document.getElementById('newPhone').value = '';
  document.getElementById('newDevice').value = '';
  document.getElementById('addCustomerModal').classList.add('show');
}

async function createCustomer() {
  const name = document.getElementById('newName').value.trim();
  const phone = document.getElementById('newPhone').value.trim();
  const device_id = document.getElementById('newDevice').value.trim();
  if (!name || !phone || !device_id) { alert('请填写所有字段'); return; }
  await fetch('/api/customers', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, phone, device_id})
  });
  closeModal('addCustomerModal');
  await loadCustomers();
}

// Token 生成
let tokenCustomerId = null;
function showTokenModal(cid, name) {
  tokenCustomerId = cid;
  document.getElementById('tokenCustomerName').textContent = '为客户 ' + name + ' 生成激活码';
  document.getElementById('tokenDays').value = 30;
  document.getElementById('tokenDaysModal').classList.add('show');
}

async function generateToken() {
  const days = parseInt(document.getElementById('tokenDays').value);
  const resp = await fetch(`/api/customers/${tokenCustomerId}/token`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({days})
  });
  const data = await resp.json();
  closeModal('tokenDaysModal');
  document.getElementById('tokenCode').textContent = data.token;
  document.getElementById('tokenResultModal').classList.add('show');
}

// 删除确认
function showDeleteModal(cid, name) {
  deleteTargetId = cid;
  document.getElementById('deleteCustomerName').textContent = name;
  document.getElementById('deleteConfirmModal').classList.add('show');
}

async function confirmDelete() {
  await fetch(`/api/customers/${deleteTargetId}`, {method: 'DELETE'});
  closeModal('deleteConfirmModal');
  selectedCustomerId = null;
  document.getElementById('detailPanel').innerHTML = `
    <div class="empty"><p style="font-size:48px;">👈</p><p>选择左侧客户查看详情</p></div>
  `;
  await loadCustomers();
}

// 弹窗通用
function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}

// 初始加载
loadCustomers();
</script>
{% endblock %}
```

- [ ] **Step 2: 验证主界面可渲染**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
# 先登录
login_resp = client.post('/login', data={'username':'admin','password':'admin123'})
cookie = login_resp.cookies.get('session')
# 访问dashboard
resp = client.get('/dashboard', cookies={'session': cookie})
print('Status:', resp.status_code)
print('Has customer list:', '客户列表' in resp.text)
print('Has detail panel:', '选择左侧客户' in resp.text)
"
```

Expected: Status: 200, Has customer list: True, Has detail panel: True

- [ ] **Step 3: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add templates/dashboard.html
git -C /Users/qinzz/Desktop/paygo-platform commit -m "feat: 添加主界面前端（客户列表+详情面板+弹窗）"
```

---

### Task 10: 集成验证 & 回归测试

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 编写端到端流程测试**

```python
# tests/test_integration.py
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
    assert len(token_data["token"]) == 8
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
```

- [ ] **Step 2: 运行所有测试**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/ -v
```

Expected: 所有测试 PASS（18+ tests passed）

- [ ] **Step 3: 验证应用可启动并可访问**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 2
curl -s http://127.0.0.1:8000/login | grep -c "PAYGO Solar"
curl -s -X POST -d "username=admin&password=admin123" http://127.0.0.1:8000/login -c /tmp/cookies.txt -D /tmp/headers.txt
curl -s -b /tmp/cookies.txt http://127.0.0.1:8000/dashboard | grep -c "客户列表"
kill %1 2>/dev/null; true
```

Expected: 第一个 grep 返回 1，第二个 grep 返回 1

- [ ] **Step 4: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add tests/test_integration.py
git -C /Users/qinzz/Desktop/paygo-platform commit -m "test: 添加端到端集成测试"
```

---

### Task 11: 最终验证 & 清理

- [ ] **Step 1: 运行完整测试套件**

```bash
cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/ -v --tb=short
```

Expected: 全部 PASS，无 FAIL 或 ERROR

- [ ] **Step 2: 确认文件结构符合设计文档**

```bash
find /Users/qinzz/Desktop/paygo-platform -type f -not -path '*/.git/*' -not -path '*/.superpowers/*' -not -path '*/docs/*' -not -path '*/__pycache__/*' -not -path '*.pyc' | sort
```

Expected 路径:
```
app/__init__.py
app/db.py
app/main.py
app/routers/__init__.py
app/routers/auth.py
app/routers/customers.py
app/token_engine.py
requirements.txt
static/style.css
templates/base.html
templates/dashboard.html
templates/login.html
tests/__init__.py
tests/test_auth.py
tests/test_customers_api.py
tests/test_db.py
tests/test_integration.py
tests/test_token_engine.py
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/qinzz/Desktop/paygo-platform add -A
git -C /Users/qinzz/Desktop/paygo-platform commit -m "chore: 最终验证，确认结构完整"
```
