# OpenPAYGO 标准迁移设计

**日期**: 2026-05-18  
**状态**: 已确认  
**决策**: 废弃自研 Token 实现，全面迁移至 [OpenPAYGO 开源标准](https://github.com/EnAccess/OpenPAYGO-python)（v0.6.3）

---

## 1. 背景

当前 paygo-platform 使用自研 15 位数字 Token 编码方案，存在两个关键缺陷：

- **Token 重复**: `generate_token(device_id, days)` 是纯函数，同设备同天数永远生成相同 Token，充值后控制器拒绝
- **安全性弱**: 简单校验和验证，无密钥保护，可被逆向伪造

OpenPAYGO 是 EnAccess Foundation 资助的离网太阳能行业开源标准，使用 SipHash 加密哈希链确保 Token 唯一性与安全性。

## 2. 技术方案

### 2.1 核心差异

| 维度 | 当前自研 | OpenPAYGO 标准 |
|---|---|---|
| Token 长度 | 固定 15 位 | 标准 9 位 |
| 安全性 | 校验和 `(hash+value+type)%10000` | SipHash 加密哈希链 |
| 唯一性 | 同设备同天数 = 同 Token | count 递增，每次生成不同 Token |
| 防重放 | 控制器存已用 Token 列表 | count 机制内置防重放 |
| 密钥 | 无 | 每设备 32 位 hex 密钥 |
| Token 类型 | 01(激活), 99(永久) | ADD_TIME, SET_TIME, DISABLE_PAYG, COUNTER_SYNC |
| Token 链 | 每次独立生成 | 新 Token 由上一个 Token + SipHash 推导 |

### 2.2 依赖

```text
requirements.txt 增加: openpaygo>=0.6.3
```

## 3. 数据模型变更

### 3.1 后端 Customer 记录 (app/db.py)

```diff
  {
    "id": "C36A8",
    "name": "Sok Heng",
    "phone": "312266600",
    "device_id": "SN-KH-001",
-   "remaining_days": 0,
+   "secret_key": "a1b2c3d4...",   // 32位hex，设备预设
+   "count": 0,                    // OpenPAYGO token count，初始0
    "status": "locked",
  }
```

- `remaining_days`: 删除（变为纯控制器侧状态）
- `secret_key`: 新增，创建客户时由后台录入（设备出厂预设）
- `count`: 新增，每次生成 Token 后更新为 `new_count`

### 3.2 控制器状态 ~/.paygo/state.json (controller/state_manager.py)

```diff
  {
-   "device_id_hash": 543,
+   "secret_key": "a1b2c3d4...",
+   "count": 0,
+   "used_counts": [],
    "remaining_days": 7,
    "last_update": "2026-05-18",
    "status": "active",
  }
```

- `~/.paygo/used_tokens.json`: 删除（count 机制替代）

### 3.3 后端 Token 审计记录

```diff
  {
-   "token": "005430030010574",
+   "token": "123456789",
+   "count": 2,
    "days": 30,
  }
```

## 4. Token 流程

### 4.1 生成（后端 → SMS）

```python
from openpaygo import generate_token, TokenType

# 激活 Token
new_count, token = generate_token(
    secret_key=customer["secret_key"],
    count=customer["count"],
    value=30,
    token_type=TokenType.ADD_TIME,
)
customer["count"] = new_count

# 永久解锁
new_count, token = generate_token(
    secret_key=customer["secret_key"],
    count=customer["count"],
    token_type=TokenType.DISABLE_PAYG,
)
customer["count"] = new_count
```

### 4.2 短信格式

```text
[PAYGO Solar] 尊敬的用户，您已成功支付$5.00。
您的太阳能激活码为：123456789。有效期30天。请尽快输入您的设备。
```

- 9 位纯数字，无空格分隔

### 4.3 验证（控制器）

```python
from openpaygo import decode_token, TokenType

value, token_type, new_count, used_counts = decode_token(
    token="123456789",
    secret_key=state["secret_key"],
    count=state["count"],
    used_counts=state.get("used_counts"),
)

if token_type == TokenType.INVALID:
    # 无效Token
elif token_type == TokenType.ALREADY_USED:
    # 已使用
elif token_type == TokenType.DISABLE_PAYG:
    state["status"] = "permanent"
elif token_type == TokenType.ADD_TIME:
    state["remaining_days"] += int(value)
    state["status"] = "active"

state["count"] = new_count
state["used_counts"] = used_counts
```

### 4.4 防重放

- count 递增机制：每次生成新 Token，count 跳至下一个有效值
- `decode_token` 返回 `ALREADY_USED` 拒绝重放
- `decode_token` 返回 `INVALID` 拒绝伪造
- 不需要额外的 `used_tokens.json` 文件

## 5. 文件变更清单

### 删除

| 文件 | 原因 |
|---|---|
| `app/token_engine.py` | openpaygo 替代 |
| `controller/token_codec.py` | openpaygo 替代 |
| `tests/test_token_codec.py` | 重写 |
| `tests/test_token_engine.py` | 重写 |

### 修改

| 文件 | 改动点 |
|---|---|
| `app/db.py` | Customer 加 `secret_key` + `count`；删除 `remaining_days` |
| `app/routers/customers.py` | `CustomerCreate` 加 `secret_key`；Token 生成用 openpaygo；SMS 去空格 |
| `controller/state_manager.py` | `secret_key` + `count` + `used_counts` 替换 `device_id_hash`；删除 `is_token_used`/`mark_token_used` |
| `controller/controller.py` | UI 文案适配 9 位 Token；[N] 输入校验改为 9 位 |
| `requirements.txt` | 加 `openpaygo` |
| `tests/test_customers_api.py` | 适配新 Token 格式 |
| `tests/test_integration.py` | 端到端测试适配 |
| `tests/test_state_manager.py` | 状态机适配 |
| `tests/test_controller_integration.py` | 控制器测试适配 |

### 不变

| 文件 | 原因 |
|---|---|
| `app/main.py` | 入口无变化 |
| `templates/` | 后续按需微调 |
| `static/` | 无变化 |
| `controller/state_manager.py` 中 `tick`/`fast_forward`/`reset` | 天数递减逻辑不变 |

## 6. 测试策略

| 测试文件 | 覆盖内容 |
|---|---|
| `tests/test_customers_api.py` | 创建客户（含 secret_key）、生成 9 位 Token、SMS 无空格、永久解锁、同设备两次充值生成不同 Token |
| `tests/test_integration.py` | 后端生成 → 控制器解码 → 激活 → 天数递减 → 锁定 → 再充值新 Token 有效、旧 Token 拒绝 |
| `tests/test_state_manager.py` | count 更新、used_counts 维护、permanent 状态、重放防护 |
| `tests/test_controller_integration.py` | 无效 Token 拒绝、已用 Token 拒绝、永久解锁流程 |

## 7. 迁移注意

1. **数据不兼容**: 旧版 `~/.paygo/state.json` 格式不同，删除后重新初始化
2. **旧 Token 全部失效**: 后台内存数据库重建，旧 15 位 Token 无意义
3. **密钥格式**: 32 位 hex 字符串，后台录入客户时需校验格式
4. **count 初始值**: 新设备 count=0，openpaygo 自动递增到正确奇偶性
5. **secret_key 来源**: 设备出厂预设，不通过后台自动生成；录入客户时手动填入或扫码
