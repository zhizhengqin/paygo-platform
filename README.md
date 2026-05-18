# PAYGO 太阳能平台 — 操作手册（OpenPAYGO 标准 v3.0）

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
git clone <仓库地址>
cd paygo-platform
pip install -r requirements.txt
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

## 4. 运行测试

```bash
source venv/bin/activate

# 运行全部测试（79 个）
pytest tests/ -v

# 按模块运行
pytest tests/test_db.py -v                     # 数据库 (16 tests)
pytest tests/test_auth.py -v                   # 认证 (6 tests)
pytest tests/test_customers_api.py -v          # 客户API (20 tests)
pytest tests/test_state_manager.py -v          # 状态机 (19 tests)
pytest tests/test_config_api.py -v             # 支付汇率 (2 tests)
pytest tests/test_controller_integration.py -v # 控制器集成 (4 tests)
pytest tests/test_integration.py -v            # 端到端集成 (3 tests)
pytest tests/test_upgrade.py -v                # 五场景演示 (9 tests)
```

## 5. 五个 MFI 演示场景

> **前置准备**：启动后台服务，确保 `http://localhost:8000/dashboard` 可访问。

### 5.1 准备设备密钥

设备出厂预设了 32 位 hex 密钥。演示用密钥：
```
a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```
将此密钥输入到控制器初始设置中（首次运行控制器时会提示）。

---

### 场景一：首次支付解锁

1. 打开运营后台 http://localhost:8000/dashboard
2. 新增客户：
   - 姓名 `Sok Heng`
   - 电话 `0888888001`
   - 设备编号 `SN-KH-001`
   - **设备密钥** `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`
3. 确认客户状态显示为 **🔴 已锁定**
4. 在「模拟支付」区域选择 **$5.00 — 30天**，点击「确认支付」
5. 弹出 9 位 Token 和短信预览卡片
6. 在控制器终端中输入该 9 位 Token
7. 验证显示：`✓ Token验证成功！增加30天。当前剩余30天`

### 场景二：再次续费

1. 再次为 SN-KH-001 模拟支付 **$10.00 — 60天**
2. 在控制器输入新 Token（注意：Token 与上次**不同**，因为 OpenPAYGO 每次生成唯一的 Token）
3. 验证显示：`当前剩余90天`（30 + 60）

### 场景三：错误Token

1. 在控制器输入 `123456789`（随机 9 位数字）
2. 验证显示：`✗ Token无效`

### 场景四：逾期锁定与防重放

1. 在控制器按 `[D]`，输入快进天数耗尽剩余天数，设备自动锁定
2. 再次输入之前用过的旧 Token
3. 验证显示：`✗ Token已使用过（防重放）`

### 场景五：贷款结清永久解锁

1. 后台点击「⭐ 永久解锁」，在确认弹窗中确认
2. 弹出永久解锁 Token 和短信卡片
3. 控制器输入该 9 位 Token
4. 验证显示：`✓✓✓ 贷款已结清！设备永久解锁！`

---

## 6. 页面操作流程

### 6.1 登录

1. 打开 `http://localhost:8000/login`
2. 输入账号 `admin`，密码 `admin123`
3. 点击"登录"，进入主界面

### 6.2 新增客户

1. 在左侧面板点击 **"+ 新增"**
2. 填写姓名、电话、设备编号（如 `SN-KH-001`）
3. 填写 **设备密钥**（32 位 hex，设备出厂预设值）
4. 点击"确认添加"

### 6.3 查看客户详情

- 点击客户列表中的客户，右侧显示详细信息及状态（🟢活跃 / 🔴已锁定 / ⭐永久解锁）

### 6.4 模拟支付

1. 选中客户，在详情面板「💰 模拟支付」区域选择金额
2. 点击「💳 模拟支付」
3. 弹窗显示 9 位 Token 和模拟短信卡片（Token 为纯数字，无空格分隔）

### 6.5 锁定设备

1. 选中客户，点击「🔒 锁定设备」
2. 确认后客户状态变为「🔴 已锁定」

### 6.6 永久解锁

1. 选中客户，点击「⭐ 永久解锁」
2. 确认后弹出 DISABLE_PAYG Token，状态变为「⭐ 永久解锁」

