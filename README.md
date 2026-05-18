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
git clone <仓库地址>
cd paygo-platform
pip install -r requirements.txt
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

## 4. 运行测试

```bash
source venv/bin/activate

# 运行全部测试（117 个）
pytest tests/ -v

# 按模块运行
pytest tests/test_db.py -v                     # 数据库 (16 tests)
pytest tests/test_auth.py -v                   # 认证 (6 tests)
pytest tests/test_customers_api.py -v          # 客户API (17 tests)
pytest tests/test_token_engine.py -v           # Token引擎 (16 tests)
pytest tests/test_token_codec.py -v            # 控制器编解码 (22 tests)
pytest tests/test_state_manager.py -v          # 状态机 (23 tests)
pytest tests/test_config_api.py -v             # 支付汇率 (2 tests)
pytest tests/test_controller_integration.py -v # 控制器集成 (2 tests)
pytest tests/test_integration.py -v            # 端到端集成 (3 tests)
pytest tests/test_upgrade.py -v                # 五场景演示 (10 tests)
```

## 5. 五个 MFI 演示场景

### 场景一：首次支付解锁

1. 打开运营后台 http://localhost:8000/dashboard
2. 新增客户：姓名 `Sok Heng`，电话 `0888888001`，设备编号 `SN-KH-001`
3. 确认客户状态显示为 **🔴 已锁定**
4. 在「模拟支付」区域选择 **$5.00 — 30天**，点击「确认支付」
5. 弹出 15 位 Token 和短信预览卡片
6. 在手机 Termux 中输入该 Token
7. 验证显示：`✓ Token验证成功！增加30天。当前剩余30天`

### 场景二：再次续费

1. 再次为 SN-KH-001 模拟支付 **$10.00 — 60天**
2. 在手机输入新 Token
3. 验证显示：`当前剩余90天`（30 + 60）

### 场景三：错误Token

1. 在手机输入 `111111111111111`
2. 验证显示：`✗ Token无效`

### 场景四：逾期锁定

1. 在手机端按 `[D]`，输入快进天数耗尽剩余天数，设备自动锁定
2. （或后台点击「锁定设备」，状态变为 🔴 已锁定）
3. 再次输入之前用过的旧 Token
4. 验证显示：`Token已过期`

### 场景五：贷款结清永久解锁

1. 后台点击「⭐ 永久解锁」，在确认弹窗中确认
2. 弹出永久解锁 Token（type=99）和短信卡片
3. 手机输入该 Token
4. 验证显示：`✓✓✓ 贷款已结清！设备永久解锁！`

## 6. 页面操作流程

### 6.1 登录

1. 打开 `http://localhost:8000/login`
2. 输入账号 `admin`，密码 `admin123`
3. 点击"登录"，进入主界面

### 6.2 新增客户

1. 在左侧面板点击 **"+ 新增"**
2. 填写姓名、电话、设备编号（如 `SN-KH-001`）
3. 点击"确认添加"

### 6.3 查看客户详情

- 点击客户列表中的客户，右侧显示详细信息及状态（🟢活跃 / 🔴已锁定 / ⭐永久解锁）

### 6.4 模拟支付

1. 选中客户，在详情面板「💰 模拟支付」区域选择金额
2. 点击「💳 模拟支付」
3. 弹窗显示 15 位 Token 和模拟短信卡片

### 6.5 锁定设备

1. 选中客户，点击「🔒 锁定设备」
2. 确认后客户状态变为「🔴 已锁定」

### 6.6 永久解锁

1. 选中客户，点击「⭐ 永久解锁」
2. 确认后弹出 DISABLE_PAYG Token（type=99），状态变为「⭐ 永久解锁」

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
| POST | `/api/customers` | 新增客户 (JSON: name, phone, device_id) |
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

# 新增客户
curl -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Sok Heng","phone":"0888888001","device_id":"SN-KH-001"}' \
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

## 8. 使用 Android 模拟器测试控制器（macOS）

### 8.1 安装 Android Studio

1. 打开 https://developer.android.com/studio 下载 macOS 版本
2. 双击 `.dmg`，将 **Android Studio.app** 拖入 `Applications`
3. 首次打开选择 **Standard** 安装，等待 SDK 下载完成

### 8.2 创建安卓虚拟设备 (AVD)

1. Android Studio → **More Actions** → **Virtual Device Manager**
2. 点击 **Create device (+)**，选择 **Pixel 6/7**，Next
3. 选择系统镜像 **Tiramisu (API 33)** 或更高，Download → Next → Finish

### 8.3 启动模拟器

1. Device Manager 中点击设备旁的 **▶ 播放**
2. 等待启动到安卓桌面

### 8.4 确认 adb 可用

```bash
~/Library/Android/sdk/platform-tools/adb devices
# 应显示: emulator-5554   device
```

> 方便起见：`echo 'export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"' >> ~/.zshrc && source ~/.zshrc`

### 8.5 安装 Termux 到模拟器

```bash
# 下载 Termux APK（F-Droid）
curl -L -o ~/Downloads/termux.apk \
  https://f-droid.org/repo/com.termux_118.apk

# 安装到模拟器
~/Library/Android/sdk/platform-tools/adb install ~/Downloads/termux.apk
```

