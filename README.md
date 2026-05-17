# PAYGO 太阳能平台 — 操作手册

## 1. 环境要求

- Python 3.10+
- pip

## 2. 本地启动

```bash
# 进入项目目录
cd paygo-platform

# 创建虚拟环境（首次）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：
- **运营后台**: http://localhost:8000/dashboard
- **API 文档 (Swagger)**: http://localhost:8000/docs
- **登录账号**: `admin` / `admin123`

## 3. 远程部署

### 方案一：Render（免费）

1. 将项目推送到 GitHub
2. 在 [Render](https://render.com) 创建新 Web Service，连接仓库
3. 配置：
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 部署完成后通过 Render 提供的域名访问

### 方案二：VPS / 云服务器

```bash
# 在服务器上克隆项目
git clone <仓库地址>
cd paygo-platform

# 安装依赖
pip install -r requirements.txt

# 后台运行（使用 nohup 或 screen）
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 或使用 systemd 管理（推荐生产环境）
```

## 4. 运行测试

```bash
source venv/bin/activate

# 运行全部测试（26 个）
python -m pytest tests/ -v

# 按模块运行
python -m pytest tests/test_db.py -v           # 数据库 (7 tests)
python -m pytest tests/test_auth.py -v         # 认证 (6 tests)
python -m pytest tests/test_customers_api.py -v # 客户API (8 tests)
python -m pytest tests/test_token_engine.py -v  # Token引擎 (2 tests)
python -m pytest tests/test_integration.py -v   # 端到端集成 (3 tests)
```

## 5. 页面操作流程

### 5.1 登录

1. 打开 `http://localhost:8000/login`
2. 输入账号 `admin`，密码 `admin123`
3. 点击"登录"，进入主界面

### 5.2 新增客户

1. 在主界面左侧点击 **"+ 新增"** 按钮
2. 填写客户姓名、电话、设备编号
3. 点击"确认添加"

### 5.3 查看客户详情

- 在左侧客户列表点击任意客户，右侧显示详细信息（电话、设备、剩余天数、状态）

### 5.4 生成激活码 (Token)

1. 选中客户，在右侧详情面板点击 **"生成激活码"**
2. 输入使用天数（默认 30 天）
3. 确认后弹出 8 位数字 Token，复制发送给客户

### 5.5 删除客户

1. 选中客户，点击 **"删除客户"**
2. 在确认弹窗中确认删除

### 5.6 退出登录

- 点击右上角 **"退出登录"**

## 6. API 接口速查

所有 API 需要先登录获取 session cookie。

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/login` | 登录页面 |
| POST | `/login` | 提交登录 (form: username, password) |
| GET | `/logout` | 退出登录 |

### 客户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/customers` | 客户列表 |
| POST | `/api/customers` | 新增客户 (JSON: name, phone, device_id) |
| GET | `/api/customers/{id}` | 客户详情 |
| DELETE | `/api/customers/{id}` | 删除客户 |

### Token

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/customers/{id}/token` | 生成 Token (JSON: days) |
| GET | `/api/tokens` | Token 历史记录 |

### curl 示例

```bash
# 登录并保存 cookie
curl -c cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login

# 新增客户
curl -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Sok Heng","phone":"0888888001","device_id":"Solar-001"}' \
  http://localhost:8000/api/customers

# 查看客户列表
curl -b cookies.txt http://localhost:8000/api/customers

# 为客户生成 30 天 Token
curl -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"days":30}' \
  http://localhost:8000/api/customers/{customer_id}/token

# 删除客户
curl -b cookies.txt -X DELETE \
  http://localhost:8000/api/customers/{customer_id}
```

## 7. 项目结构

```
paygo-platform/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── db.py                # 内存数据库
│   ├── token_engine.py      # Token 生成引擎
│   └── routers/
│       ├── auth.py          # 认证路由
│       └── customers.py     # 客户 & Token API
├── static/
│   └── style.css            # 全局样式
├── templates/
│   ├── base.html            # 基础布局
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面
└── tests/
    ├── test_db.py
    ├── test_auth.py
    ├── test_customers_api.py
    ├── test_token_engine.py
    └── test_integration.py
```