### 6.7 删除客户

1. 选中客户，点击「删除客户」并在弹窗中确认

### 6.8 退出登录

- 点击右上角「退出登录」

## 7. API 接口速查

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
| POST | `/api/customers` | 新增客户 (JSON: name, phone, device_id, **secret_key**) |
| GET | `/api/customers/{id}` | 客户详情 |
| DELETE | `/api/customers/{id}` | 删除客户 |

### 模拟支付 & 设备控制

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/customers/{id}/simulate-payment` | 模拟支付 (JSON: amount)，返回 Token + SMS |
| POST | `/api/customers/{id}/lock` | 锁定设备 |
| POST | `/api/customers/{id}/permanent-unlock` | 永久解锁，生成 DISABLE_PAYG Token |

### Token & 记录

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/customers/{id}/token` | 生成 Token (JSON: days) |
| GET | `/api/tokens` | Token 历史记录 |
| GET | `/api/sms?customer_id={id}` | 短信发送记录 |

### 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/payment-rates` | 支付汇率配置 |

### curl 示例

```bash
# 登录并保存 cookie
curl -c cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login

# 新增客户（注意：必须提供 secret_key，32 位 hex）
curl -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Sok Heng","phone":"0888888001","device_id":"SN-KH-001","secret_key":"a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"}' \
  http://localhost:8000/api/customers

# 模拟支付 $5
curl -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"amount":5}' \
  http://localhost:8000/api/customers/{customer_id}/simulate-payment

# 锁定设备
curl -b cookies.txt -X POST \
  http://localhost:8000/api/customers/{customer_id}/lock

# 永久解锁
curl -b cookies.txt -X POST \
  http://localhost:8000/api/customers/{customer_id}/permanent-unlock

# 查看支付汇率
curl -b cookies.txt http://localhost:8000/api/config/payment-rates
```

## 8. 控制器使用（macOS 本地终端）

### 8.1 首次运行：初始化设备密钥

```bash
cd controller
source ../venv/bin/activate
python controller.py
```

首次运行显示初始设置界面：

```
╔══════════════════════════════╗
║            初始设置          ║
╠══════════════════════════════╣
║ 请输入设备预设密钥 (32位hex) ║
╚══════════════════════════════╝
密钥: _
```

输入 32 位 hex 密钥后进入主界面：

```
╔══════════════════════════════╗
║    PAYGO 太阳能控制器       ║
╠══════════════════════════════╣
║ 设备密钥: a1b2c3d4…        ║
║ 状态:   未绑定              ║
║ 剩余天数: 0 天               ║
║ 继电器: [断开]              ║
║ Count:   0                  ║
╚══════════════════════════════╝
[N] 输入新Token  [D] 模拟天数流逝  [R] 重置  [Q] 退出
```

### 8.2 操作说明

| 操作 | 按键 | 说明 |
|------|------|------|
| 输入 Token | `N` | 输入 9 位数字 Token（OpenPAYGO 标准格式） |
| 模拟天数流逝 | `D` | 输入天数直接递减剩余天数（演示用） |
| 重置 | `R` | 清除密钥、绑定和天数，恢复未绑定状态 |
| 退出 | `Q` | 保存状态并退出 |

### 8.3 重置设备

```bash
rm -rf ~/.paygo
```

---

## 9. 使用 Android 模拟器测试控制器（macOS）

### 9.1 安装 Android Studio

1. 打开 https://developer.android.com/studio 下载 macOS 版本
2. 双击 `.dmg`，将 **Android Studio.app** 拖入 `Applications`
3. 首次打开选择 **Standard** 安装，等待 SDK 下载完成

### 9.2 创建安卓虚拟设备 (AVD)

1. Android Studio → **More Actions** → **Virtual Device Manager**
2. 点击 **Create device (+)**，选择 **Pixel 6/7**，Next
3. 选择系统镜像 **Tiramisu (API 33)** 或更高，Download → Next → Finish

### 9.3 启动模拟器

1. Device Manager 中点击设备旁的 **▶ 播放**
2. 等待启动到安卓桌面

