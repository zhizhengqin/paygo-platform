# 控制器 Token 无效问题排查

## 前置排查：确认控制器文件已升级（模拟器 Termux 中执行）

```bash
echo "=== 文件时间戳 ===" && ls -la ~/controller/ && echo "=== UI新特性检查 ===" && grep '\[D\]' ~/controller/controller.py && grep 'len(token) != 15' ~/controller/token_codec.py && echo "=== decode测试(15位) ===" && cd ~/controller && python3 -c "
from token_codec import generate, decode
t = generate('SN-KH-001', 30)
r = decode(t)
print(f'Token: {t} (len={len(t)})')
print(f'Decode: {r}')
print(f'旧8位Token被拒绝: {decode(\"07030303\")}')
" && echo "=== 缓存检查 ===" && ls -la ~/controller/__pycache__/ 2>/dev/null
```

**期望输出：**
- `grep '\[D\]'` 输出：`print("[N] 输入新Token  [D] 模拟天数流逝  [R] 重置  [Q] 退出")`
- `grep 'len(token) != 15'` 输出：`if len(token) != 15 or not token.isdigit():`
- decode 测试输出 15 位 Token，解码结果含 `'type': 1`
- 旧 8 位 Token `07030303` 返回 `None`

---

### 如果 grep 无输出或 decode 返回 None — 文件是旧版本

**步骤 1：在 Mac 终端确认推送正确文件**

```bash
cd ~/Desktop/paygo-platform
adb shell cat /sdcard/controller/controller.py | grep '\[D\]'
adb shell cat /sdcard/controller/token_codec.py | grep 'len(token) != 15'
```

如果 Mac 端 grep 有输出但模拟器端没有 → 文件未正确复制到 `~/controller`

**步骤 2：彻底重新部署（模拟器 Termux）**

```bash
# 先删除旧文件，再复制（不要用 cp -r 覆盖，旧文件可能残留）
rm -rf ~/controller
cp -r /sdcard/controller ~/controller

# 确认更新
grep '\[D\]' ~/controller/controller.py
grep 'len(token) != 15' ~/controller/token_codec.py
```

**步骤 3：如果仍不对 — 从 Mac 重新推送**

```bash
# Mac 终端
cd ~/Desktop/paygo-platform
adb shell rm -rf /sdcard/controller
adb push controller/ /sdcard/controller/

# 确认推送成功
adb shell ls -la /sdcard/controller/
```

然后在模拟器 Termux 重新执行步骤 2。

---

## 第 1 步：确认平台服务正在运行且为最新代码

在 Mac 浏览器打开 http://localhost:8000/login，确认能打开登录页。

如果不能，清除缓存后启动：

```bash
cd ~/Desktop/paygo-platform
source venv/bin/activate

# 清除所有 Python 缓存（重要！）
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# 停止旧进程
pkill -f "uvicorn app.main" 2>/dev/null

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**验证所有新路由已注册：**

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys,json
data=json.load(sys.stdin)
paths=sorted(data['paths'].keys())
expected=['/api/customers/{id}/simulate-payment','/api/sms','/api/config/payment-rates']
for p in expected:
    found=any(p.replace('{id}','{customer_id}') in x for x in paths)
    print(f'{'✓' if found else '✗'} {p}')
"
```

期望全部显示 `✓`。

---

## 第 2 步：用 curl 创建测试客户并模拟支付

**2.1 登录（保存 cookie）：**

```bash
curl -c /tmp/paygo-cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login
```

**2.2 新增客户：**

```bash
curl -b /tmp/paygo-cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"test","phone":"000","device_id":"SN-KH-001"}' \
  http://localhost:8000/api/customers
```

记下返回的 `id` 值。

**2.3 模拟支付（新 API — 直接生成 15 位 Token + SMS）：**

```bash
curl -b /tmp/paygo-cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"amount":5}' \
  http://localhost:8000/api/customers/{替换为实际id}/simulate-payment
```

**期望输出：**

```json
{
  "token": "005430030010574",
  "customer_id": "CXXXX",
  "days": 30,
  "sms": {
    "to": "000",
    "message": "[PAYGO Solar] 尊敬的用户，您已成功支付$5.00。您的太阳能激活码为：..."
  }
}
```

记下 `token` 的值（15 位数字）。

**2.4 在 Mac 终端本地验证 Token 可解码：**

```bash
cd ~/Desktop/paygo-platform/controller && python3 -c "
from token_codec import decode
result = decode('替换为实际15位token')
print(result)
"
```

期望输出 `{'device_id_hash': xxx, 'days': 30, 'type': 1}`。

---

## 第 3 步：在模拟器中输入 Token

在模拟器 Termux 中：

```bash
cd ~/controller
python3 controller.py
```

界面应显示：

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

1. 输入 `N`，回车
2. 看到 `Token:` 提示，输入第 2.3 步获取的 15 位 Token
3. 应显示 `✓ Token验证成功！增加30天。`

---

## 常见错误

| 现象 | 原因 | 解决 |
|------|------|------|
| 控制器界面无 `[D]` `[R]` 选项 | 文件是旧版本 | 按前置排查步骤彻底重新部署 |
| grep 无输出 | `cp -r` 未覆盖旧文件 | `rm -rf ~/controller` 后再 `cp -r` |
| 15 位 Token 输入后显示"无效" | token_codec.py 仍是 8 位版本 | 检查 `grep 'len(token) != 15'` 有无输出 |
| decode 输出 `None` | `__pycache__` 缓存了旧代码 | `rm -rf ~/controller/__pycache__` |
| `/api/sms` 返回 404 | 服务器未清除缓存 | Mac 端 `find . -name __pycache__ -exec rm -rf {} +` |
| 新 API 路由缺失 | 服务器进程跑了旧字节码 | `pkill -f uvicorn` 后清除缓存重启 |
| 登录后点击客户没反应 | 浏览器控制台 JS 报错，`/api/sms` 404 | 检查新路由是否全部注册 |
| curl 返回 401 | cookie 过期 | 重新执行登录命令 |
| Token 输入后显示"已过期" | Token 之前已用过（防重放） | 后台重新模拟支付生成新 Token |
| 模拟支付返回 400 | 金额不在汇率表中 | 使用 $5 或 $10 |
