# PAYGO 太阳能平台 — 运营后台操作手册

柬埔寨太阳能 PAYGO（Pay-As-You-Go）运营管理平台。通过 MFI 合作，客户分期付款购买太阳能系统，还款后生成 OpenPAYGO Token 延长设备使用期限。

---

## 1. 快速启动

```bash
# 确保 PostgreSQL 15 和 Redis 8 已运行
# 首次启动自动创建表 + 种子数据

cd paygo-platform
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：**http://localhost:8000/dashboard**
登录：`admin` / `admin123`

> 首次启动自动创建 8 张表，种子 5 档贷款产品和支付汇率。运行 `scripts/seed_demo_data.py` 可加载完整演示数据。

---

## 2. 平台操作流程

平台包含三个主要模块，通过顶部导航栏切换。

### 2.1 运营仪表盘（首页）

默认显示的首页，展示平台整体运营概况：

- **4 个 KPI 卡片**：总客户数 / 活跃设备 / 本月收入 / 逾期锁定
- **设备状态饼图**（chart.js 甜甜圈图）：活跃（绿色）/ 已锁定（红色）/ 永久解锁（琥珀色）
- **最近交易列表**：时间 / 客户 / 金额 / 天数

点击「运营仪表盘」随时返回首页。

### 2.2 客户管理

左侧为客户列表，右侧为客户详情。

#### 查看客户
- 左侧显示所有客户（状态标记：🟢活跃 / 🔴已锁定 / ⭐永久解锁）
- 点击任意客户查看详情

#### 新增客户
1. 点击左侧「+ 新增」
2. 填写姓名、电话、设备编号
3. 填写**设备密钥**（32 位 hex，设备出厂预设，可点「随机」生成）
4. 确认添加

#### 模拟支付
1. 选中客户，在详情面板「模拟支付」区选择金额
   - $5.00 → 30 天
   - $10.00 → 60 天
2. 点击「确认支付」
3. 弹窗显示 **9 位 OpenPAYGO Token** 和模拟短信内容
4. 客户在设备端输入 Token 即可解锁/续期

#### 设备控制
- **锁定设备**：客户设备立即停止供电
- **永久解锁**：生成 DISABLE_PAYG Token，设备永久解除 PAYGO 限制
- **删除客户**：仅限未绑定合同的客户

### 2.3 合同管理

点击导航栏「合同管理」进入。

#### 贷款产品配置
1. 点击左侧「贷款产品配置」
2. 查看 5 档贷款产品：

| 产品 | 系统规模 | 期限 | 年利率 | 首付 | 总价 |
|------|---------|------|--------|------|------|
| 6kW-12月基础 | 6kW | 12月 | 10% | 20% | $690 |
| 10kW-24月标准 | 10kW | 24月 | 12% | 20% | $1,150 |
| 15kW-24月标准 | 15kW | 24月 | 12% | 20% | $1,725 |
| 20kW-36月进阶 | 20kW | 36月 | 14% | 20% | $2,300 |
| 30kW-36月旗舰 | 30kW | 36月 | 14% | 20% | $3,450 |

#### 创建合同
1. 点击「+ 新合同」
2. 选择客户和贷款产品
3. 点击「确认创建」→ 合同进入「草稿」状态
4. 系统自动计算首付、贷款本金、月供

#### 审批合同
1. 点击「审批通过」
2. 合同状态变为「执行中」
3. 自动生成**等额本息还款计划表**，展示每期：应还日 / 月供 / 本金 / 利息 / 剩余本金 / 状态

#### 合同状态管理

```
draft → active → overdue → closed / recovered
```

| 操作 | 条件 | 说明 |
|------|------|------|
| 审批通过 | draft 状态 | 生成还款计划，进入 active |
| 标记逾期 | active 状态 | 进入 overdue |
| 恢复活跃 | overdue 状态 | 返回 active |
| 结清/回收 | active/overdue | 选「确定」结清，「取消」回收 |

---

## 3. 演示数据加载

```bash
cd paygo-platform
PYTHONPATH="." venv/bin/python scripts/seed_demo_data.py
```

加载后仪表盘显示：

| 指标 | 值 |
|------|-----|
| 总客户数 | 4 |
| 活跃设备 | 2（Sok Heng / Alice） |
| 本月收入 | $204.74（4 笔支付） |
| 逾期锁定 | 2（Bob / Sarun） |

演示客户：

| 客户 | 电话 | 设备 | 合同 | 状态 |
|------|------|------|------|------|
| Sok Heng | 0888888001 | DEV-KH-001 | 10kW-24月 | 🟢 活跃（2期已还） |
| Alice | 011222333 | DEV-KH-002 | 6kW-12月 | 🟢 活跃（1期已还） |
| Bob | 044555666 | DEV-KH-003 | 15kW-24月 | 🔴 逾期（1期已还） |
| Sarun | 077123456 | DEV-KH-004 | 无 | ⚪ 待签约 |

---

## 4. API 接口速查

所有接口需先登录获取 session cookie。

### 仪表盘

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats` | 仪表盘 KPI + 最近交易 |

### 客户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/customers` | 客户列表 |
| POST | `/api/customers` | 新增客户 |
| GET | `/api/customers/{id}` | 客户详情 |
| DELETE | `/api/customers/{id}` | 删除客户 |
| POST | `/api/customers/{id}/simulate-payment` | 模拟支付（含 Token 生成） |
| POST | `/api/customers/{id}/lock` | 锁定设备 |
| POST | `/api/customers/{id}/permanent-unlock` | 永久解锁 |

