# 柬埔寨太阳能PAYGO平台原型

## 项目概述
本项目是柬埔寨太阳能发电系统PAYGO（Pay-As-You-Go）平台的原型系统。通过与MFI（小额信贷机构）合作，客户可以分期付款购买太阳能系统，每次还款后系统生成激活Token延长设备使用期限。

## 业务背景
- 柬埔寨商业电价高达0.135-0.185美元/千瓦时
- 太阳能发电成本仅约0.03美元/千瓦时，成本优势超过75%
- 目标系统规模：6kW-30kW分布式太阳能系统
- 目标客户：别墅、商铺、中小型工厂、大型农场
- 合作MFI：LOLC Cambodia、PRASAC、ACLEDA等
- 支付方式：通过Bakong系统（柬埔寨国家银行数字支付平台）

## 当前原型范围

当前为**第二阶段原型（Phase 0 + Phase 1 已完成）**，累计 **165 个测试**，**10 张数据表**。

### Phase 0：安全基础升级 ✅ 已完成 2026-05-20
- 密码 bcrypt 哈希存储（替换明文比较）
- 设备密钥 Fernet 加密存储（`secret_key_encrypted` 列，启动时自动迁移明文→密文）
- API 限流中间件（Redis 滑动窗口，100次/min 通用，10次/min 登录）
- 请求日志中间件（方法/路径/状态码/耗时/IP）
- 登录失败锁定（5次失败锁定15分钟）
- 新增文件：`app/security.py`, `app/middleware.py`
- 新增环境变量：`ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `SECRET_KEY_MASTER_KEY`, `RATE_LIMIT_PER_MINUTE`, `LOGIN_RATE_LIMIT_PER_MINUTE`, `LOGIN_MAX_FAILURES`, `LOGIN_LOCKOUT_MINUTES`

### Phase 1：合同管理补完（原 M7 收尾） ✅ 已完成 2026-05-20
- 按期还款标记 → 自动生成 ADD_TIME Token → 创建 RepaymentRecord
- 逾期自动检测（check_overdue_schedules：到期未付 → 标记 overdue → 合同联动 → 设备锁定）
- 提前结清（生成 DISABLE_PAYG Token → 永久解锁 → 合同 closed）
- 还款进度可视化（合同详情页绿色进度条 + 期数快捷还款按钮）
- 新增表：`repayment_records`
- 新增字段：`tokens.contract_id`
- API：`POST /api/contracts/{cid}/pay`, `POST /api/contracts/check-overdue`, `POST /api/contracts/{cid}/settle`

### 已有功能（早期原型）
- PostgreSQL 15 + Redis 8 迁移
- 运营仪表盘首页（KPI 卡片 + 设备状态饼图 + 最近交易列表）
- 二层导航栏（运营仪表盘 / 客户管理 / 合同管理）
- Docker Compose 生产部署（4 服务编排）
- 客户 CRUD + 模拟支付 + Token 生成（OpenPAYGO SipHash-2-4）
- 合同 CRUD + 审批 + 等额本息还款计划自动生成
- 贷款产品 5 档配置（6kW~30kW）

## 原型迭代路线图

详细升级计划见根目录 `PAYGO平台升级迭代计划.md`。按业务闭环深度分 9 个阶段（Phase 0-8），每阶段完成后必须同步更新本文件和升级计划文件。

### Phase 0：安全基础升级 ✅ 已完成 2026-05-20（原 M5 安全升级提前执行）
- bcrypt 密码哈希、设备密钥 Fernet 加密存储、API 限流、请求日志、登录失败锁定
- 新增：app/security.py, app/middleware.py，157 tests

### Phase 1：合同管理补完 ✅ 已完成 2026-05-20（原 M7 收尾）
- 按期还款→Token 生成、逾期自动检测→设备锁定、提前结清→永久解锁、还款进度条
- 新增：repayment_records 表，165 tests

### Phase 2：Token 管理独立模块 ✅ 已完成 2026-05-20
- **导航 tab**：新增「Token 管理」（第 4 个 tab）
- **核心能力**：Token 列表（按客户/状态筛选+分页）、Token 统计卡片（总数/今日/本月/已作废）、Token 详情（含客户名/关联合同/审计字段）、手动补发（Counter+1 新 Token，原 Token → SUPERSEDED）、Token 作废（标记 SUPERSEDED + 操作人 + 原因）
- **新增文件**：`app/routers/tokens.py`, `tests/test_tokens_api.py`
- **Token 模型**：新增 status/superseded_by/voided_at/voided_by/void_reason/ip_address/user_agent（7 字段）
- 178 tests

### Phase 3：客户 360 视图与 MFI 管理 ✅ 已完成 2026-05-20
- **导航 tab**：增强「客户管理」（搜索筛选 + 360 聚合视图 + 标签管理）
- 客户扩展字段：地址/GPS/身份证/MFI 关联/标签（JSON）
- 客户 360 聚合视图：合同卡片（可点击跳转）+ Token 时间线（15条）+ MFI 名称
- 标签管理：添加/删除标签（VIP/高风险/投诉频繁/新客户）
- 搜索筛选：姓名/电话实时搜索（300ms debounce）
- MFI 机构管理：CRUD API（LOLC/PRASAC/ACLEDA）
- 新增模型：`Mfi`, 新增 6 个 Customer 字段
- 188 tests

### Phase 4：告警中心（原 M8 扩展）
- **导航 tab**：新增「告警中心」
- 详见升级计划 Phase 4

### Phase 5-8：仪表盘增强 → 设备地图 → 报表中心 → 系统设置
- 详见升级计划 Phase 5-8

### 原型阶段暂不做
- M2 Bakong 支付、M3 SMS 网关、M4 设备控制器（均需外部系统对接，仅模拟）
- AWS 云部署 / K8s / Kafka / EMQX（原型用 Docker Compose + BackgroundTasks + DB 模拟）

## 技术栈
- 后端框架：Python FastAPI
- 前端：Jinja2 模板 + 纯 CSS（绿色主题 #059669）
- 数据库：PostgreSQL 15（SQLAlchemy 2.0 async + asyncpg 驱动）
- 缓存：Redis 8（session 管理 + API 响应缓存 + Token 防重放）
- Token 生成：OpenPAYGO 标准 >=0.6.3（SipHash-2-4 哈希链，9 位纯数字，ADD_TIME / DISABLE_PAYG）
- 安全：bcrypt（密码哈希）+ Fernet（设备密钥对称加密）+ Redis 滑动窗口限流
- ORM：SQLAlchemy 2.0 async，**11 张表**（+mfis）
- 测试：pytest-asyncio，**188 个测试**，真实测试数据库隔离

## Superpowers 框架配置
- 强制使用TDD：所有功能必须先写测试再写实现
- 计划先行：每个开发阶段前必须编写实施计划
- 子代理开发：复杂任务使用子代理执行
- 双重审查：规格合规审查 + 代码质量审查
- 验证前完成：所有功能必须通过测试验证
- 频繁提交：每个小步骤完成后提交代码

## 项目目录结构
```
paygo-platform/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 主应用入口（lifespan 管理连接池 + 中间件注册 + 数据迁移）
│   ├── settings.py          # 数据库/Redis/安全/限流 配置（环境变量覆盖）
│   ├── models.py            # SQLAlchemy ORM 模型（10 张表）
│   ├── database.py          # async engine + session 工厂 + Depends 注入
│   ├── redis.py             # Redis 客户端 + session/缓存/防重放
│   ├── store.py             # async 数据访问层（CRUD + 还款标记 + 逾期检测 + 结清）
│   ├── security.py          # bcrypt 密码哈希 + Fernet 密钥加解密（Phase 0 新增）
│   ├── middleware.py         # 限流中间件 + 请求日志中间件（Phase 0 新增）
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # 登录/登出（bcrypt 验证 + 登录锁定）
│       ├── customers.py     # 客户CRUD + 模拟支付 + 锁定/永久解锁 API（async + 缓存）
│       ├── config.py        # 支付汇率配置 API（async + 缓存）
│       ├── contracts.py     # 合同/贷款产品 CRUD + 还款/逾期检测/结清 API（Phase 1 新增）
│       └── dashboard.py     # 仪表盘统计 API
├── controller/
│   ├── controller.py        # 终端 UI（9位Token输入/密钥绑定/count显示）
│   └── state_manager.py     # 状态机 + PostgreSQL 持久化
├── static/
│   ├── __init__.py
│   ├── style.css            # 全局样式（绿色主题 #059669）
│   └── logo.png             # 平台 Logo
├── templates/
│   ├── base.html            # 布局框架
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面（左列表+右详情）
├── tests/
│   ├── conftest.py          # 全局 fixture + openpaygo 补丁 + Fernet/Redis 初始化 + 状态清理
│   ├── test_models.py       # ORM 模型 (8 tests)
│   ├── test_database.py     # 数据库连接池 (3 tests)
│   ├── test_redis_client.py # Redis 客户端 (10 tests)
│   ├── test_store.py        # 数据访问层 (23 tests, 含密钥加密+还款流)
│   ├── test_auth.py         # 认证 (8 tests, 含登录锁定)
│   ├── test_customers_api.py# 客户API (22 tests)
│   ├── test_state_manager.py# 状态机 (19 tests)
│   ├── test_config_api.py   # 支付汇率 (2 tests)
│   ├── test_controller_integration.py  # 控制器集成 (4 tests)
│   ├── test_integration.py  # 端到端集成 (6 tests)
│   ├── test_upgrade.py      # 五场景 MFI 演示 (9 tests)
│   ├── test_contract_models.py  # 合同+还款记录模型 (7 tests, Phase 1)
│   ├── test_contract_store.py   # 合同 store 层 (21 tests, Phase 1)
│   ├── test_contracts_api.py    # 合同 API (9 tests, Phase 1)
│   ├── test_dashboard_api.py    # 仪表盘 API (2 tests)
│   ├── test_security.py     # 安全模块 (10 tests, Phase 0)
│   └── test_middleware.py   # 限流+日志中间件 (2 tests, Phase 0)
├── docs/
│   ├── debug-controller.md
│   ├── controller-redeploy.md
│   └── superpowers/
│       ├── specs/           # 设计文档
│       └── plans/           # 实施计划
├── requirements.txt
├── README.md
├── CLAUDE.md                # 本文件
├── AGENTS.md                # 代理角色定义
├── cookies.txt
└── .superpowers/            # Superpowers 框架配置
```

## 开发规范
- 强制TDD：每个功能必须先有失败的测试，再写实现代码
- 计划先行：每个 Phase 前编写实施计划到 `docs/superpowers/plans/YYYY-MM-DD-<name>.md`
- 子代理开发：复杂任务使用 Subagent-Driven Development 执行
- 双重审查：规格合规审查 + 代码质量审查
- 验证前完成：所有功能必须通过测试验证（`pytest tests/ -v`）
- 频繁提交：每个小步骤完成后提交代码
- 代码注释使用中文（部分英文标签）
- 所有API接口使用 `/api/` 前缀
- 认证方式：单一管理员账号 + bcrypt 密码验证 + Redis session cookie + 登录锁定
- **每个 Phase 完成后必须同步更新两个文件**：
  1. `PAYGO平台升级迭代计划.md` — 标注 Phase 完成状态 ✅ + 填写实际结果（测试数、文件列表、关键差异）
  2. `CLAUDE.md` — 更新原型范围、测试数、表数、迭代路线图状态、目录结构

## 启动命令
```bash
# 前置依赖：确保 PostgreSQL 15 和 Redis 8 已运行
# PostgreSQL 数据库：paygo_platform，用户：paygo_user
# Redis：localhost:6379

