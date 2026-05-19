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

当前为**第二阶段原型**，已完成 PostgreSQL + Redis 迁移。以下功能暂不在范围内：
- 多管理员 / 角色权限
- 在线支付集成（Bakong）
- 真实短信网关对接
- remaining_days 自动递减逻辑
- 设备端 Starting Code / DISABLE_PAYG 逻辑
- 密码加密

后续迭代规划：
- 接入 Bakong 支付回调
- 接入 SMS 网关发送 Token
- 容器化部署（Docker + Docker Compose）

## 技术栈
- 后端框架：Python FastAPI
- 前端：Jinja2 模板 + 纯 CSS（绿色主题 #059669）
- 数据库：PostgreSQL 15（SQLAlchemy 2.0 async + asyncpg 驱动）
- 缓存：Redis 7（session 管理 + API 响应缓存 + Token 防重放）
- Token 生成：OpenPAYGO 标准 v0.6.3（SipHash-2-4 哈希链，9 位纯数字，ADD_TIME / DISABLE_PAYG）
- ORM：SQLAlchemy 2.0 async，5 张表（customers, tokens, sms_records, payment_rates, device_states）
- 测试：pytest-asyncio，105 个测试，真实测试数据库隔离

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
│   ├── main.py              # FastAPI 主应用入口（lifespan 管理连接池）
│   ├── settings.py          # 数据库/Redis 连接配置（环境变量覆盖）
│   ├── models.py            # SQLAlchemy ORM 模型（5 张表）
│   ├── database.py          # async engine + session 工厂 + Depends 注入
│   ├── redis.py             # Redis 客户端 + session/缓存/防重放
│   ├── store.py             # async 数据访问层（替代旧 db.py）
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # 登录/登出（Redis session）
│       ├── customers.py     # 客户CRUD + 模拟支付 + 锁定/永久解锁 API（async + 缓存）
│       └── config.py        # 支付汇率配置 API（async + 缓存）
├── controller/
│   ├── controller.py        # 终端 UI（9位Token输入/密钥绑定/count显示）
│   └── state_manager.py     # 状态机 + PostgreSQL 持久化
├── static/
│   └── style.css            # 全局样式（绿色主题 #059669）
├── templates/
│   ├── base.html            # 布局框架
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面（左列表+右详情）
├── tests/
│   ├── conftest.py          # 全局 fixture + openpaygo 兼容补丁 + asyncio 配置
│   ├── test_models.py       # ORM 模型 (8 tests)
│   ├── test_database.py     # 数据库连接池 (3 tests)
│   ├── test_redis_client.py # Redis 客户端 (10 tests)
│   ├── test_store.py        # 数据访问层 (18 tests)
│   ├── test_auth.py         # 认证 (6 tests)
│   ├── test_customers_api.py# 客户API (20 tests)
│   ├── test_state_manager.py# 状态机 (19 tests)
│   ├── test_config_api.py   # 支付汇率 (2 tests)
│   ├── test_controller_integration.py  # 控制器集成 (4 tests)
│   ├── test_integration.py  # 端到端集成 (6 tests)
│   └── test_upgrade.py      # 五场景 MFI 演示 (9 tests)
├── docs/
│   └── superpowers/
│       ├── specs/           # 设计文档
│       └── plans/           # 实施计划
├── requirements.txt
├── README.md
├── CLAUDE.md                # 本文件
└── AGENTS.md                # 代理角色定义
```

## 开发规范
- 强制TDD：每个功能必须先有失败的测试，再写实现代码
- 代码注释使用中文
- 所有API接口使用 `/api/` 前缀
- 认证方式：单一管理员账号 + session cookie
- 每次变更后运行全部测试验证
- 每个功能完成后编写简短的中文提交信息

## 启动命令
```bash
# 前置依赖：确保 PostgreSQL 15 和 Redis 7 已运行
# PostgreSQL 数据库：paygo_platform，用户：paygo_user
# Redis：localhost:6379

# 开发环境启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行所有测试（105 个）
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_store.py -v

# 按模块运行
pytest tests/test_models.py -v          # ORM 模型 (8 tests)
pytest tests/test_database.py -v        # 连接池 (3 tests)
pytest tests/test_redis_client.py -v    # Redis (10 tests)
pytest tests/test_store.py -v           # 数据访问层 (18 tests)
pytest tests/test_auth.py -v            # 认证 (6 tests)
pytest tests/test_customers_api.py -v   # 客户API (20 tests)
pytest tests/test_state_manager.py -v   # 状态机 (19 tests)
pytest tests/test_config_api.py -v      # 支付汇率 (2 tests)
pytest tests/test_integration.py -v     # 集成 (6 tests)
pytest tests/test_upgrade.py -v         # 五场景 (9 tests)

# 控制器终端
cd controller && python controller.py

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
