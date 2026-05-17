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
4. 客户在手机 Termux 中输入 Token 激活设备（详见第 7 章）

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

## 7. 控制器模拟脚本（安卓 Termux）

控制器模拟脚本运行在安卓手机的 Termux 环境中，模拟真实 PAYGO 太阳能控制器的行为：接收激活 Token、本地解码校验、管理设备状态。

### 7.1 安装 Termux

1. 在安卓手机上安装 [Termux](https://f-droid.org/packages/com.termux/)（推荐 F-Droid 版本）
2. 打开 Termux，安装 Python：

```bash
pkg update && pkg upgrade
pkg install python
```

### 7.2 部署控制器

将 `controller/` 目录拷贝到手机：

**方式一：直接拷贝（USB / 文件管理器）**
1. 将项目的 `controller/` 目录复制到手机存储
2. 在 Termux 中访问：`cp -r /sdcard/controller ~/controller`

**方式二：通过网络传输**
```bash
# 在 Termux 中执行，替换为电脑的 IP
pkg install openssh
scp -r user@192.168.x.x:/path/to/controller ~/controller
```

### 7.3 运行控制器

```bash
cd ~/controller
python controller.py
```

运行后显示终端界面：

```
╔══════════════════════════════╗
║    PAYGO 太阳能控制器       ║
╠══════════════════════════════╣
║ 设备:   --                  ║
║ 状态:   ○ 未绑定            ║
║ 剩余天数: 0 天               ║
║ 继电器: [断开]              ║
╚══════════════════════════════╝
[N] 输入新Token  [Q] 退出
```

### 7.4 操作说明

| 操作 | 按键 | 说明 |
|------|------|------|
| 输入 Token | `N` | 输入 8 位数字 Token，激活或续费设备 |
| 退出 | `Q` | 保存状态并退出控制器 |

**首次激活流程：**

1. 在运营后台选中客户，点击"生成激活码"，输入天数（如 30 天）
2. 后台显示 8 位数字 Token，如 `07030303`
3. 在 Termux 中运行 `python controller.py`
4. 按 `N`，输入 Token：`07030303`
5. 显示 "激活成功！+30 天"，设备绑定到该 Token 编码的设备 ID

**续费叠加：**

- 设备在 ACTIVE 状态下，输入新的同设备 Token，天数自动累加
- 例如：剩余 10 天 + 新 Token 30 天 = 40 天

**设备锁定与重启：**

- 剩余天数归零后，设备自动变为 LOCKED 状态（继电器断开）
- LOCKED 状态下可以输入新 Token 重新激活

### 7.5 状态文件

控制器状态保存在 `~/.paygo/state.json`：

```json
{
  "device_id_hash": 703,
  "remaining_days": 27,
  "last_update": "2026-05-17",
  "status": "active"
}
```

- `device_id_hash` — 设备 ID 的数字哈希（可与运营后台的设备编号对应）
- `remaining_days` — 当前剩余天数
- `last_update` — 上次状态更新日期，重新运行时自动计算天数差
- `status` — `unbound`（未绑定）/ `active`（已激活）/ `locked`（已锁定）

**重置设备**：删除 `~/.paygo/state.json` 即可恢复到未绑定状态。

### 7.6 Token 编码格式

Token 为 8 位数字，内嵌设备 ID 和天数信息，控制器可离线解码验证：

```
{device_hash:4位}{days:3位}{checksum:1位}
```

- 前 4 位：设备 ID 哈希（设备 ID 各字符码求和 % 10000）
- 中间 3 位：天数（1-365）
- 末 1 位：校验位 `(device_hash + days) % 10`

控制器解码后自动校验 checksum，无效 Token 会被拒绝。

## 8. 项目结构

```
paygo-platform/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── db.py                # 内存数据库
│   ├── token_engine.py      # Token 生成引擎（结构化编码）
│   └── routers/
│       ├── auth.py          # 认证路由
│       └── customers.py     # 客户 & Token API
├── controller/
│   ├── controller.py        # 控制器主入口（终端 UI）
│   ├── token_codec.py       # Token 编解码（离线验证）
│   └── state_manager.py     # 状态机 + JSON 持久化
├── static/
│   └── style.css            # 全局样式
├── templates/
│   ├── base.html            # 基础布局
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面
├── tests/
│   ├── test_db.py
│   ├── test_auth.py
│   ├── test_customers_api.py
│   ├── test_token_engine.py
│   ├── test_token_codec.py
│   ├── test_state_manager.py
│   ├── test_controller_integration.py
│   └── test_integration.py
└── docs/
    └── superpowers/
        ├── specs/           # 设计文档
        └── plans/           # 实施计划
```
