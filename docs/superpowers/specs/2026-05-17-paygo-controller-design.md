# PAYGO 太阳能控制器模拟脚本 — 设计文档

## 概述

在安卓手机 Termux 环境中运行的 Python 命令行脚本，模拟 PAYGO 太阳能控制器的核心行为：接收激活 Token、本地解码验证、管理设备状态（激活/锁定）、天数递减。

## 设计决策

| 决策点 | 选择 |
|--------|------|
| Token 验证方式 | 本地自验证（B）— Token 编码设备 ID + 天数 |
| 设备绑定方式 | Token 自带设备 ID（B）— 首次输入时自动绑定 |
| Token 输入方式 | 手动输入（A）— 终端直接键入 |
| 平台通信 | 纯离线工作（B）— 不主动连接平台 |

## Token 编码算法

8 位数字 Token 格式：

```
{device_hash:4位}{days:3位}{checksum:1位}
```

- **device_hash** = (device_id 每个字符 ord 值求和) % 10000，左侧补零到 4 位
- **days** = 天数 (1-365)，左侧补零到 3 位
- **checksum** = (hashed_device + days) % 10

示例（device_id=`Solar-001`, days=30）：
- char sum = 83+111+108+97+114+45+48+48+49 = 703
- hash = 0703, days = 030
- checksum = (703+30) % 10 = 3
- Token = `07030303`

## 状态机

```
UNBOUND ──输入有效Token──▶ ACTIVE ──天数归零──▶ LOCKED
   ◀──────────────────────────────── 输入新Token ──▶ ACTIVE
```

- **UNBOUND** — 首次运行，未绑定设备，等待输入 Token
- **ACTIVE** — 已绑定设备，剩余天数 > 0，继电器闭合（供电中）
- **LOCKED** — 剩余天数归零，继电器断开（断电），可输入新 Token 恢复

Token 叠加规则：ACTIVE 状态下输入新 Token（同设备），天数累加（新天数 = 剩余天数 + Token 天数）。

## 文件结构

```
controller/
├── controller.py     # 主入口，终端 UI + 交互循环
├── token_codec.py    # Token 编解码（generate / decode / verify）
└── state_manager.py  # 状态机 + JSON 持久化 (~/.paygo/state.json)
```

### controller.py — 主入口

- 终端显示循环（刷新间隔 1s 或按交互键）
- 显示当前状态面板（设备 ID、状态指示灯、剩余天数、继电器状态）
- 交互：`[N] 输入新Token  [Q] 退出`
- 启动时检查本地状态文件，存在则恢复状态，不存在则进入 UNBOUND

### token_codec.py — Token 编解码

纯函数模块，无外部依赖，与 `app/token_engine.py` 共享相同算法：

```python
def generate(device_id: str, days: int) -> str  # 生成 8 位 Token
def decode(token: str) -> dict | None            # 返回 {device_id_hash, days} 或 None
```

### state_manager.py — 状态管理

```python
class StateManager:
    def load() -> dict        # 从 ~/.paygo/state.json 加载
    def save(state: dict)     # 持久化到 ~/.paygo/state.json
    def apply_token(state, token)  # 解码 → 绑定设备 → 叠加天数
    def tick(state)           # 日期推进 → 递减天数 → 状态转换
```

本地存储格式（`~/.paygo/state.json`）：

```json
{
  "device_id": "Solar-001",
  "remaining_days": 27,
  "last_update": "2026-05-17",
  "status": "active"
}
```

## 终端界面

```
╔══════════════════════════════╗
║    PAYGO 太阳能控制器       ║
╠══════════════════════════════╣
║ 设备 ID:  Solar-001         ║
║ 状态:    ● 已激活           ║
║ 剩余天数: 27 天             ║
║ 继电器:  [闭合] 供电中      ║
╚══════════════════════════════╝
[N] 输入新Token  [Q] 退出
```

UNBOUND 状态时设备 ID 显示为 `--`，状态显示 `○ 未绑定`，继电器显示 `[断开]`。

## 平台侧改动

| 文件 | 改动 |
|------|------|
| `app/token_engine.py` | `generate_token()` 从随机数改为结构化编码，复用 `controller/token_codec.py` 的 `generate()` 逻辑 |
| `tests/test_token_engine.py` | 更新测试用例匹配新 Token 格式（验证 device_hash + days + checksum 编码正确） |

注：由于 controller 目录需要独立拷贝到手机运行，平台侧 `token_engine.py` 与 `controller/token_codec.py` 各自实现相同算法，不引入跨目录 import。

## 技术约束

- 无第三方依赖（仅 Python 3.10+ 标准库）
- 单文件可运行，也支持模块导入
- 所有持久化数据仅写 `~/.paygo/` 目录
- Termux 环境下 `~` 即 `/data/data/com.termux/files/home/`

## 测试策略

在平台侧 `tests/` 目录新增：

| 测试文件 | 内容 |
|----------|------|
| `tests/test_token_codec.py` | Token encode/decode 正确性、checksum 校验、边界值（天数 1/365）、无效 Token 拒绝 |

控制器自身的集成测试在 PC 上直接运行 `controller/controller.py` 验证交互流程。
