# 柬埔寨即付即用平台原型

Python FastAPI + Jinja2 + PostgreSQL 15 + Redis 8。200 tests，16 张表，8 个导航 Tab。

## 常用命令

```bash
# 开发启动（需 PostgreSQL + Redis 已运行）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 加载演示数据（4 客户 + 3 合同 + GPS + MFI）
PYTHONPATH="." python scripts/seed_demo_data.py

# 运行全部测试
pytest tests/ -v

# 运行单个模块
pytest tests/test_store.py -v

# Docker Compose 部署
docker compose up -d --build
```

访问：http://localhost:8000/dashboard · 登录：`admin` / `admin123` · API 文档：http://localhost:8000/docs

## 架构摘要

```
router/  →  store.py  →  models.py  →  PostgreSQL 15
   ↓           ↓
  Jinja2     Redis 8 (session / 缓存 / 限流 / 防重放)
```

- **routers/** — 每个模块一个文件，通过 `_check_auth` 认证（JWT Bearer → JWT Cookie → Session Cookie 三通道）
- **store.py** — 所有数据访问层，async SQLAlchemy 2.0。CRUD + 等额本息计算 + 还款标记 + 逾期检测 + 告警 + 360视图 + 标签 + Token 管理
- **models.py** — 16 张表，首次启动 `lifespan` 自动 `create_all` + 逐个 ALTER TABLE 迁移
- **security.py** — bcrypt 密码哈希 + Fernet 设备密钥加密（密钥持久化到 `.env`）+ JWT HS256
- **middleware.py** — RateLimiterMiddleware（Redis 滑动窗口 100/min）+ RequestLoggingMiddleware
- **templates/** — `base.html` 布局 + `dashboard.html` SPA 全部 8 模块（含浮动控制器面板）

路由→文件映射：`/api/customers` → `routers/customers.py`，`/api/tokens` → `routers/tokens.py`，以此类推。

## 开发规范

### Superpowers 框架（强制执行）

所有开发升级迭代**必须**通过 Superpowers 技能体系，不允许跳过：

| 场景 | 必须使用的技能 |
|:---|:---|
| 新功能 / 复杂改动 | `brainstorming` → `writing-plans` → `subagent-driven-development` |
| Bug 修复 | `systematic-debugging`（先定位根因再修改） |
| 功能完成 / 合并前 | `verification-before-completion` + `requesting-code-review` |
| 分支收尾 | `finishing-a-development-branch` |

**复杂改动的判定标准**（满足任一即为复杂）：
- 涉及 3 个以上文件
- 需要新增数据模型或 API 端点
- 涉及 UI 布局或交互变更
- 不确定实现方案

### UI 开发（强制 Playwright 验证）

- **界面相关改动必须通过 Playwright 截图验证**，不允许仅凭代码逻辑判断 UI 正确性
- 移动端适配需在 375×812 视口下验证
- 修改完成后提供 Playwright 验证结果（截图 + 关键数据），确认无误再回复
- 常用验证项：z-index 层级、点击可达性、元素可见性、菜单展开/收起

### 日常规范

- **强制 TDD**：先写失败测试再写实现。测试数据库 `paygo_platform_test` 独立隔离
- **计划先行**：每个 Phase 前写实施计划到 `docs/superpowers/plans/`
- **子代理执行**：用 Subagent-Driven Development 按 task 逐个实现+审查
- **API 前缀**：所有接口 `/api/` 前缀，健康检查 `/api/v1/health`
- **认证**：`_check_auth()` 三通道（Bearer > JWT Cookie > Session），复用于所有 router
- **Fernet 密钥一致性**：`SECRET_KEY_MASTER_KEY` 存于 `.env`，首次启动自动生成并持久化。种子数据和服务器必须使用同一密钥

### 语言约定

- **思考过程**：中文
- **回复用户**：中文
- **代码注释**：中文
- **Git 提交信息**：中文简述

## 关键环境变量

| 变量 | 说明 |
|:---|:---|
| `DATABASE_URL` | PostgreSQL 连接串（含 `+asyncpg` 驱动） |
| `REDIS_URL` | Redis 连接串 |
| `SECRET_KEY_MASTER_KEY` | Fernet 设备密钥加密主密钥，**必须跨进程一致** |
| `JWT_SECRET_KEY` | JWT HS256 签名密钥 |
| `ADMIN_PASSWORD_HASH` | bcrypt 密码哈希（空则默认密码 `admin123`） |
| `RATE_LIMIT_PER_MINUTE` | API 限流阈值，默认 100 |

全部变量见 `app/settings.py`。

## 测试策略

- 所有测试独立于开发数据库，使用 `paygo_platform_test`
- `conftest.py` 管理 session 级 Redis/Fernet 初始化 + 模块间 Redis 状态清理
- 按模块对应：`test_store.py` → `app/store.py`，`test_contracts_api.py` → `routers/contracts.py`
- 新功能 = 新测试文件（store 测试用函数级 test DB，API 测试用 httpx ASGITransport）

## 约束与边界

**原型模拟（不可真实对接）**：
- 支付：页面按钮模拟，不接 Bakong API · SMS：弹窗展示，不接 SMPP 网关
- 设备通信：DB 模拟状态，不接 MQTT/EMQX · MFI 同步：手动录入，不接 CBS

**安全底线（即使原型也必须实现）**：bcrypt 密码、Fernet 密钥加密、Redis 限流、登录锁定。

**Flutter App / AWS K8s / Terraform 不在此原型范围。**

## 相关文档

| 文档 | 位置 |
|:---|:---|
| 升级迭代计划（10 Phase 全记录） | `docs/项目文档/平台升级迭代计划.md` |
| 演示流程手册（4 角色 × 25 步 × 截图） | `docs/项目文档/平台演示流程手册.md` |
| 需求规格说明书 PRD | `docs/项目文档/平台需求规格说明书_PRD_V1.0.md` |
| 系统架构设计说明书 | `docs/项目文档/系统架构设计说明书_V1.0.md` |
| 云端部署指导手册 | `docs/项目文档/云部署指导手册.md` |
| 运营操作手册 + API 速查 | `README.md` |
