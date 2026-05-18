# PAYGO 平台升级设计文档

**日期**: 2026-05-18  
**目标**: 支持 5 个 MFI 演示场景，升级 Token 编码、后台功能、SMS 模拟和终端脚本

---

## 1. 测试场景覆盖

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 一：首次支付解锁 | 后台模拟支付$5 → 15位Token → 手机输入 | ✓ Token验证成功！增加30天 |
| 二：再次续费 | 模拟支付$10 → 新Token → 手机输入 | 当前剩余90天 |
| 三：错误Token | 手机输入 `111111111111111` | ✗ Token无效 |
| 四：逾期锁定 | 控制器[D]快进耗尽天数 → 输入旧Token | Token已过期 |
| 五：永久解锁 | 后台永久解锁 → DISABLE_PAYG Token → 手机输入 | ✓✓✓ 贷款已结清！设备永久解锁！ |

---

## 2. Token 编码（8位 → 15位）

```
{device_hash:5}{value:4}{type:2}{checksum:4}
```

| 字段 | 位置 | 说明 |
|------|------|------|
| device_hash | 0:5 | sum(ord(c) for c in device_id) % 100000 |
| value | 5:9 | type=01 时编码天数，type=99 时填 0000 |
| type | 9:11 | 01=激活（PAY），99=永久解锁（DISABLE_PAYG） |
| checksum | 11:15 | (device_hash + value + type) % 10000 |

**约束**: 天数 1-3650，type 仅 01/99

**两套 codec 同步**: `app/token_engine.py`（服务端生成）和 `controller/token_codec.py`（终端离线解码）算法必须保持一致。

---

## 3. 状态模型

### 3.1 状态流转

```
unbound ──Token(type=01)──→ active ──天数归零或[D]快进──→ locked
                │                 │                    │
                │    Token(type=01)│                    │Token(type=01或99)
                └─────────────────┘                    │
                                                       ↓
                              permanent ←── Token(type=99)
```

### 3.2 状态定义

| 状态 | 含义 | 继电器 |
|------|------|--------|
| unbound | 未绑定 | 断开 |
| active | 已激活，天数递减 | 闭合 |
| locked | 已锁定（后台锁定或天数用尽） | 断开 |
| permanent | 永久解锁 | 闭合 |

### 3.3 状态文件 (`~/.paygo/state.json`)

```json
{
  "device_id_hash": 12345,
  "remaining_days": 90,
  "last_update": "2026-05-18",
  "status": "active"
}
```

permanent 状态时 `remaining_days` 固定为 -1（标记无限）。

---

## 4. 后台改动

### 4.1 新增"模拟支付"功能

- 在客户详情面板增加「模拟支付」区域
- 金额下拉选择: $5 / $10
- 默认汇率: $5=30天, $10=60天（通过 `/api/config/payment-rates` 查询）
- 点击后调用 API 生成15位 Token，返回 Token + SMS 预览
- API: `POST /api/customers/{id}/simulate-payment` body: `{amount: 5}`

### 4.2 新增"锁定设备"

- 客户详情面板增加「锁定设备」按钮，二次确认
- 设备状态变为 "locked"
- API: `POST /api/customers/{id}/lock`

### 4.3 新增"永久解锁"

- 客户详情面板增加「永久解锁」按钮，二次确认
- 生成 type=99 的 DISABLE_PAYG Token
- 弹出显示 Token + SMS 预览
- 客户状态变为 permanent
- API: `POST /api/customers/{id}/permanent-unlock`

### 4.4 SMS 模拟

- `simulate-payment` 和 `permanent-unlock` 返回体增加 `sms` 字段
- 返回格式:

```json
{
  "token": "0123400300101265",
  "customer_id": "...",
  "days": 30,
  "sms": {
    "to": "0888888001",
    "message": "[PAYGO Solar] 尊敬的用户，您的太阳能激活码为：01234 00300 10126 5。有效期30天。请尽快输入您的设备。"
  }
}
```

- 前端 token 结果弹窗同时展示 Token 码和短信预览卡片（含收件号码、短信全文）
- 客户详情面板底部展示历史短信记录

### 4.5 支付汇率配置

- API: `GET /api/config/payment-rates` 返回 `[{"amount": 5, "days": 30}, {"amount": 10, "days": 60}]`
- 内存存储，默认值硬编码

### 4.6 客户详情展示升级

- 状态显示: 🟢活跃 / 🔴已锁定 / ⭐永久解锁
- 设备编号格式: SN-KH-XXX
- 新增显示 Token 历史记录

### 4.7 数据库模型扩展