### 合同管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/loan-products` | 贷款产品列表 |
| POST | `/api/loan-products` | 新增贷款产品 |
| PUT | `/api/loan-products/{id}` | 编辑贷款产品 |
| DELETE | `/api/loan-products/{id}` | 禁用贷款产品 |
| GET | `/api/contracts` | 合同列表 |
| POST | `/api/contracts` | 创建合同（draft） |
| GET | `/api/contracts/{id}` | 合同详情（含还款计划） |
| PUT | `/api/contracts/{id}/approve` | 审批通过 → 生成还款计划 |
| PUT | `/api/contracts/{id}/status` | 变更状态 |

### 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/payment-rates` | 支付汇率配置 |

### curl 示例

```bash
# 登录
curl -c cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login

# 查看仪表盘
curl -b cookies.txt http://localhost:8000/api/dashboard/stats

# 创建合同
curl -b cookies.txt -X POST \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"Cxxxx","product_id":"LPxxxx"}' \
  http://localhost:8000/api/contracts

# 审批合同
curl -b cookies.txt -X PUT \
  http://localhost:8000/api/contracts/{cid}/approve
```

---

## 5. 环境要求与安装

- Python 3.10+
- PostgreSQL 15+
- Redis 8+

### 数据库初始化（首次）

```bash
psql -U postgres -c "CREATE USER paygo_user WITH PASSWORD 'PaygoDB2026!';"
psql -U postgres -c "CREATE DATABASE paygo_platform OWNER paygo_user;"
psql -U postgres -c "CREATE DATABASE paygo_platform_test OWNER paygo_user;"
psql -U postgres -d paygo_platform -c "GRANT ALL ON SCHEMA public TO paygo_user;"
psql -U postgres -d paygo_platform_test -c "GRANT ALL ON SCHEMA public TO paygo_user;"
```

### Homebrew 安装（macOS）

```bash
brew install postgresql@15 redis
brew services start postgresql@15
brew services start redis
```

---

## 6. 运行测试

```bash
source venv/bin/activate
pytest tests/ -v     # 140 个测试
```

测试使用独立数据库 `paygo_platform_test`，不影响开发数据。

---

## 7. 项目结构

```
paygo-platform/
├── app/
│   ├── main.py                  # FastAPI 入口（lifespan 管理 DB + Redis）
│   ├── settings.py              # 连接配置（环境变量覆盖）
│   ├── models.py                # SQLAlchemy ORM（8 张表）
│   ├── database.py              # async engine + session 工厂
│   ├── redis.py                 # Redis session/缓存/防重放
│   ├── store.py                 # async 数据访问层（含等额本息计算）
│   └── routers/
│       ├── auth.py              # 认证（Redis session）
│       ├── customers.py         # 客户 CRUD + 模拟支付 + 锁定/解锁
│       ├── contracts.py         # 合同 + 贷款产品 API
│       ├── dashboard.py         # 仪表盘 stats API
│       └── config.py            # 支付汇率配置
├── scripts/
│   └── seed_demo_data.py        # 演示数据初始化脚本
├── controller/
│   ├── controller.py            # 终端 UI（9位Token/密钥绑定/count）
│   └── state_manager.py         # 状态机 + PostgreSQL 持久化
├── static/
│   ├── style.css                # 全局样式（绿色主题 #059669）
│   └── logo.png
├── templates/
│   ├── base.html                # 布局框架（二层导航栏）
│   ├── login.html               # 登录页
│   └── dashboard.html           # 主界面 SPA（仪表盘/客户/合同）
└── tests/                       # 140 个测试
```

## 8. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform` | 数据库连接串 |
| `TEST_DATABASE_URL` | 同上，数据库 `paygo_platform_test` | 测试数据库 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `DB_POOL_SIZE` | `10` | 连接池常驻连接数 |
| `DB_MAX_OVERFLOW` | `20` | 连接池峰值溢出 |
| `CACHE_TTL_API` | `60` | API 缓存 TTL（秒） |
| `SESSION_TTL` | `1800` | Session TTL（30分钟） |
| `ANTIREPLAY_TTL` | `604800` | Token 防重放 TTL（7天） |

---

## 9. Token 编码格式（OpenPAYGO 标准）

- **标准**：[OpenPAYGO](https://github.com/EnAccess/OpenPAYGO-python) >=0.6.3
- **格式**：9 位纯数字
- **加密**：SipHash-2-4 哈希链
- **防重放**：count 递增机制
- **类型**：ADD_TIME（累加）/ SET_TIME（设置）/ DISABLE_PAYG（永久解锁）/ COUNTER_SYNC（同步）

---

## 10. 远程部署

### Docker Compose

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://paygo_user:${DB_PASSWORD}@db:5432/paygo_platform
      REDIS_URL: redis://redis:6379/0
    depends_on: [db, redis]
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: paygo_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: paygo_platform
    volumes: [pgdata:/var/lib/postgresql/data]
  redis:
    image: redis:8-alpine
volumes:
  pgdata:
```

```bash
DB_PASSWORD=<password> docker compose up -d
```

### 云托管（Render / Railway / Fly.io）

1. 推送代码到 GitHub
2. 创建 Web Service，Build: `pip install -r requirements.txt`
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 配置环境变量指向云 PostgreSQL + Redis