### 9.4 确认 adb 可用

```bash
~/Library/Android/sdk/platform-tools/adb devices
# 应显示: emulator-5554   device
```

> 方便起见：`echo 'export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"' >> ~/.zshrc && source ~/.zshrc`

### 9.5 安装 Termux 到模拟器

```bash
# 下载 Termux APK（F-Droid）
curl -L -o ~/Downloads/termux.apk \
  https://f-droid.org/repo/com.termux_118.apk

# 安装到模拟器
~/Library/Android/sdk/platform-tools/adb install ~/Downloads/termux.apk
```

### 9.6 在 Termux 中安装 Python

在模拟器的 Termux 中：

```bash
pkg update && pkg upgrade
pkg install python
```

### 9.7 部署控制器脚本

Mac 终端：

```bash
cd ~/Desktop/paygo-platform
~/Library/Android/sdk/platform-tools/adb push controller/ /sdcard/controller/
```

模拟器 Termux 中：

```bash
termux-setup-storage
# 允许存储权限
cp -r /sdcard/controller ~/controller
```

### 9.8 安装 OpenPAYGO 依赖

在 Termux 中：

```bash
pip install openpaygo
```

### 9.9 运行控制器

```bash
cd ~/controller
python controller.py
```

首次运行会提示输入设备密钥。

### 9.10 重新部署（代码更新后）

```bash
# Mac 终端
cd ~/Desktop/paygo-platform
adb push controller/ /sdcard/controller/

# 模拟器 Termux
cp -r /sdcard/controller ~/controller
```

### 9.11 常见问题

| 问题 | 解决方法 |
|------|----------|
| **模拟器启动后黑屏** | Device Manager → ▼ → **Cold Boot Now** |
| **adb devices 无设备** | `adb kill-server && adb devices` |
| **termux-setup-storage 无反应** | 安卓设置 → 应用 → Termux → 权限 → 开启存储 |
| **模拟器卡顿** | Device Manager → 编辑 → Graphics → **Hardware - GLES 2.0** |
| **Apple Silicon 选不了镜像** | 选择带 **arm64-v8a** 标记的镜像 |

## 10. 安卓真机 Termux 部署

### 10.1 安装 Termux

