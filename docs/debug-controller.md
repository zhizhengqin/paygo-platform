# 控制器 Token 无效问题排查

## 第 1 步：在模拟器 Termux 中验证 decode 是否正常

在模拟器的 Termux 终端中执行：

```bash
cd ~/controller
python3 -c "from token_codec import decode; print(decode('07030303'))"
```

**期望输出:**

```
{'device_id_hash': 703, 'days': 30}
```

如果输出 `None`，说明代码没推送到位，重新执行推送：

```bash
# 在 Mac 终端执行
cd ~/Desktop/paygo-platform
~/Library/Android/sdk/platform-tools/adb push controller/ /sdcard/controller/
```

```bash
# 在模拟器 Termux 执行
cp -r /sdcard/controller ~/controller
```

---

## 第 2 步：确认平台服务正在运行

在 Mac 浏览器打开 http://localhost:8000/login

确认能打开登录页。如果不能，启动服务：

```bash
cd ~/Desktop/paygo-platform
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 第 3 步：用 curl 创建测试客户并获取 Token

**3.1 登录（保存 cookie）：**

```bash
curl -c /tmp/paygo-cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login
```

**3.2 新增一个客户：**

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

**3.3 为这个客户生成 Token：**

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

---

## 第 4 步：在模拟器中输入 Token

在模拟器 Termux 中：

```bash
cd ~/controller
python3 controller.py
```

1. 看到 `>` 提示符，输入 `N` 后回车
2. 看到 `Token:` 提示，输入第 3 步获取的 8 位数字 Token，回车
3. 应该显示 `激活成功！+30 天`
4. 界面刷新显示设备已激活

---

## 常见错误

| 现象 | 原因 |
|------|------|
| decode 输出 `None` | controller/ 目录代码不是最新的，重新 adb push + cp |
| curl 返回 401 | cookie 过期，重新执行登录命令 |
| curl 返回 404 | 客户 id 写错了，检查第 3.2 步的输出 |