```python
# 客户记录新增字段
{
  "id": "...",
  "name": "...",
  "phone": "...",
  "device_id": "SN-KH-001",
  "remaining_days": 0,
  "status": "active",       # active / locked / permanent
  "created_at": "...",
  "locked_at": None,        # 锁定时间
}

# 新增短信记录存储
_sms_records: list[dict] = []
# {"id": "...", "customer_id": "...", "to": "088...", "message": "...", "sent_at": "..."}

# 新增支付汇率存储
_payment_rates: list[dict] = [
    {"amount": 5, "days": 30},
    {"amount": 10, "days": 60},
]
```

### 4.8 新增 API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/customers/{id}/simulate-payment` | 模拟支付，生成Token + SMS |
| POST | `/api/customers/{id}/lock` | 锁定设备 |
| POST | `/api/customers/{id}/permanent-unlock` | 永久解锁，生成DISABLE_PAYG + SMS |
| GET | `/api/config/payment-rates` | 获取支付汇率 |

---

## 5. 控制器终端改动

### 5.1 Token 解码 (token_codec.py)

- 8位扩展为15位
- 解析 type 字段，返回 `{device_id_hash, days, type}`
- type=99 时 days=0

### 5.2 状态管理 (state_manager.py)

- 新增 `"permanent"` 状态
- `apply_token()`: type=01 累加天数激活，type=99 调用 `apply_permanent_unlock()`
- `apply_permanent_unlock()`: 设置 status=permanent, remaining_days=-1
- `tick()`: permanent 状态不递减天数
- 防重放: 维护已用 Token 哈希集合，存储于 `~/.paygo/used_tokens.json`

### 5.3 防重放存储 (`~/.paygo/used_tokens.json`)

```json
{
  "hashes": ["a1b2c3d4e5f6a7b8", "f9e8d7c6b5a43210"]
}
```

用 token 完整字符串的 SHA256 前16位作为哈希。

### 5.4 终端 UI (controller.py)

- 输入接受15位 Token
- 新增 `[D]` 调试命令：输入天数直接递减 remaining_days，归零则 locked（隐藏选项，用于演示场景四）
- 区分错误提示:
  - 格式/校验错 → "✗ Token无效"
  - 防重放命中 → "Token已过期"
  - type=01 激活 → "✓ Token验证成功！增加X天。"
  - type=99 永久 → "✓✓✓ 贷款已结清！设备永久解锁！"
- 状态显示: 未绑定 / 已激活 / 已锁定 / 永久解锁
- 继电器: permanent=[闭合] 供电中

---

## 6. 文件改动清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `app/token_engine.py` | 重写 | 8位→15位，支持 type 编码，支持 DISABLE_PAYG |
| `app/db.py` | 修改 | 客户模型扩展，新增 payment-rates/sms 存储 |
| `app/routers/customers.py` | 扩展 | 新增 simulate-payment/lock/permanent-unlock 端点 |
| `app/routers/config.py` | 新增 | 支付汇率查询端点 |
| `app/main.py` | 微改 | 注册 config 路由 |
| `templates/dashboard.html` | 大改 | 模拟支付区、锁定/永久解锁按钮、SMS预览、短信记录 |
| `controller/token_codec.py` | 重写 | 8位→15位解码，type 识别 |
| `controller/state_manager.py` | 修改 | permanent 状态、防重放、tick 不递减 permanent |
| `controller/controller.py` | 修改 | 15位输入、[D]快进命令、新提示文案、UI 状态更新 |
| `tests/test_upgrade.py` | 新增 | 覆盖5个场景的升级测试用例 |

---

## 7. 测试场景与断言

### 场景一：首次支付解锁
- 创建客户 SN-KH-001，状态 locked
- 模拟支付 $5 → 生成15位Token，返回 sms 字段
- 控制器 decode: type=01, days=30
- apply_token: status=active, remaining_days=30
- 显示 "✓ Token验证成功！增加30天。"

### 场景二：续费叠加
- 模拟支付 $10 → 生成15位Token (60天)
- apply_token: remaining_days=30+60=90
- 显示 "当前剩余90天"

### 场景三：错误Token
- 输入 `111111111111111`
- decode 返回 None（checksum 不匹配）
- 显示 "✗ Token无效"

### 场景四：逾期锁定
- 控制器 [D] 命令快进耗尽天数 → status=locked
- 输入之前用过的旧Token
- 防重放检测命中 → 显示 "Token已过期"

### 场景五：永久解锁
- 后台 permanent-unlock → 生成 type=99 Token，返回 sms 字段
- decode: type=99
- apply_token: status=permanent, remaining_days=-1
- 显示 "✓✓✓ 贷款已结清！设备永久解锁！"
