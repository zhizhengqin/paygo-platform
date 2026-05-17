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

## 7. 使用 Android 模拟器测试控制器（macOS）

如果手边没有安卓手机，可以在 macOS 上用 **Android Studio 模拟器** 来运行控制器脚本。

### 7.1 安装 Android Studio

1. 打开 https://developer.android.com/studio 下载 macOS 版本（Apple Silicon 选 ARM64，Intel 选 x86_64）
2. 下载完成后，双击 `.dmg` 文件，将 **Android Studio.app** 拖入 `Applications` 文件夹
3. 首次打开 Android Studio，按提示完成安装向导：
   - 选择 **Standard** 安装类型（推荐）
   - 选择主题（深色/浅色随意）
   - 等待 SDK 组件下载完成（约 1-2 GB，需联网）
4. 安装完成后进入欢迎界面

### 7.2 创建安卓虚拟设备 (AVD)

1. 在 Android Studio 欢迎界面，点击左侧 **More Actions** → **Virtual Device Manager**

   > 如果已经在项目中，点击顶部菜单 **Tools** → **Device Manager**，然后点击 **+** 号

2. 点击 **Create device (+)** 按钮

3. **选择硬件型号**：选择一个手机型号（推荐 **Pixel 6** 或 **Pixel 7**），点击 **Next**

4. **选择系统镜像**（模拟器里的安卓版本）：
   - 推荐选择 **Tiramisu (API 33)** 或 **UpsideDownCake (API 34)**
   - 点击镜像名称旁的 **Download** 按钮（蓝色文字）下载镜像
   - 下载完成后选中该镜像，点击 **Next**

5. **配置 AVD**：
   - AVD Name：可以保持默认或改成 `PaygoTest`
   - Startup orientation：**Portrait**（竖屏）
   - 其他保持默认即可
   - 点击 **Finish** 完成创建

### 7.3 启动模拟器

1. 在 Device Manager 窗口，找到刚创建的设备，点击右侧的 **▶ 播放按钮**

2. 等待模拟器启动（首次约 1-2 分钟），直到看到安卓桌面：

   - 底部显示虚拟导航栏（返回/主页/最近）
   - 顶部有状态栏

3. **让模拟器保持运行**，接下来在终端中通过 `adb` 操作它

### 7.4 确认 adb 命令可用

`adb`（Android Debug Bridge）随 Android Studio 一起安装，位于 SDK 目录中。

打开 macOS 的 **终端**（Terminal.app），执行以下命令确认 adb 可用：

```bash
# 方法一：直接使用完整路径（推荐新手）
~/Library/Android/sdk/platform-tools/adb devices
```

如果显示类似以下内容，说明模拟器已连接：

```
List of devices attached
emulator-5554   device
```

**常见问题**：如果提示 `No such file or directory`：
1. 在 Android Studio 中点击 **More Actions** → **SDK Manager**
2. 切换到 **SDK Tools** 标签页
3. 确认 **Android SDK Platform-Tools** 已勾选；如未勾选则勾选并点击 **Apply** 等待安装
4. 安装完毕后重新执行上述命令

> **提示**：为了方便后续使用，可以将 adb 加入 PATH。在终端执行：
> ```bash
> echo 'export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"' >> ~/.zshrc
> source ~/.zshrc
> ```
> 之后就可以直接用 `adb` 而不用写完整路径。

### 7.5 安装 Termux 到模拟器

Termux 不通过 Google Play 分发，需要手动下载 APK 安装。

**步骤一：下载 Termux APK**

在终端中执行：

```bash
# 下载 Termux APK（从 F-Droid 官方仓库）
curl -L -o ~/Downloads/termux.apk \
  https://f-droid.org/repo/com.termux_118.apk
```

> 如果上述链接失效，可以去 https://f-droid.org/packages/com.termux/ 查看最新版本，复制下载链接替换上面的 URL。

**步骤二：安装到模拟器**

```bash
~/Library/Android/sdk/platform-tools/adb install ~/Downloads/termux.apk
```

安装成功后终端显示 `Success`。

**步骤三：在模拟器中打开 Termux**

