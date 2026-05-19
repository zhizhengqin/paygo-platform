# PostgreSQL + Redis 迁移设计

**日期:** 2026-05-19
**状态:** 已确认

## 目标

将 paygo-platform 从内存 dict 存储迁移至 PostgreSQL 15 持久化，引入 Redis 缓存层，建立完整 ORM 模型。

## 技术选型

- **ORM:** SQLAlchemy 2.0 async + asyncpg 驱动
- **缓存:** Redis (redis-py async)
- **数据库:** PostgreSQL 15，数据库 `paygo_platform`，用户 `paygo_user`
- **Session:** 从 cookie 明文改为 Redis-backed session

## 整体架构

```
FastAPI (async handlers)
  └── app/store.py (async 数据访问层)
        ├── app/database.py (asyncpg 连接池)
        ├── app/models.py  (SQLAlchemy ORM)
        └── app/redis.py   (Redis 客户端)
```

## 新增文件

| 文件 | 职责 |
|------|------|
| `app/models.py` | 5 个 ORM 模型定义 |
| `app/database.py` | async engine + session 工厂 + Depends 注入 |
| `app/redis.py` | Redis 客户端初始化 + session/缓存/防重放工具 |
| `app/store.py` | 原 db.py 的 async 重写，所有数据访问 |
| `app/settings.py` | DB 连接串、Redis 连接串等配置 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 启动/关闭事件管理连接池生命周期 |
| `app/routers/auth.py` | Redis session 替代 cookie 明文 |
| `app/routers/customers.py` | handler 改为 async，注入 DB session |
| `app/routers/config.py` | handler 改为 async |
| `controller/state_manager.py` | JSON 文件 → PostgreSQL device_states 表 |

## 删除文件

- `app/db.py` — 功能完全迁移到 `store.py` + `models.py`

## 数据模型 (5 张表)

### customers
| 列 | 类型 | 约束 |
|----|------|------|
| id | VARCHAR(8) | PK |
| name | VARCHAR(100) | NOT NULL |
| phone | VARCHAR(20) | NOT NULL |
| device_id | VARCHAR(50) | NOT NULL |
| secret_key | VARCHAR(64) | NOT NULL |
| count | INTEGER | DEFAULT 0 |
| status | VARCHAR(20) | DEFAULT 'locked' |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| locked_at | TIMESTAMPTZ | nullable |

### tokens
| 列 | 类型 | 约束 |
|----|------|------|
| id | VARCHAR(8) | PK |
| customer_id | VARCHAR(8) | FK → customers.id |
| token | VARCHAR(9) | NOT NULL |
| days | INTEGER | NOT NULL |
| count | INTEGER | NOT NULL |
| generated_at | TIMESTAMPTZ | DEFAULT now() |
| expires_at | TIMESTAMPTZ | NOT NULL |

### sms_records
| 列 | 类型 | 约束 |
|----|------|------|
| id | VARCHAR(8) | PK |
| customer_id | VARCHAR(8) | FK → customers.id |
| to_phone | VARCHAR(20) | NOT NULL |
| message | TEXT | NOT NULL |
| sent_at | TIMESTAMPTZ | DEFAULT now() |

### payment_rates
| 列 | 类型 | 约束 |
|----|------|------|
| id | SERIAL | PK |
| amount | NUMERIC(10,2) | NOT NULL UNIQUE |
| days | INTEGER | NOT NULL |

### device_states
| 列 | 类型 | 约束 |
|----|------|------|
| id | SERIAL | PK |
| device_id | VARCHAR(50) | NOT NULL UNIQUE |
| secret_key | VARCHAR(64) | nullable |
| count | INTEGER | DEFAULT 0 |
| used_counts | JSONB | DEFAULT '[]' |
| remaining_days | INTEGER | DEFAULT 0 |
| last_update | DATE | nullable |
| status | VARCHAR(20) | DEFAULT 'unbound' |

### 索引
- `customers.phone` — 按手机号查询
- `tokens.customer_id` — 按客户查 Token 历史
- `tokens.expires_at` — 清理过期 Token
- `device_states.device_id` — 设备状态快速查询

## Redis 缓存设计

| 层 | Key 格式 | TTL | 用途 |
|----|----------|-----|------|
| Session | `session:{uuid}` | 30 min | 替代 cookie 明文，自动续期 |
| API 响应 | `cache:customers:list` 等 | 60s | 高频读接口缓存 |
| 防重放 | `antireplay:{device_id}:{count}` | 7 days | 防止 Token 重复使用 |

### 缓存策略
- **Cache-Aside**: 读 miss → 查 DB 回填；写 → 删缓存
- 缓存范围: `GET /api/customers`, `GET /api/customers/:id`, `GET /api/tokens`, `GET /api/config/payment-rates`
- Redis 不可用时降级直查 DB，不阻塞业务

## 连接管理

- PostgreSQL 连接池: pool_size=10, max_overflow=20, pool_pre_ping=True
- FastAPI startup: 创建表; shutdown: 释放连接池 + 关闭 Redis
- 每请求独立 AsyncSession，通过 FastAPI Depends 注入

## 错误处理

- DB 连接失败 → 503 + 日志
- Redis 不可用 → 降级直查 DB
- 唯一约束冲突 → 409
- 外键约束 → 422

## 测试策略

- 使用独立测试数据库 `paygo_platform_test`
- pytest-asyncio 支持 async 测试
- conftest.py 管理测试 DB session + 表创建/清理
- 隔离: 每次测试创建独立 session，rollback 回滚