# 开发环境启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行所有测试（165 个）
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_store.py -v

# 按模块运行
pytest tests/test_models.py -v          # ORM 模型 (8 tests)
pytest tests/test_database.py -v        # 连接池 (3 tests)
pytest tests/test_redis_client.py -v    # Redis (10 tests)
pytest tests/test_security.py -v        # 安全模块 (10 tests, Phase 0)
pytest tests/test_middleware.py -v      # 中间件 (2 tests, Phase 0)
pytest tests/test_store.py -v           # 数据访问层 (23 tests)
pytest tests/test_auth.py -v            # 认证 (8 tests)
pytest tests/test_customers_api.py -v   # 客户API (22 tests)
pytest tests/test_contract_models.py -v # 合同模型 (7 tests, Phase 1)
pytest tests/test_contract_store.py -v  # 合同 store (21 tests, Phase 1)
pytest tests/test_contracts_api.py -v   # 合同 API (9 tests, Phase 1)
pytest tests/test_dashboard_api.py -v   # 仪表盘 API (2 tests)
pytest tests/test_state_manager.py -v   # 状态机 (19 tests)
pytest tests/test_config_api.py -v      # 支付汇率 (2 tests)
pytest tests/test_integration.py -v     # 集成 (6 tests)
pytest tests/test_upgrade.py -v         # 五场景 (9 tests)