1. 在模拟器中向上滑动打开应用抽屉
2. 找到并点击 **Termux** 图标
3. 首次启动会自动初始化（约 10-20 秒），显示命令行提示符

### 7.6 在 Termux 中安装 Python

在模拟器的 Termux 窗口中，依次执行：

```bash
# 更新软件源
pkg update

# 出现提示 [Y/n] 时直接按回车（或输入 y）

# 升级已安装包
pkg upgrade

# 安装 Python
pkg install python
```

完成后再检查 Python 版本：

```bash
python --version
# 应显示 Python 3.x.x
```

### 7.7 部署控制器脚本

**步骤一：从 Mac 推送文件到模拟器**

在 Mac 终端中执行：

```bash
# 进入项目目录
cd ~/Desktop/paygo-platform

# 推送 controller 目录到模拟器的共享存储
~/Library/Android/sdk/platform-tools/adb push controller/ /sdcard/controller/
```

推送成功会显示类似 `controller/token_codec.py: 1 file pushed.` 等信息。

**步骤二：在 Termux 中复制控制器**

切回模拟器的 Termux 窗口，执行：

```bash
# 设置 Termux 访问共享存储的权限
termux-setup-storage
```

模拟器会弹出权限请求，点击 **Allow** 或 **允许**。

然后复制文件：

```bash
cp -r /sdcard/controller ~/controller
ls ~/controller/
# 应显示三个文件: controller.py  token_codec.py  state_manager.py
```

### 7.8 运行控制器

在模拟器的 Termux 中：

```bash
cd ~/controller
python controller.py
```

将看到控制器界面：

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

按 `Q` 退出回到 Mac 终端继续下一步。

### 7.9 完整测试流程

现在来跑一次完整的端到端测试。

**准备：启动平台服务**

Mac 终端中：

```bash
cd ~/Desktop/paygo-platform
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**步骤 1：在运营后台创建客户**

1. 打开 Mac 浏览器，访问 **http://localhost:8000/login**
2. 输入账号 `admin`，密码 `admin123`，登录
3. 在左侧面板点击 **"+ 新增"**
4. 填写信息：
   - 姓名：`Sok Heng`
   - 电话：`0888888001`
   - 设备编号：`Solar-001`
5. 点击 **"确认添加"**

**步骤 2：生成激活 Token**

1. 在左侧客户列表中点击刚创建的 **Sok Heng**
2. 在右侧详情面板中点击 **"生成激活码"**
3. 输入天数：`30`
4. 确认后弹出 8 位 Token，例如 `07030303`
5. **记下这个 Token**（点击可复制）

**步骤 3：在模拟器中激活设备**

1. 切回模拟器的 Termux 窗口
2. 输入 `python ~/controller/controller.py` 启动控制器
3. 按 `N`，出现 `Token:` 提示
4. 输入从后台复制的 Token，按回车
5. 看到 "激活成功！+30 天"
6. 界面刷新显示：
   ```
   ║ 设备:   #0703                ║
   ║ 状态:   ● 已激活             ║
   ║ 剩余天数: 30 天               ║
   ║ 继电器: [闭合] 供电中        ║
   ```

**步骤 4：验证状态持久化**

在 Termux 中按 `Q` 退出控制器，然后重新运行：

```bash
python ~/controller/controller.py
```

应显示状态保持不变（剩余天数仍然正确），证明持久化生效。

### 7.10 重新部署（代码更新后）

修改了 `controller/` 目录下的代码后，重新推送：

```bash
# Mac 终端中
cd ~/Desktop/paygo-platform
~/Library/Android/sdk/platform-tools/adb push controller/ /sdcard/controller/

