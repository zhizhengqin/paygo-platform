# 控制器 Token 无效问题排查

## 前置排查（模拟器 Termux 中执行）

```bash
echo "=== 文件时间戳 ===" && ls -la ~/controller/ && echo "=== decode测试 ===" && cd ~/controller && python3 -c "from token_codec import decode; print(decode('07030303'))" && echo "=== 缓存检查 ===" && ls -la ~/controller/__pycache__/ 2>/dev/null
```

**期望输出：**
- `controller.py` 大小约 2509 字节，日期为 5月18日
- `state_manager.py` 大小约 1953 字节，日期为 5月18日
- decode 测试输出 `{'device_id_hash': 703, 'days': 30}`

**如果 decode 输出 `None`：** 清除缓存后重试

```bash
rm -rf ~/controller/__pycache__ && cd ~/controller && python3 -c "from token_codec import decode; print(decode('07030303'))"
```

**如果仍输出 `None`：** 文件仍是旧版本，重新部署（Mac 终端）

```bash
cd ~/Desktop/paygo-platform
~/Library/Android/sdk/platform-tools/adb shell rm -rf /sdcard/controller
~/Library/Android/sdk/platform-tools/adb push controller/ /sdcard/controller/
```

然后在模拟器 Termux：

```bash
rm -rf ~/controller && cp -r /sdcard/controller ~/controller && rm -rf ~/controller/__pycache__ && cd ~/controller && python3 -c "from token_codec import decode; print(decode('07030303'))"
```

应输出 `{'device_id_hash': 703, 'days': 30}`。

---

## 第 1 步：确认平台服务正在运行

在 Mac 浏览器打开 http://localhost:8000/login

确认能打开登录页。如果不能，启动服务：

```bash
cd ~/Desktop/paygo-platform
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 第 2 步：用 curl 创建测试客户并获取 Token

**2.1 登录（保存 cookie）：**

```bash
curl -c /tmp/paygo-cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login
```

**2.2 新增一个客户：**

```bash
curl -b /tmp/paygo-cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"test","phone":"000","device_id":"Solar-001"}' \
  http://localhost:8000/api/customers
```

**期望输出类似：**

```json
{"id":"C135F","name":"test","phone":"000","device_id":"Solar-001","remaining_days":0,"status":"active","created_at":"2026-05-18"}
```

记下返回的 `id` 值（例如 `C135F`），下一步要用。

**2.3 为这个客户生成 Token：**

把下面命令中的 `C135F` 替换为上一步返回的实际 id：

```bash
curl -b /tmp/paygo-cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"days":30}' \
  http://localhost:8000/api/customers/C135F/token
```

**期望输出类似：**

```json
{"token":"07030303","customer_id":"C135F","days":30}
```

记下 `token` 的值（8 位数字）。

**2.4 验证 Token 可解码（Mac 终端）：**

```bash
cd ~/Desktop/paygo-platform && python3 -c "from controller.token_codec import decode; print(decode('替换为实际token'))"
```

---

## 第 3 步：在模拟器中输入 Token

在模拟器 Termux 中：

```bash
cd ~/controller
python3 controller.py
```

1. 看到 `>` 提示符，输入 `N` 后回车
2. 看到 `Token:` 提示，输入第 2 步获取的 8 位数字 Token，回车
3. 应该显示 `激活成功！+30 天`
4. 界面刷新显示设备已激活

---

## 常见错误

| 现象 | 原因 | 解决 |
|------|------|------|
| decode 输出 `None` | __pycache__ 缓存了旧代码 | `rm -rf ~/controller/__pycache__` |
| decode 输出 `None` | controller/ 文件是旧版本 | 按前置排查中的步骤重新部署 |
| curl 返回 401 | cookie 过期 | 重新执行登录命令 |
| curl 返回 404 | 客户 id 写错了 | 检查第 2.2 步的输出 |
| Token 输入后显示无效 | 复制时带了空格或换行 | 手动输入 Token，不要粘贴 |