在手机上安装 [Termux](https://f-droid.org/packages/com.termux/)（F-Droid 版本），然后：

```bash
pkg update && pkg upgrade
pkg install python
pip install openpaygo
```

### 10.2 部署控制器

**USB + adb（推荐）：**

```bash
# Mac 终端 — 手机 USB 连接并开启 USB 调试
cd ~/Desktop/paygo-platform
adb push controller/ /sdcard/controller/
```

手机 Termux 中：

```bash
termux-setup-storage
cp -r /sdcard/controller ~/controller
```

**或通过网络：**

```bash
# Termux 中
pkg install openssh
scp -r user@<Mac IP>:/Users/<user>/Desktop/paygo-platform/controller ~/controller
```

### 10.3 运行

```bash
cd ~/controller
python controller.py
```

## 11. 状态文件

控制器状态保存在 `~/.paygo/` 目录：

**`~/.paygo/state.json`**：
```json
{
  "secret_key": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
  "count": 2,
  "used_counts": [0, 1],
  "remaining_days": 90,
  "last_update": "2026-05-18",
  "status": "active"
}
```

| 字段 | 说明 |
|------|------|
| `secret_key` | 32 位 hex 设备密钥（出厂预设） |
| `count` | OpenPAYGO 当前 count 值 |
| `used_counts` | 已使用的 count 列表（内置防重放） |
| `remaining_days` | 剩余天数，`-1` 表示永久解锁 |
| `last_update` | 上次状态更新日期 |
| `status` | `unbound` / `active` / `locked` / `permanent` |

> `~/.paygo/used_tokens.json` 已废弃，OpenPAYGO 的 count 机制天然防重放。

**重置设备**：`rm -rf ~/.paygo`

## 12. Token 编码格式（OpenPAYGO 标准）

本项目采用 [OpenPAYGO](https://github.com/EnAccess/OpenPAYGO-python) 开源标准（v0.6.3），Token 为 **9 位纯数字**。

### 核心机制

| 特性 | 说明 |
|------|------|
| 加密 | SipHash-2-4 哈希链，每 Token 由上一个 Token 推导 |
| 唯一性 | count 递增 + 哈希链保证每次生成的 Token 不同 |
| 防重放 | count 机制内置，无需额外存储已用 Token 列表 |
| 密钥 | 每设备 32 位 hex 密钥（设备出厂预设） |

### Token 类型

| 类型 | 说明 |
|------|------|
| ADD_TIME (1) | 累加激活天数 |
| SET_TIME (2) | 设置绝对天数 |
| DISABLE_PAYG (3) | 永久解锁 |
| COUNTER_SYNC (4) | 计数器同步 |

### 示例

设备密钥 `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`，count=0，生成 30 天激活 Token：

```python
from openpaygo import generate_token, TokenType

new_count, token = generate_token(
    secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
    count=0,
    value=30,
    token_type=TokenType.ADD_TIME,
)
# → new_count=2, token="123456789"
```

**同一设备 + 同一天数，每次生成不同的 Token** — 这是 OpenPAYGO 对比旧版自研方案的核心改进。

## 13. 项目结构

```
paygo-platform/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── db.py                # 内存数据库（客户/Token/短信/汇率）
│   └── routers/
│       ├── auth.py          # 认证路由
│       ├── customers.py     # 客户 & 模拟支付 & 锁定/解锁 API（OpenPAYGO）
│       └── config.py        # 支付汇率配置 API
├── controller/
│   ├── controller.py        # 终端 UI（9位Token输入/密钥绑定/count显示）
│   └── state_manager.py     # 状态机 + 持久化（secret_key/count/used_counts）
├── static/
│   └── style.css            # 全局样式（绿色主题 #059669）
├── templates/
│   ├── base.html            # 基础布局
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面（模拟支付/SMS/锁定/永久解锁）
├── tests/
│   ├── conftest.py          # 全局 fixture + openpaygo 兼容补丁
│   ├── test_db.py           # 数据库
│   ├── test_auth.py         # 认证
│   ├── test_customers_api.py    # 客户 API
│   ├── test_state_manager.py    # 状态机
│   ├── test_config_api.py       # 支付汇率
│   ├── test_controller_integration.py  # 控制器集成
│   ├── test_integration.py      # 端到端集成
│   └── test_upgrade.py          # 五场景 MFI 演示
└── docs/
    └── superpowers/
        ├── specs/            # 设计文档
        └── plans/            # 实施计划
```

---

## 14. 快速验证流程（从头到尾 3 分钟）

```bash
# ─── 1. 启动后台 ───
cd ~/Desktop/paygo-platform
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# ─── 2. 运行测试（确保一切正常） ───
pytest tests/ -v
# 预期: 79 passed

# ─── 3. 创建客户 ───
curl -c /tmp/cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login

curl -b /tmp/cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo User","phone":"099999999","device_id":"DEMO-001","secret_key":"a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"}' \
  http://localhost:8000/api/customers

# ─── 4. 模拟支付，获取 9 位 Token ───
curl -b /tmp/cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"amount":5}' \
  http://localhost:8000/api/customers/<CID>/simulate-payment
# 记录返回的 9 位 token

# ─── 5. 控制器验证 Token ───
cd controller
python3 -c "
from openpaygo import decode_token, TokenType
from state_manager import load, save, apply_token

state = load()
state['secret_key'] = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'
token = input('Token: ').strip()
value, token_type, new_count, used_counts = decode_token(
    token=token,
    secret_key=state['secret_key'],
    count=state['count'],
    used_counts=state.get('used_counts'),
)
print(f'Type: {token_type}, Days: {value}')
if token_type == TokenType.ADD_TIME:
    apply_token(state, int(value), token_type, new_count, used_counts)
    save(state)
    print(f'激活成功！剩余 {state[\"remaining_days\"]} 天')
elif token_type == TokenType.ALREADY_USED:
    print('Token 已使用过')
elif token_type == TokenType.INVALID:
    print('Token 无效')
"

# ─── 6. 清理 ───
rm -rf ~/.paygo
```