### 8.6 在 Termux 中安装 Python

在模拟器的 Termux 中：

```bash
pkg update && pkg upgrade
pkg install python
```

### 8.7 部署控制器脚本

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

### 8.8 运行控制器

```bash
cd ~/controller
python controller.py
```

界面显示：

```
╔══════════════════════════════╗
║    PAYGO 太阳能控制器       ║
╠══════════════════════════════╣
║ 设备:   --                  ║
║ 状态:   未绑定              ║
║ 剩余天数: 0 天               ║
║ 继电器: [断开]              ║
╚══════════════════════════════╝
[N] 输入新Token  [D] 模拟天数流逝  [R] 重置  [Q] 退出
```

### 8.9 操作说明

| 操作 | 按键 | 说明 |
|------|------|------|
| 输入 Token | `N` | 输入 15 位数字 Token |
| 模拟天数流逝 | `D` | 输入天数直接递减剩余天数（演示用） |
| 重置 | `R` | 清除绑定和天数，恢复未绑定状态 |
| 退出 | `Q` | 保存状态并退出 |

### 8.10 重新部署（代码更新后）

```bash
# Mac 终端
cd ~/Desktop/paygo-platform
adb push controller/ /sdcard/controller/

# 模拟器 Termux
cp -r /sdcard/controller ~/controller
```

### 8.11 常见问题

| 问题 | 解决方法 |
|------|----------|
| **模拟器启动后黑屏** | Device Manager → ▼ → **Cold Boot Now** |
| **adb devices 无设备** | `adb kill-server && adb devices` |
| **termux-setup-storage 无反应** | 安卓设置 → 应用 → Termux → 权限 → 开启存储 |
| **模拟器卡顿** | Device Manager → 编辑 → Graphics → **Hardware - GLES 2.0** |
| **Apple Silicon 选不了镜像** | 选择带 **arm64-v8a** 标记的镜像 |

## 9. 安卓真机 Termux 部署

### 9.1 安装 Termux

在手机上安装 [Termux](https://f-droid.org/packages/com.termux/)（F-Droid 版本），然后：

```bash
pkg update && pkg upgrade
pkg install python
```

### 9.2 部署控制器

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

### 9.3 运行

```bash
cd ~/controller
python controller.py
```

## 10. 状态文件

控制器状态保存在 `~/.paygo/` 目录：

**`~/.paygo/state.json`**：
```json
{
  "device_id_hash": 12345,
  "remaining_days": 90,
  "last_update": "2026-05-18",
  "status": "active"
}
```

- `device_id_hash` — 设备 ID 的数字哈希（5 位）
- `remaining_days` — 剩余天数，`-1` 表示永久解锁
- `last_update` — 上次状态更新日期
- `status` — `unbound` / `active` / `locked` / `permanent`

**`~/.paygo/used_tokens.json`**：
```json
{
  "hashes": ["a1b2c3d4e5f6a7b8"]
}
```
已用 Token 的 SHA256 哈希（防重放）。

**重置设备**：`rm -rf ~/.paygo`

## 11. Token 编码格式

Token 为 15 位数字，编码设备 ID、天数和类型，控制器可离线解码验证：

```
{device_hash:5位}{value:4位}{type:2位}{checksum:4位}
```

| 字段 | 位置 | 说明 |
|------|------|------|
| device_hash | 0-4 | `sum(ord(c) for c in device_id) % 100000` |
| value | 5-8 | type=01 时编码天数(1-3650)，type=99 时填 0000 |
| type | 9-10 | 01=激活(PAY)，99=永久解锁(DISABLE_PAYG) |
| checksum | 11-14 | `(device_hash + value + type) % 10000` |

**示例**：`SN-KH-001` + 30天 → `0123400300101265`

## 12. 项目结构

```
paygo-platform/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── db.py                # 内存数据库（客户/Token/短信/汇率）
│   ├── token_engine.py      # Token 生成引擎（15位编码）
│   └── routers/
│       ├── auth.py          # 认证路由
│       ├── customers.py     # 客户 & 模拟支付 & 锁定/解锁 API
│       └── config.py        # 支付汇率配置 API
├── controller/
│   ├── controller.py        # 终端 UI（15位输入/[D]快进/防重放）
│   ├── token_codec.py       # Token 编解码（15位离线验证）
│   └── state_manager.py     # 状态机 + 持久化 + 防重放
├── static/
│   └── style.css            # 全局样式（绿色主题 #059669）
├── templates/
│   ├── base.html            # 基础布局
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面（模拟支付/SMS/锁定/永久解锁）
├── tests/
│   ├── test_db.py
│   ├── test_auth.py
│   ├── test_customers_api.py
│   ├── test_token_engine.py
│   ├── test_token_codec.py
│   ├── test_state_manager.py
│   ├── test_config_api.py
│   ├── test_controller_integration.py
│   ├── test_integration.py
│   └── test_upgrade.py      # 五场景 MFI 演示集成测试
└── docs/
    └── superpowers/
        ├── specs/            # 设计文档
        └── plans/            # 实施计划
```