# 控制器终端（需先激活 venv）
source venv/bin/activate && cd controller && python controller.py

# 访问API文档
http://localhost:8000/docs

# 访问运营后台
http://localhost:8000/dashboard
```

### 环境变量

所有连接配置支持环境变量覆盖：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform` | 数据库连接串 |
| `TEST_DATABASE_URL` | 同上但数据库为 `paygo_platform_test` | 测试数据库 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `DB_POOL_SIZE` | `10` | 连接池常驻连接数 |
| `DB_MAX_OVERFLOW` | `20` | 连接池峰值溢出数 |
| `CACHE_TTL_API` | `60` | API 缓存 TTL（秒） |
| `SESSION_TTL` | `1800` | 登录 Session TTL（30分钟） |
| `ANTIREPLAY_TTL` | `604800` | Token 防重放 TTL（7天） |
| `ADMIN_USERNAME` | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD_HASH` | (空=首次启动使用默认密码) | bcrypt 密码哈希 |
| `SECRET_KEY_MASTER_KEY` | (空=自动生成临时密钥) | Fernet 加密主密钥（base64） |
| `RATE_LIMIT_PER_MINUTE` | `100` | API 限流（次/分钟/IP） |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | 登录接口限流（次/分钟/IP） |
| `LOGIN_MAX_FAILURES` | `5` | 登录失败锁定阈值 |
| `LOGIN_LOCKOUT_MINUTES` | `15` | 登录锁定时间（分钟） |