# 模拟器 Termux 中
cp -r /sdcard/controller ~/controller
```

不需要重新启动模拟器或重新安装 Termux。

### 7.11 常见问题

| 问题 | 解决方法 |
|------|----------|
| **模拟器启动后黑屏** | 在 Device Manager 中点击设备旁的 ▼ 箭头 → **Cold Boot Now** |
| **adb devices 无设备** | 确认模拟器已完全启动到桌面；重启 adb：`~/Library/Android/sdk/platform-tools/adb kill-server && ~Library/Android/sdk/platform-tools/adb devices` |
| **adb install 报 INSTALL_FAILED** | 检查模拟器存储空间，或在 Device Manager 中 **Wipe Data** |
| **Termux 下载链接失效** | 访问 https://f-droid.org/packages/com.termux/ 获取最新链接 |
| **termux-setup-storage 无反应** | 手动在安卓设置 → 应用 → Termux → 权限 → 开启存储权限 |
| **模拟器非常卡顿** | macOS 确保开启硬件加速：Device Manager → 设备编辑 → Graphics → **Hardware - GLES 2.0** |
| **Mac Apple Silicon 模拟器选不了镜像** | 选择带 **arm64-v8a** 标记的系统镜像 |

---

## 8. 控制器模拟脚本（安卓真机 Termux）

如果使用真实安卓手机（而非模拟器），按以下步骤操作。

### 8.1 安装 Termux

1. 在安卓手机上安装 [Termux](https://f-droid.org/packages/com.termux/)（推荐 F-Droid 版本）
2. 打开 Termux，安装 Python：

```bash
pkg update && pkg upgrade
pkg install python
```

### 8.2 部署控制器

将 `controller/` 目录拷贝到手机：

**方式一：USB + adb（推荐）**

```bash
# Mac 终端——手机通过 USB 连接并开启 USB 调试
cd ~/Desktop/paygo-platform
adb push controller/ /sdcard/controller/
```

然后在手机 Termux 中：

```bash
termux-setup-storage
cp -r /sdcard/controller ~/controller
```

**方式二：直接拷贝（USB / 文件管理器）**

1. 将项目的 `controller/` 目录复制到手机存储
2. 在 Termux 中：`cp -r /sdcard/controller ~/controller`

**方式三：通过网络传输**

Mac 终端查看 IP：

```bash
ipconfig getifaddr en0
# 或
ifconfig | grep "inet " | grep -v 127.0.0.1
```

在 Termux 中：

```bash
pkg install openssh
scp -r user@<Mac的IP>:/Users/<用户名>/Desktop/paygo-platform/controller ~/controller
```

### 8.3 运行控制器

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

### 8.4 操作说明

| 操作 | 按键 | 说明 |
|------|------|------|
| 输入 Token | `N` | 输入 8 位数字 Token，激活或续费设备 |
| 退出 | `Q` | 保存状态并退出控制器 |

**首次激活流程：**

1. 在运营后台选中客户，点击"生成激活码"，输入天数（如 30 天）
2. 后台显示 8 位数字 Token，如 `07030303`
3. 在 Termux 中运行 `python controller.py`
4. 按 `N`，输入 Token
5. 显示 "激活成功！+30 天"，设备绑定到该 Token 编码的设备 ID

**续费叠加：**

- 设备在 ACTIVE 状态下，输入新的同设备 Token，天数自动累加
- 例如：剩余 10 天 + 新 Token 30 天 = 40 天

**设备锁定与重启：**

- 剩余天数归零后，设备自动变为 LOCKED 状态（继电器断开）
- LOCKED 状态下可以输入新 Token 重新激活

### 8.5 状态文件

控制器状态保存在 `~/.paygo/state.json`：

```json
{
  "device_id_hash": 703,
  "remaining_days": 27,
  "last_update": "2026-05-17",
  "status": "active"
}
```

- `device_id_hash` — 设备 ID 的数字哈希
- `remaining_days` — 当前剩余天数
- `last_update` — 上次状态更新日期
- `status` — `unbound` / `active` / `locked`

**重置设备**：`rm -rf ~/.paygo` 即可恢复到未绑定状态。

### 8.6 Token 编码格式

Token 为 8 位数字，内嵌设备 ID 和天数信息，控制器可离线解码验证：

```
{device_hash:4位}{days:3位}{checksum:1位}
```

- 前 4 位：设备 ID 哈希（设备 ID 各字符码求和 % 10000）
- 中间 3 位：天数（1-365）
- 末 1 位：校验位 `(device_hash + days) % 10`

---

## 9. 项目结构

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
