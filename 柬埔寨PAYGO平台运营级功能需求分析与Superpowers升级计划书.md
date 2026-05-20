# 柬埔寨太阳能PAYGO平台运营级功能需求分析与Superpowers升级计划书

**文档版本**: V2.0  
**编制日期**: 2026年5月19日  
**编制单位**: 新华智科技（柬埔寨）有限公司 / 广西新豪智云技术股份有限公司  
**关联项目**: paygo-platform (https://github.com/zhizhengqin/paygo-platform)  
**开发框架**: Superpowers (https://github.com/obra/superpowers) + Claude Code (VS Code)  

---

## 目录

- [第一章 执行摘要与升级背景](#第一章-执行摘要与升级背景)
- [第二章 当前原型状态评估与差距分析](#第二章-当前原型状态评估与差距分析)
- [第三章 运营级功能需求总览](#第三章-运营级功能需求总览)
- [第四章 核心功能模块详细需求](#第四章-核心功能模块详细需求)
- [第五章 数据持久化与数据库架构升级](#第五章-数据持久化与数据库架构升级)
- [第六章 Bakong支付系统集成方案](#第六章-bakong支付系统集成方案)
- [第七章 SMS网关集成方案](#第七章-sms网关集成方案)
- [第八章 设备控制器模拟与OpenPAYGO完整实现](#第八章-设备控制器模拟与openpaygo完整实现)
- [第九章 运营后台与数据可视化](#第九章-运营后台与数据可视化)
- [第十章 安全架构升级](#第十章-安全架构升级)
- [第十一章 迭代路线图与里程碑规划](#第十一章-迭代路线图与里程碑规划)
- [第十二章 Superpowers框架升级手册](#第十二章-superpowers框架升级手册)
- [第十三章 各功能模块Claude Code提示词汇总](#第十三章-各功能模块claude-code提示词汇总)
- [附录A 数据库完整Schema设计](#附录a-数据库完整schema设计)
- [附录B Bakong API对接规范](#附录b-bakong-api对接规范)
- [附录C SMS网关接口规范](#附录c-sms网关接口规范)
- [附录D 测试策略与用例清单](#附录d-测试策略与用例清单)
- [附录E 参考资料与开源组件](#附录e-参考资料与开源组件)

---

## 第一章 执行摘要与升级背景

### 1.1 项目背景

本项目是柬埔寨太阳能发电系统PAYGO（Pay-As-You-Go）平台的运营级升级计划。基于第一阶段原型（paygo-platform开源项目），通过与MFI（小额信贷机构）合作，客户可分期付款购买6kW-30kW分布式太阳能系统，每次还款后系统生成OpenPAYGO Token延长设备使用期限。

### 1.2 升级目标

本计划书的核心目标是**将当前原型系统升级为可投入实际运营的PAYGO平台**，对标行业领先平台（Angaza、PaygOps）的功能水准，实现以下关键能力：

| 维度 | 当前状态（原型） | 目标状态（运营级） |
|------|-----------------|-------------------|
| 数据存储 | 内存dict（重启丢失） | PostgreSQL持久化 + Redis缓存 |
| 支付集成 | 模拟支付 | Bakong真实支付 + KHQR扫码 |
| 通知通道 | 模拟SMS | 真实SMS网关（SMPP协议） |
| 设备控制 | 基础Token生成 | 完整OpenPAYGO v2.1 + 控制器模拟器 |
| 客户管理 | 基础CRUD | 360度客户视图 + 信用评分 |
| 合同管理 | 简单记录 | 完整贷款生命周期 + 还款计划引擎 |
| 逾期管理 | 手动操作 | 自动分级预警 + 自动锁定/降额 |
| 运营报表 | 无 | 实时仪表盘 + GOGLA标准KPI |
| 权限控制 | 单管理员 | RBAC多角色 + MFI隔离 |
| 安全合规 | 密码明文 | AES-256加密 + 审计日志 + 合规 |

### 1.3 参考平台功能对标

本计划书深入分析了两大行业领先平台的功能特性：

**Angaza Platform**（200+分销商，800万+产品）核心功能：
- 客户数字化管理（Customer Account Handling）
- 灵活支付管理（Payment Management）
- 远程设备控制（Remote Device Control）
- 实时数据分析（Real-Time Data Reporting）
- 库存与团队管理（Inventory & Workforce）
- 自动化计费与提醒（Automated Billing & SMS）
- 多渠道支付集成（Mobile Money, Cash, Bank Transfer）

**PaygOps by Solaris Offgrid**（35+国家，40+制造商集成）核心功能：
- 完整租赁管理（Lease Management）
- 售后服务工单（After-Sales Ticketing）
- 呼叫中心管理（Call Centre Management）
- 自定义仪表盘（Customised Dashboards）
- 移动App现场作业（Mobile App for Agents）
- GOGLA KPI标准集成（Impact Measurement）
- 应收账款融资（Receivables Finance Platform）
- 表面测绘（Surface Mapping for Agriculture）

### 1.4 Superpowers框架说明

本项目采用Superpowers agentic开发框架进行迭代升级。Superpowers是一套完整的软件开发方法论，提供可组合的技能（skills）和严格的开发纪律，确保代码质量。核心技能包括：

| 技能 | 用途 |
|------|------|
| `test-driven-development` | 强制TDD：先写测试再写实现 |
| `writing-plans` | 编写详细的实施计划文档 |
| `subagent-driven-development` | 子代理分工执行复杂任务 |
| `executing-plans` | 按计划逐步执行 |
| `verification-before-completion` | 完成前验证所有功能 |
| `using-git-worktrees` | Git工作树管理并行开发 |
| `systematic-debugging` | 系统化调试 |

---

## 第二章 当前原型状态评估与差距分析

### 2.1 原型现有能力

当前原型基于Python FastAPI + Jinja2模板 + 纯CSS（绿色主题#059669），使用OpenPAYGO标准v0.6.3（SipHash-2-4哈希链，9位纯数字Token）。核心模块包括：

```
paygo-platform/
├── app/
│   ├── main.py              # FastAPI主应用入口
│   ├── db.py                # 内存数据库（customers + tokens + SMS + 汇率）
│   └── routers/
│       ├── auth.py          # 登录/登出（单管理员）
│       ├── customers.py     # 客户CRUD + 模拟支付 + 锁定/永久解锁 API
│       └── config.py        # 支付汇率配置 API
├── controller/
│   ├── controller.py        # 终端UI（9位Token输入/密钥绑定/count显示）
│   └── state_manager.py     # 状态机 + 持久化（secret_key/count/used_counts）
├── static/style.css         # 全局样式（绿色主题）
├── templates/               # Jinja2模板（base/login/dashboard）
└── tests/                   # 79个测试（db/auth/customers/state_manager/config/integration/upgrade）
```

### 2.2 详细差距分析

#### 差距1：数据持久化（严重）

| 项目 | 详情 |
|------|------|
| **当前状态** | 使用内存dict存储所有数据，应用重启后全部丢失 |
| **影响** | 无法用于任何生产环境，客户数据、设备密钥、交易记录均不持久 |
| **解决方向** | 迁移至PostgreSQL，使用SQLAlchemy ORM，保留现有API接口不变 |
| **优先级** | **P0 - 阻塞所有其他功能** |

#### 差距2：在线支付集成（严重）

| 项目 | 详情 |
|------|------|
| **当前状态** | 仅支持模拟支付（点击按钮即视为"已支付"） |
| **影响** | 无法接收真实客户付款，无法自动触发Token发放 |
| **解决方向** | 深度集成Bakong支付系统（柬埔寨国家银行数字支付平台），支持KH/USD双币种，实现Webhook回调自动处理 |
| **优先级** | **P0 - 核心业务阻塞** |

#### 差距3：SMS网关集成（严重）

| 项目 | 详情 |
|------|------|
| **当前状态** | SMS发送为模拟（仅记录到内存） |
| **影响** | 客户无法真实收到Token激活码，还款提醒无法触达 |
| **解决方向** | 集成本地SMS网关（Cellcard/ Smart企业短信网关），支持SMPP协议，实现Token自动发送、还款提醒、逾期通知 |
| **优先级** | **P0 - 核心业务阻塞** |

#### 差距4：remaining_days自动递减（高）

| 项目 | 详情 |
|------|------|
| **当前状态** | 设备剩余天数不会自动减少，需要手动修改 |
| **影响** | 设备锁定/解锁逻辑无法正常运作，逾期管理失效 |
| **解决方向** | 实现Celery定时任务，每日零点自动递减所有激活设备的remaining_days |
| **优先级** | **P1 - 核心功能缺失** |

#### 差距5：设备端Starting Code/DISABLE_PAYG逻辑（高）

| 项目 | 详情 |
|------|------|
| **当前状态** | 缺少设备首次激活的Starting Code生成逻辑，缺少贷款结清后的DISABLE_PAYG永久解锁逻辑 |
| **影响** | 新设备安装后无法首次激活，客户还清贷款后无法永久解锁设备 |
| **解决方向** | 完整实现OpenPAYGO Token所有类型（ADD_TIME, SET_TIME, DISABLE_PAYG, COUNTER_SYNC），控制器模拟器支持全部Token类型验证 |
| **优先级** | **P1 - 核心功能缺失** |

#### 差距6：密码加密（高）

| 项目 | 详情 |
|------|------|
| **当前状态** | 管理员密码明文存储 |
| **影响** | 严重安全隐患，不符合任何安全合规要求 |
| **解决方向** | 使用bcrypt进行密码哈希，支持密码强度校验 |
| **优先级** | **P1 - 安全合规** |

#### 差距7：多管理员与角色权限（中）

| 项目 | 详情 |
|------|------|
| **当前状态** | 仅支持单一管理员账号 |
| **影响** | 无法支持多MFI、多角色协作（运营人员、财务人员、技术人员、客服） |
| **解决方向** | 实现RBAC权限模型，支持角色：超级管理员、MFI管理员、运营专员、财务专员、客服专员、技术员 |
| **优先级** | **P2 - 运营支撑** |

---

## 第三章 运营级功能需求总览

### 3.1 功能模块全景图

基于差距分析和行业对标，本次升级共包含**8大核心模块**、**32个子功能**，按优先级分为三个阶段：

```
┌─────────────────────────────────────────────────────────────┐
│                 柬埔寨PAYGO平台运营级功能全景                    │
├─────────────────────────────────────────────────────────────┤
│  Phase 1（核心运营能力 - 1-2个月）                              │
│  ├── M1: 数据库持久化与架构升级（PostgreSQL + Redis）            │
│  ├── M2: Bakong支付系统集成（支付/Webhook/对账）                │
│  ├── M3: SMS网关集成（Token发送/提醒/通知）                     │
│  ├── M4: OpenPAYGO完整实现（全Token类型/自动递减/控制器模拟）    │
│  └── M5: 安全架构升级（密码加密/JWT/HTTPS）                     │
├─────────────────────────────────────────────────────────────┤
│  Phase 2（运营管理能力 - 2-3个月）                              │
│  ├── M6: 客户360视图与MFI管理                                   │
│  ├── M7: 合同与还款计划引擎                                     │
│  ├── M8: 逾期预警与自动锁定系统                                 │
│  ├── M9: 运营仪表盘与报表系统                                   │
│  └── M10: RBAC权限与多租户隔离                                  │
├─────────────────────────────────────────────────────────────┤
│  Phase 3（规模化与优化 - 2-3个月）                              │
│  ├── M11: 设备遥测与实时监控                                    │
│  ├── M12: 售后服务工单系统                                      │
│  ├── M13: 移动端现场作业App                                     │
│  ├── M14: 应收账款融资接口                                      │
│  └── M15: 性能优化与高可用部署                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 功能优先级矩阵

| 模块 | 功能 | 业务价值 | 技术复杂度 | 优先级 | 阶段 |
|------|------|---------|-----------|--------|------|
| M1 | PostgreSQL迁移 | 极高（阻塞项） | 中 | P0 | Phase 1 |
| M2 | Bakong支付集成 | 极高（核心业务） | 高 | P0 | Phase 1 |
| M3 | SMS网关集成 | 极高（核心业务） | 中 | P0 | Phase 1 |
| M4 | OpenPAYGO完整实现 | 极高（核心技术） | 高 | P0 | Phase 1 |
| M5 | 安全架构升级 | 高（合规要求） | 中 | P1 | Phase 1 |
| M6 | 客户360视图 | 高（运营基础） | 中 | P1 | Phase 2 |
| M7 | 合同与还款引擎 | 高（运营基础） | 高 | P1 | Phase 2 |
| M8 | 逾期预警系统 | 高（风险控制） | 中 | P1 | Phase 2 |
| M9 | 运营仪表盘 | 中（决策支持） | 中 | P2 | Phase 2 |
| M10 | RBAC多租户 | 中（协作支撑） | 中 | P2 | Phase 2 |
| M11 | 设备遥测监控 | 中（服务增值） | 高 | P2 | Phase 3 |
| M12 | 售后工单系统 | 中（服务增值） | 中 | P3 | Phase 3 |
| M13 | 移动端App | 中（效率提升） | 高 | P3 | Phase 3 |
| M14 | 应收账款融资 | 低（未来扩展） | 高 | P3 | Phase 3 |
| M15 | 性能优化部署 | 中（技术债） | 高 | P2 | Phase 3 |

---

## 第四章 核心功能模块详细需求

### M1: 数据库持久化与架构升级

#### 1.1 目标
将内存数据存储迁移至PostgreSQL 15，引入Redis作为缓存层，建立完整的ORM模型，确保数据持久化和高并发支持。

#### 1.2 数据库选型

| 组件 | 选型 | 用途 |
|------|------|------|
| 主数据库 | PostgreSQL 15 | 业务数据持久化（客户/合同/设备/交易/Token审计） |
| 缓存层 | Redis 7 | 热点数据缓存、Token序列预生成、Session存储 |
| ORM | SQLAlchemy 2.0 | 数据库抽象层，异步支持 |
| 迁移工具 | Alembic | 数据库版本管理 |

#### 1.3 核心数据模型

**customers（客户表）**
```sql
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mfi_id          UUID NOT NULL REFERENCES mfis(id),
    full_name       VARCHAR(100) NOT NULL,
    phone_number    VARCHAR(20) NOT NULL UNIQUE,
    id_card_number  VARCHAR(50),           -- 柬埔寨身份证号
    address         TEXT,
    province        VARCHAR(50),           -- 省份（金边/暹粒/西港等）
    commune         VARCHAR(50),           -- 社区
    village         VARCHAR(50),           -- 村庄
    gps_latitude    DECIMAL(10,8),
    gps_longitude   DECIMAL(11,8),
    credit_score    INTEGER DEFAULT 50,    -- 信用评分0-100
    status          VARCHAR(20) DEFAULT 'active', -- active/inactive/blacklisted
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

**devices（设备表）**
```sql
CREATE TABLE devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    serial_number   VARCHAR(50) NOT NULL UNIQUE,
    model           VARCHAR(50) NOT NULL,  -- Victron MultiPlus-II / ONESUN等
    capacity_kw     DECIMAL(5,2),          -- 系统容量（6-30kW）
    secret_key      BYTEA NOT NULL,        -- AES-256加密存储
    token_counter   INTEGER DEFAULT 1,     -- OpenPAYGO计数器
    starting_code   VARCHAR(15),           -- 首次激活码
    payg_enabled    BOOLEAN DEFAULT TRUE,  -- PAYGO模式是否启用
    status          VARCHAR(20) DEFAULT 'installed', 
                                    -- installed/active/locked/recovered/disabled
    customer_id     UUID REFERENCES customers(id),
    contract_id     UUID REFERENCES contracts(id),
    last_online_at  TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

**contracts（合同表）**
```sql
CREATE TABLE contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number VARCHAR(30) NOT NULL UNIQUE, -- KH-2026-00001格式
    customer_id     UUID NOT NULL REFERENCES customers(id),
    mfi_id          UUID NOT NULL REFERENCES mfis(id),
    device_id       UUID REFERENCES devices(id),
    total_amount    DECIMAL(12,2) NOT NULL,     -- 贷款总额（USD）
    down_payment    DECIMAL(12,2) NOT NULL,     -- 首付金额
    loan_amount     DECIMAL(12,2) NOT NULL,     -- 贷款本金
    interest_rate   DECIMAL(5,2) NOT NULL,      -- 年利率（%）
    term_months     INTEGER NOT NULL,           -- 贷款期限（12/24/36月）
    monthly_payment DECIMAL(10,2) NOT NULL,     -- 月供金额
    currency        VARCHAR(3) DEFAULT 'USD',   -- USD/KHR
    start_date      DATE NOT NULL,              -- 贷款开始日
    end_date        DATE NOT NULL,              -- 贷款结束日
    status          VARCHAR(20) DEFAULT 'pending',
                    -- pending/approved/active/overdue/closed/recovered
    remaining_days  INTEGER DEFAULT 0,          -- 设备剩余使用天数
    grace_period_end DATE,                     -- 宽限期结束日
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

**payments（支付记录表）**
```sql
CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    amount          DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL,
    payment_method  VARCHAR(20) NOT NULL,  -- bakong/cash/bank_transfer
    bakong_tx_id    VARCHAR(100),          -- Bakong交易ID
    status          VARCHAR(20) DEFAULT 'pending', 
                    -- pending/completed/failed/refunded
    paid_at         TIMESTAMP,
    token_generated BOOLEAN DEFAULT FALSE, -- 是否已生成Token
    token_id        UUID REFERENCES tokens(id),
    created_at      TIMESTAMP DEFAULT NOW()
);
```

**tokens（Token记录表）**
```sql
CREATE TABLE tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID NOT NULL REFERENCES devices(id),
    contract_id     UUID NOT NULL REFERENCES contracts(id),
    token_value     VARCHAR(15) NOT NULL,       -- 15位数字Token
    token_type      VARCHAR(20) NOT NULL,       -- ADD_TIME/SET_TIME/DISABLE_PAYG/COUNTER_SYNC
    days_added      INTEGER DEFAULT 0,          -- 增加/设置的天数
    counter_used    INTEGER NOT NULL,           -- 使用的计数器值
    status          VARCHAR(20) DEFAULT 'generated',
                    -- generated/sent/used/expired/revoked
    generated_at    TIMESTAMP DEFAULT NOW(),
    sent_at         TIMESTAMP,                  -- SMS发送时间
    used_at         TIMESTAMP,                  -- 客户输入使用时间
    sms_message_id  VARCHAR(100)               -- SMS网关消息ID
);
```

**token_audit_log（Token审计日志）**
```sql
CREATE TABLE token_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID NOT NULL,
    token_type      VARCHAR(20) NOT NULL,
    token_hash      VARCHAR(64) NOT NULL,       -- SHA-256哈希值
    counter         INTEGER NOT NULL,
    days            INTEGER,
    generated_at    TIMESTAMP DEFAULT NOW(),
    generated_by    VARCHAR(50) NOT NULL        -- 生成者身份
);
```

#### 1.4 Redis缓存策略

| 缓存Key | 数据类型 | TTL | 说明 |
|---------|---------|-----|------|
| `customer:{id}` | Hash | 300s | 客户基本信息 |
| `device:{serial}` | Hash | 300s | 设备状态和剩余天数 |
| `contract:{id}` | Hash | 300s | 合同详情 |
| `token_queue:{device_id}` | List | 3600s | 预生成Token队列 |
| `payment_lock:{contract_id}` | String | 60s | 支付处理分布式锁 |
| `session:{session_id}` | Hash | 3600s | 用户Session |
| `rate_limit:{ip}` | String | 60s | API速率限制计数 |

#### 1.5 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M1-R1 | 配置PostgreSQL连接池，支持异步操作 | 连接池大小可配置（默认20连接），支持async/await | P0 |
| M1-R2 | 使用Alembic管理数据库迁移 | 提供初始迁移脚本，支持upgrade/downgrade | P0 |
| M1-R3 | 所有现有API兼容新数据库层 | 现有79个测试全部通过，无需修改测试逻辑 | P0 |
| M1-R4 | Redis缓存集成 | 热点数据读取延迟<10ms，缓存命中率>80% | P1 |
| M1-R5 | 数据库连接健康检查 | /health端点返回数据库连接状态 | P1 |
| M1-R6 | 数据库备份脚本 | 每日自动全量备份，保留7天 | P2 |

---

### M2: Bakong支付系统集成

#### 2.1 目标
深度集成柬埔寨国家银行Bakong支付系统，支持KH/USD双币种，实现从支付到Token发放的自动化闭环。

#### 2.2 Bakong系统概述
Bakong是由柬埔寨国家银行（NBC）于2020年推出的基于Hyperledger Iroha区块链的银行间移动支付平台，连接全国所有持牌金融机构。截至2024年，已拥有850万+用户账户，支持KHR和USD双币种零手续费实时到账。

#### 2.3 集成架构

```
┌─────────────┐     REST API      ┌─────────────┐     ┌─────────────┐
│  PAYGO平台   │ ───────────────→ │ Bakong网关   │ ──→ │  MFI核心系统  │
│             │ ←─────────────── │             │     │  (CBS)       │
└─────────────┘   Webhook回调    └─────────────┘     └─────────────┘
       │                                                    ↑
       │         POST /webhooks/bakong                      │
       └────────────────────────────────────────────────────┘
                    支付状态变更通知
```

#### 2.4 核心对接场景

**场景1：客户通过MFI App还款（P2P转账）**
1. 客户登录MFI App，选择"太阳能贷款还款"
2. App显示应还金额（KHR或USD），客户确认后发起Bakong转账
3. 资金通过Bakong实时划转至太阳能公司账户，零手续费
4. Bakong发送支付确认Webhook至PAYGO平台
5. 平台验证支付金额与合同月供匹配
6. 平台调用Token服务生成ADD_TIME Token
7. SMS网关发送Token至客户手机
8. 整个流程从还款到系统解锁在5分钟内完成

**场景2：客户通过KHQR扫码还款**
1. 平台为每笔贷款生成唯一的KHQR码（柬埔寨统一二维码标准）
2. 客户使用任意支持Bakong的银行App扫描KHQR码
3. 扫码后自动填充收款方和应还金额
4. 支付完成后Bakong回调平台，触发Token生成

**场景3：MFI柜台现金还款**
1. 客户前往MFI分支机构柜台提供贷款编号和现金
2. MFI柜员在CBS系统中录入还款，同步至PAYGO平台
3. 平台生成Token并发送至客户手机

#### 2.5 API接口规范

| 接口 | 方法 | 用途 |
|------|------|------|
| `/api/v1/bakong/payments` | POST | 发起P2P转账支付 |
| `/api/v1/bakong/payments/{tx_id}` | GET | 查询支付状态 |
| `/api/v1/bakong/khqr` | POST | 生成KHQR码 |
| `/webhooks/bakong` | POST | 接收Bakong支付状态变更通知 |
| `/api/v1/bakong/statements` | GET | 按日获取交易明细（对账） |

#### 2.6 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M2-R1 | Bakong API客户端封装 | 支持HMAC-SHA256签名，超时重试3次 | P0 |
| M2-R2 | Webhook接收端点 | 支持幂等处理，防止重复Token发放 | P0 |
| M2-R3 | 支付金额与合同匹配验证 | 验证金额偏差在±1%以内，币种一致 | P0 |
| M2-R4 | 自动Token生成与SMS通知 | 支付成功后60秒内完成Token生成和SMS发送 | P0 |
| M2-R5 | KHQR码生成与展示 | 支持USD/KHR，二维码可在运营后台打印 | P1 |
| M2-R6 | 日终自动对账 | 每日凌晨2:00执行，比对Bakong流水与平台记录 | P1 |
| M2-R7 | 差错处理与人工复核 | 支付成功但Token未发/金额不匹配时进入待处理队列 | P1 |
| M2-R8 | 支付回调模拟器（开发测试用） | 开发环境可模拟Bakong回调，无需真实支付 | P1 |

---

### M3: SMS网关集成

#### 3.1 目标
集成柬埔寨本地SMS网关，实现Token自动发送、还款提醒、逾期通知等功能的双向SMS通信。

#### 3.2 通信架构

```
┌─────────────┐     SMPP/HTTP     ┌─────────────────┐     GSM网络
│  PAYGO平台   │ ───────────────→ │ Cellcard企业网关  │ ─────────→ 客户手机
│             │ ←─────────────── │ Smart备用网关    │            （+855）
└─────────────┘   投递状态报告     └─────────────────┘
```

#### 3.3 SMS模板设计（高棉语/英语双语）

| 场景 | 模板内容（英语） | 模板内容（高棉语） |
|------|-----------------|-------------------|
| Token发放 | "[新华智科技] Payment received! Your solar system is extended for {days} days. Activation code: {token}. Valid until {expiry}." | "[新华智科技] ការទូទាត់បានជោគជ័យ! ប្រព័ន្ធថាមពលព្រះអាទិត្យរបស់អ្នកត្រូវបានបន្ថែម{days}ថ្ងៃ។ លេខកូដសកម្មភាព: {token}" |
| 还款提醒（提前3天） | "[新华智科技] Reminder: Your solar payment of ${amount} is due on {due_date}. Please pay via Bakong KHQR or MFI App to avoid service interruption." | "[新华智科技] ការរំលឹក: ការទូទាត់ថាមពលព្រះអាទិត្យ{amount}ដុល្លារត្រូវបង់នៅថ្ងៃ{due_date}" |
| 逾期警告（第7天） | "[新华智科技] URGENT: Your solar payment is 7 days overdue. Your system will enter power-saving mode soon. Please pay immediately to restore full power." | "[新华智科技] បន្ទាន់: ការទូទាត់ហួសកំណត់7ថ្ងៃ។ សូមបង់ប្រាក់ភ្លាមៗ" |
| 降额通知（第16天） | "[新华智科技] NOTICE: Due to non-payment, your solar system has been reduced to 50% power. Pay ${amount} to restore full capacity." | "[新华智科技] ការជូនដំណឹង: ប្រព័ន្ធថាមពលត្រូវបានកាត់បន្ថយមួយភាគពីរដោយសារមិនបានបង់ប្រាក់" |
| 完全锁定（第31天） | "[新华智科技] FINAL NOTICE: Your solar system has been locked due to prolonged non-payment. Contact your MFI loan officer immediately." | "[新华智科技] ការជូនដំណឹងចុងក្រោយ: ប្រព័ន្ធត្រូវបានចាក់សោ។ សូមទាក់ទងមន្ត្រីកម្ចី" |
| 贷款结清 | "[新华智科技] Congratulations! Your solar loan is fully paid. Permanent unlock code: {token}. Your system is now fully yours!" | "[新华智科技] អបអរសាទរ! កម្ចីបានបង់រួចាល់។ លេខកូដដោះសោ: {token}" |

#### 3.4 双向SMS支持

| 客户发送 | 系统响应 |
|---------|---------|
| `BALANCE` | 返回剩余天数和下次还款日期 |
| `HELP` | 返回客服热线和还款指引 |
| `TOKEN` | 如果已支付未收到Token，重新发送 |

#### 3.5 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M3-R1 | SMS网关客户端封装 | 支持SMPP v3.4和HTTP API双模式，自动故障转移 | P0 |
| M3-R2 | Token自动SMS发送 | 支付成功后30秒内送达，成功率>99% | P0 |
| M3-R3 | 还款提醒定时任务 | 到期前3天自动发送，支持批量（每日凌晨执行） | P1 |
| M3-R4 | 逾期分级SMS通知 | 7/16/31天自动触发不同模板，记录发送状态 | P1 |
| M3-R5 | 双向SMS处理 | 支持BALANCE/HELP/TOKEN关键词回复 | P1 |
| M3-R6 | SMS发送状态追踪 | 记录message_id，支持投递状态查询 | P1 |
| M3-R7 | 高棉语Unicode支持 | SMS内容正确编码，高棉语手机正常显示 | P1 |
| M3-R8 | SMS网关模拟器（开发测试） | 开发环境不发送真实SMS，记录到日志和数据库 | P1 |

---

### M4: OpenPAYGO完整实现

#### 4.1 目标
完整实现OpenPAYGO Token标准v2.1的全部功能，包括所有Token类型、自动递减逻辑、控制器模拟器，确保与Victron、SolarRun、ONESUN等设备的兼容性。

#### 4.2 Token类型完整支持

| Token类型 | 功能 | 应用场景 | 当前状态 |
|-----------|------|---------|---------|
| `ADD_TIME` | 为设备增加指定天数 | 客户按月还款后延长使用期限 | 已支持 |
| `SET_TIME` | 将设备使用时间设置为指定天数 | 逾期降额（设为0即完全锁定） | 部分支持 |
| `DISABLE_PAYG` | 永久禁用PAYGO模式 | 贷款全部结清后转移所有权 | **未实现** |
| `COUNTER_SYNC` | 同步服务器与设备端计数器 | 解决计数器漂移问题 | **未实现** |
| `STARTING_CODE` | 设备首次激活码 | 新设备安装后首次启用 | **未实现** |

#### 4.3 remaining_days自动递减

**业务规则：**
- 每日00:00（柬埔寨时间UTC+7）自动递减所有激活设备的`remaining_days`
- 当`remaining_days` <= 3天时，发送即将到期提醒SMS
- 当`remaining_days` = 0时，进入宽限期（默认3天），期间设备降额运行（50%功率）
- 宽限期结束后，`remaining_days` = 0且未还款，设备完全锁定（0%功率）

**技术实现：**
```python
# Celery Beat定时任务（每日00:00 UTC+7执行）
@app.task
def daily_remaining_days_decrement():
    """每日递减所有激活设备的remaining_days"""
    # 1. 递减remaining_days > 0的设备
    # 2. 检测即将到期（<=3天）的设备并发送提醒
    # 3. 检测宽限期结束的设备并执行完全锁定
    # 4. 记录所有操作到audit_log
```

#### 4.4 控制器模拟器升级

当前控制器模拟器需升级支持：
1. **完整Token验证**：支持所有5种Token类型的解析和验证
2. **状态机完善**：增加`grace_period_days`计数、降额运行状态
3. **持久化**：状态保存到SQLite文件（替代当前内存存储）
4. **设备模拟批量管理**：支持模拟多台设备同时运行
5. **自动化测试接口**：提供API用于自动化测试Token全流程

#### 4.5 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M4-R1 | 实现DISABLE_PAYG永久解锁Token | 贷款结清后生成，设备输入后永久解除PAYGO限制 | P0 |
| M4-R2 | 实现COUNTER_SYNC计数器同步Token | 处理计数器漂移，设备可恢复正常同步 | P0 |
| M4-R3 | 实现Starting Code首次激活逻辑 | 新设备安装后生成30天初始激活码 | P0 |
| M4-R4 | remaining_days每日自动递减 | Celery定时任务，每日零点执行，支持柬埔寨时区 | P0 |
| M4-R5 | 宽限期与分级锁定逻辑 | 0天进入3天宽限期（50%功率），宽限期满完全锁定 | P0 |
| M4-R6 | 控制器模拟器全Token支持 | 模拟器可验证所有Token类型，状态机完整 | P1 |
| M4-R7 | Token使用审计日志 | 每次Token生成/发送/使用均记录不可篡改日志 | P1 |
| M4-R8 | Token序列预生成 | 支持批量预生成未来12个月Token，存储于Redis | P2 |

---

### M5: 安全架构升级

#### 5.1 目标
建立符合金融科技行业标准的安全体系，满足柬埔寨数据保护法规和央行合规要求。

#### 5.2 安全需求矩阵

| 安全域 | 当前状态 | 目标状态 | 实现方案 |
|--------|---------|---------|---------|
| 密码存储 | 明文 | bcrypt哈希 | bcrypt(password, rounds=12) |
| 传输加密 | HTTP | HTTPS (TLS 1.3) | Let's Encrypt证书 |
| API认证 | Session Cookie | JWT + Refresh Token | PyJWT, access_token 15min |
| 设备密钥 | 明文 | AES-256加密 | Fernet (cryptography库) |
| 审计日志 | 无 | 完整操作审计 | 独立audit_log表，WAL模式 |
| 输入校验 | 基础 | 严格校验 | Pydantic + 自定义validators |
| 速率限制 | 无 | API级别限流 | Redis + slowapi |
| SQL注入 | 可能风险 | ORM参数化查询 | SQLAlchemy Core |

#### 5.3 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M5-R1 | 管理员密码bcrypt哈希 | 现有明文密码迁移为哈希，登录时验证 | P0 |
| M5-R2 | JWT认证替换Session | Access Token 15分钟, Refresh Token 7天 | P0 |
| M5-R3 | 设备Secret Key AES-256加密 | 数据库中无明文密钥，加密密钥环境变量管理 | P0 |
| M5-R4 | API速率限制 | 100次/分钟/IP，登录5次/分钟 | P1 |
| M5-R5 | 操作审计日志 | 所有关键操作记录用户/时间/IP/操作结果 | P1 |
| M5-R6 | HTTPS强制 | 生产环境HTTP自动跳转HTTPS，HSTS头 | P1 |

---

### M6: 客户360视图与MFI管理

#### 6.1 目标
建立完整的客户信息管理体系，支持MFI（小额信贷机构）多租户模式，形成客户360度视图。

#### 6.2 MFI管理

**支持的MFI机构：**
- LOLC Cambodia
- PRASAC
- ACLEDA Bank
- AMK Microfinance
- Amret Microfinance

**MFI数据模型：**
```sql
CREATE TABLE mfis (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(20) NOT NULL UNIQUE, -- LOLC/PRASAC/ACLEDA
    contact_person  VARCHAR(100),
    phone           VARCHAR(20),
    email           VARCHAR(100),
    address         TEXT,
    status          VARCHAR(20) DEFAULT 'active',
    created_at      TIMESTAMP DEFAULT NOW()
);
```

#### 6.3 客户360视图

单个客户页面整合：
- **基本信息**：姓名、电话、地址、GPS坐标、身份证号
- **合同信息**：所有历史/当前合同列表、还款进度
- **设备信息**：已安装设备、当前状态、剩余天数
- **支付历史**：所有还款记录、支付方式、状态
- **Token历史**：所有接收/使用的Token记录
- **服务工单**：售后维修记录
- **通信记录**：所有SMS发送记录
- **信用评分**：基于还款行为的动态评分

#### 6.4 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M6-R1 | MFI基础CRUD管理 | 支持增删改查，MFI编码唯一 | P1 |
| M6-R2 | 客户信息扩展字段 | 支持柬埔寨地址结构（省/社区/村） | P1 |
| M6-R3 | 客户GPS坐标记录 | 安装时记录设备GPS位置，地图展示 | P1 |
| M6-R4 | 客户360视图页面 | 单页展示客户所有关联信息 | P1 |
| M6-R5 | 客户搜索与筛选 | 按姓名/电话/合同号/MFI筛选 | P1 |
| M6-R6 | 客户导入导出 | 支持CSV批量导入客户数据 | P2 |
| M6-R7 | 信用评分模型v1 | 基于还款准时率的简单评分（0-100） | P2 |

---

### M7: 合同与还款计划引擎

#### 7.1 目标
建立完整的合同管理和还款计划引擎，支持灵活的贷款产品配置。

#### 7.2 贷款产品配置

| 产品参数 | 配置范围 | 默认值 |
|---------|---------|--------|
| 系统规模 | 6kW / 10kW / 15kW / 20kW / 30kW | - |
| 贷款期限 | 12/18/24/36个月 | 24个月 |
| 年利率 | 8%-18% | 12% |
| 首付比例 | 10%-30% | 20% |
| 还款频率 | 月付/双周付 | 月付 |
| 币种 | USD / KHR | USD |

#### 7.3 还款计划生成

等额本息还款公式：
```
月供 = 贷款本金 × [月利率 × (1+月利率)^期数] / [(1+月利率)^期数 - 1]
```

#### 7.4 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M7-R1 | 合同创建与审批流程 | 支持pending→approved→active状态流转 | P1 |
| M7-R2 | 自动还款计划生成 | 根据贷款参数生成完整的还款计划表 | P1 |
| M7-R3 | 还款日历视图 | 按月展示所有合同的还款安排 | P1 |
| M7-R4 | 合同模板打印 | 生成PDF格式贷款合同（高棉语+英语） | P2 |
| M7-R5 | 提前还款计算 | 支持部分/全部提前还款，自动重新计算 | P2 |

---

### M8: 逾期预警与自动锁定系统

#### 8.1 目标
建立自动化的逾期检测、预警和分级锁定机制，降低贷款违约风险。

#### 8.2 分级处理策略

| 阶段 | 逾期天数 | 系统操作 | 通知方式 |
|------|---------|---------|---------|
| 阶段1 | 1-7天 | 发送第一次SMS提醒 | SMS |
| 阶段2 | 8-15天 | 发送第二次SMS + 标记高风险 | SMS |
| 阶段3 | 16-30天 | 设备降额至50%（SET_TIME Token） | SMS + 运营后台告警 |
| 阶段4 | 31-60天 | 设备完全锁定（SET_TIME=0 Token） | SMS + MFI通知 |
| 阶段5 | 60+天 | 启动设备回收流程 | 邮件 + 工单 |

#### 8.3 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M8-R1 | 每日逾期扫描任务 | 自动检测所有逾期合同，更新逾期天数 | P1 |
| M8-R2 | 分级预警自动触发 | 根据逾期天数自动执行对应策略 | P1 |
| M8-R3 | 设备降额Token自动发送 | 逾期16天自动生成SET_TIME=half Token | P1 |
| M8-R4 | 设备锁定Token自动发送 | 逾期31天自动生成SET_TIME=0 Token | P1 |
| M8-R5 | 逾期客户清单与报表 | 运营后台实时展示逾期客户列表 | P1 |
| M8-R6 | 宽限期管理 | 支持为特定客户手动延长宽限期 | P2 |

---

### M9: 运营仪表盘与报表系统

#### 9.1 目标
提供实时运营数据可视化，支持管理决策，对标GOGLA行业标准KPI。

#### 9.2 仪表盘组件

| 组件 | 指标 | 数据来源 |
|------|------|---------|
| 业务概览卡片 | 总客户数/活跃设备数/本月收入/逾期率 | 实时计算 |
| 收入趋势图 | 按月展示还款收入趋势（USD/KHR） | payments表 |
| 设备状态分布 | 正常/即将到期/宽限期/锁定/离线 饼图 | devices表 |
| 逾期热力图 | 按省份展示逾期分布 | contracts + customers |
| 最近交易列表 | 最近20笔支付记录实时刷新 | payments表 |
| Token发放统计 | 今日/本周/本月Token发放数量 | tokens表 |

#### 9.3 GOGLA标准KPI

| KPI指标 | 计算方式 |
|---------|---------|
| 客户获取成本（CAC） | 总销售成本 / 新增客户数 |
| 贷款组合风险（PAR） | 逾期>30天贷款余额 / 总贷款余额 |
| 还款率 | 实际收款 / 应收款 |
| 设备可用率 | 正常运性设备 / 总安装设备 |
| 客户留存率 | 持续还款客户 / 总活跃客户 |

#### 9.4 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M9-R1 | 运营仪表盘首页 | 核心指标一目了然，数据实时刷新 | P2 |
| M9-R2 | 收入分析报表 | 支持按MFI/月份/产品筛选 | P2 |
| M9-R3 | 逾期分析报表 | 按逾期天数/省份/MFI分布 | P2 |
| M9-R4 | 设备状态监控面板 | 地图展示设备位置与状态 | P2 |
| M9-R5 | GOGLA KPI自动计算 | 按季度自动生成标准KPI报告 | P3 |
| M9-R6 | 报表导出PDF/Excel | 支持打印和下载 | P2 |

---

### M10: RBAC权限与多租户隔离

#### 10.1 目标
实现基于角色的访问控制，支持多MFI数据隔离，满足不同角色的操作权限需求。

#### 10.2 角色定义

| 角色 | 权限范围 |
|------|---------|
| 超级管理员 | 全平台管理，包括MFI管理、系统配置 |
| MFI管理员 | 管理所属MFI下的所有客户、合同、还款 |
| 运营专员 | 客户管理、合同创建、Token手动发放 |
| 财务专员 | 支付确认、对账、退款处理、报表查看 |
| 客服专员 | 客户查询、Token重发、工单创建 |
| 技术员 | 设备安装、设备状态查看、控制器调试 |

#### 10.3 需求规格说明

| 需求ID | 需求描述 | 验收标准 | 优先级 |
|--------|---------|---------|--------|
| M10-R1 | RBAC权限模型 | 角色与权限可配置，API接口级别控制 | P2 |
| M10-R2 | MFI数据隔离 | 用户只能查看所属MFI的数据 | P2 |
| M10-R3 | 用户管理CRUD | 管理员可创建/编辑/禁用用户 | P2 |
| M10-R4 | 操作日志追踪 | 记录每个用户的所有操作 | P2 |

---

## 第五章 数据持久化与数据库架构升级

> 本章节为M1模块的详细技术实施规范。

### 5.1 迁移策略

采用**增量迁移**策略，确保现有API和测试不受影响：

1. **阶段1**：引入SQLAlchemy ORM，建立新模型，保留内存数据库作为fallback
2. **阶段2**：开发数据库迁移脚本（Alembic），初始化生产数据库
3. **阶段3**：切换API至新数据库层，运行全部测试验证
4. **阶段4**：移除内存数据库代码，清理遗留代码

### 5.2 数据库连接配置

```python
# config/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL异步连接
DATABASE_URL = "postgresql+asyncpg://paygo_user:{password}@localhost:5432/paygo_platform"
engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Redis连接
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
```

### 5.3 实体关系图（ERD）

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    mfis     │ 1:N   │  customers  │ 1:N   │  contracts  │
├─────────────┤──────→├─────────────┤──────→├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ name        │       │ mfi_id (FK) │       │ customer_id │
│ code        │       │ full_name   │       │ mfi_id      │
└─────────────┘       │ phone       │       │ device_id   │
                      │ province    │       │ status      │
                      └─────────────┘       └─────────────┘
                             │ 1:1                │
                             │                    │
                             ↓                    ↓
                      ┌─────────────┐       ┌─────────────┐
                      │   devices   │       │   payments  │
                      ├─────────────┤       ├─────────────┤
                      │ id (PK)     │       │ id (PK)     │
                      │ serial_num  │       │ contract_id │
                      │ secret_key  │       │ amount      │
                      │ customer_id │       │ status      │
                      │ contract_id │       │ token_id ───────→┌──────────┐
                      │ status      │       └─────────────┘    │  tokens  │
                      └─────────────┘                           ├──────────┤
                                                                │ id (PK)  │
                                                                │ token_val│
                                                                │ device_id│
                                                                │ status   │
                                                                └──────────┘
```

---

## 第六章 Bakong支付系统集成方案

> 本章节为M2模块的详细技术实施规范。

### 6.1 Bakong API客户端架构

```python
# services/bakong_client.py
class BakongClient:
    """Bakong API 客户端 - 支持支付发起/查询/对账"""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
    
    async def create_payment(self, amount: Decimal, currency: str, 
                            from_account: str, to_account: str,
                            description: str, external_ref: str) -> dict:
        """发起P2P转账支付"""
        payload = { ... }
        return await self._signed_request("POST", "/api/v1/payments", payload)
    
    async def query_payment(self, transaction_id: str) -> dict:
        """查询支付状态"""
        return await self._signed_request("GET", f"/api/v1/payments/{transaction_id}")
    
    async def generate_khqr(self, amount: Decimal, currency: str,
                           merchant_name: str, bill_number: str) -> dict:
        """生成KHQR码"""
        payload = { ... }
        return await self._signed_request("POST", "/api/v1/khqr", payload)
    
    def _generate_signature(self, payload: str, timestamp: str) -> str:
        """HMAC-SHA256签名"""
        message = f"{timestamp}.{payload}"
        return hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
```

### 6.2 Webhook处理流程

```python
# routers/webhooks.py
@router.post("/webhooks/bakong")
async def bakong_webhook_handler(payload: BakongWebhookPayload, db: AsyncSession = Depends(get_db)):
    """
    Bakong支付状态变更Webhook处理
    
    处理流程：
    1. 验证Webhook签名（防篡改）
    2. 幂等检查（防止重复处理）
    3. 查找对应合同
    4. 验证支付金额
    5. 更新支付记录状态
    6. 生成ADD_TIME Token
    7. 发送SMS通知
    8. 记录审计日志
    """
    # 实现...
```

### 6.3 KHQR码展示

运营后台合同详情页集成：
- 展示KHQR码图片（PNG格式，300x300px）
- 显示收款方信息（公司名称、Bakong账号）
- 显示应还金额和币种
- 支持打印和下载

---

## 第七章 SMS网关集成方案

> 本章节为M3模块的详细技术实施规范。

### 7.1 SMS网关抽象层

```python
# services/sms_gateway.py
from abc import ABC, abstractmethod

class SMSGateway(ABC):
    """SMS网关抽象基类"""
    
    @abstractmethod
    async def send_sms(self, phone_number: str, message: str, 
                       template_id: str = None) -> str:
        """发送SMS，返回message_id"""
        pass
    
    @abstractmethod
    async def query_status(self, message_id: str) -> str:
        """查询发送状态"""
        pass

class CellcardSMSGateway(SMSGateway):
    """Cellcard企业短信网关实现"""
    pass

class SmartSMSGateway(SMSGateway):
    """Smart备用网关实现"""
    pass

class MockSMSGateway(SMSGateway):
    """模拟网关（开发测试用）- 记录到数据库不发送"""
    pass

# 工厂模式根据环境创建对应网关
class SMSGatewayFactory:
    @staticmethod
    def get_gateway() -> SMSGateway:
        if settings.ENV == "production":
            return CellcardSMSGateway()  # 主通道
        return MockSMSGateway()  # 开发/测试环境
```

### 7.2 SMS模板引擎

```python
# services/sms_templates.py
class SMSTemplateEngine:
    """SMS模板引擎 - 支持多语言和变量替换"""
    
    TEMPLATES = {
        "token_issued": {
            "en": "[XHZ Tech] Payment received! System extended {days} days. Code: {token}",
            "km": "[ថាមពលព្រះអាទិត្យ] ការទូទាត់បានជោគជ័យ! បន្ថែម{days}ថ្ងៃ។ លេខកូដ: {token}"
        },
        "payment_reminder": {
            "en": "[XHZ Tech] Reminder: Payment ${amount} due on {due_date}. Pay via Bakong to avoid interruption.",
            "km": "[ថាមពលព្រះអាទិត្យ] រំលឹក: ត្រូវបង់{amount}ដុល្លារនៅ{due_date}"
        },
        # ... 更多模板
    }
    
    @classmethod
    def render(cls, template_name: str, lang: str = "km", **kwargs) -> str:
        template = cls.TEMPLATES[template_name][lang]
        return template.format(**kwargs)
```

---

## 第八章 设备控制器模拟与OpenPAYGO完整实现

> 本章节为M4模块的详细技术实施规范。

### 8.1 控制器模拟器架构

```python
# controller/simulator.py
class PAYGODeviceSimulator:
    """
    PAYGO设备控制器模拟器
    
    模拟真实设备的行为：
    - Token输入和验证
    - 状态机管理（正常/降额/锁定）
    - remaining_days每日递减
    - 宽限期管理
    - 持久化存储（SQLite）
    """
    
    def __init__(self, device_serial: str, secret_key: str):
        self.serial = device_serial
        self.secret_key = secret_key
        self.token_counter = 1
        self.remaining_days = 0
        self.grace_period_days = 0
        self.payg_enabled = True
        self.power_limit = 0  # 0=锁定, 50=降额, 100=全功率
        self.invalid_token_count = 0
        self.state_file = f"controller_states/{device_serial}.db"
        self._load_state()
    
    def process_token(self, token: str) -> dict:
        """处理输入的Token，返回结果"""
        # 1. Token解码和验证
        # 2. 根据类型处理（ADD_TIME/SET_TIME/DISABLE_PAYG/COUNTER_SYNC）
        # 3. 更新状态机
        # 4. 持久化
        # 5. 返回操作结果
        pass
    
    def daily_tick(self) -> dict:
        """每日时钟触发 - 递减remaining_days"""
        # 1. 递减remaining_days
        # 2. 检查是否进入宽限期
        # 3. 检查是否完全锁定
        # 4. 保存状态
        pass
    
    def _load_state(self):
        """从SQLite加载设备状态"""
        pass
    
    def _save_state(self):
        """保存设备状态到SQLite"""
        pass
```

### 8.2 批量设备模拟器

```python
# controller/batch_simulator.py
class BatchDeviceSimulator:
    """
    批量设备模拟器 - 支持同时模拟多台设备
    
    用途：
    - 压力测试Token生成服务
    - 模拟大规模设备运营场景
    - 自动化集成测试
    """
    
    def __init__(self):
        self.devices: dict[str, PAYGODeviceSimulator] = {}
    
    def register_device(self, serial: str, secret_key: str) -> PAYGODeviceSimulator:
        """注册新设备到模拟器"""
        device = PAYGODeviceSimulator(serial, secret_key)
        self.devices[serial] = device
        return device
    
    async def daily_tick_all(self) -> list[dict]:
        """对所有设备执行每日时钟"""
        results = []
        for device in self.devices.values():
            result = device.daily_tick()
            results.append(result)
        return results
    
    async def simulate_token_input(self, serial: str, token: str) -> dict:
        """模拟设备Token输入"""
        if serial not in self.devices:
            raise ValueError(f"Device {serial} not found")
        return self.devices[serial].process_token(token)
```

---

## 第九章 运营后台与数据可视化

> 本章节为M6-M9模块的前端界面需求规范。

### 9.1 运营后台页面结构

```
dashboard/                          # 运营后台
├── index                           # 运营仪表盘首页（M9）
│   ├── 业务概览卡片
│   ├── 收入趋势图
│   ├── 设备状态分布
│   └── 最近交易列表
├── customers/                      # 客户管理（M6）
│   ├── list                        # 客户列表页（搜索/筛选/分页）
│   ├── detail/{id}                 # 客户360视图
│   ├── create                      # 新建客户
│   └── import                      # 批量导入
├── contracts/                      # 合同管理（M7）
│   ├── list                        # 合同列表
│   ├── detail/{id}                 # 合同详情（还款计划/历史）
│   ├── create                      # 新建合同
│   └── khqr/{id}                   # KHQR码展示（M2）
├── devices/                        # 设备管理（M4）
│   ├── list                        # 设备列表
│   ├── detail/{serial}             # 设备详情
│   ├── simulator                   # 控制器模拟器
│   └── map                         # 设备地图（GPS）
├── payments/                       # 支付管理（M2）
│   ├── list                        # 支付记录
│   ├── pending                     # 待确认支付
│   └── reconciliation              # 对账界面
├── tokens/                         # Token管理（M4）
│   ├── list                        # Token记录
│   ├── generate                    # 手动生成Token
│   └── audit                       # 审计日志
├── overdue/                        # 逾期管理（M8）
│   ├── list                        # 逾期客户清单
│   ├── alert-rules                 # 预警规则配置
│   └── actions                     # 批量操作
├── sms/                            # SMS管理（M3）
│   ├── log                         # 发送记录
│   ├── templates                   # 模板管理
│   └── inbox                       # 收件箱（双向SMS）
├── reports/                        # 报表系统（M9）
│   ├── revenue                     # 收入报表
│   ├── overdue                     # 逾期分析
│   ├── portfolio                   # 组合分析
│   └── gogla                       # GOGLA KPI
└── settings/                       # 系统设置（M10）
    ├── users                       # 用户管理
    ├── roles                       # 角色权限
    ├── mfis                        # MFI管理
    ├── exchange-rate               # 汇率配置
    └── bakong                      # Bakong配置
```

### 9.2 前端技术选型

保持现有技术栈（Jinja2 + 纯CSS）的基础上，引入以下组件：

| 组件 | 用途 | 引入方式 |
|------|------|---------|
| Chart.js | 数据图表（趋势/饼图/热力图） | CDN引入 |
| DataTables | 表格排序/筛选/分页 | CDN引入 |
| Leaflet.js | 设备GPS地图展示 | CDN引入 |
| qrcode.js | KHQR码生成 | CDN引入 |

---

## 第十章 安全架构升级

> 本章节为M5模块的详细技术实施规范。

### 10.1 认证流程（JWT）

```
┌──────────┐     POST /api/auth/login      ┌──────────┐
│  客户端   │ ─────────────────────────────→ │  服务端   │
│          │    {username, password}        │          │
│          │ ←───────────────────────────── │          │
│          │    {access_token, refresh_token}          │
│          │                                │          │
│          │     GET /api/protected        │          │
│          │ ─────────────────────────────→ │          │
│          │    Authorization: Bearer {access_token}   │
│          │ ←───────────────────────────── │          │
│          │    {data} / 401 Unauthorized   │          │
└──────────┘                                └──────────┘
```

### 10.2 设备密钥加密

```python
from cryptography.fernet import Fernet

# 主密钥从环境变量获取
MASTER_KEY = os.environ.get('PAYGO_MASTER_KEY')  # Fernet.generate_key()
cipher = Fernet(MASTER_KEY)

# 加密Secret Key
def encrypt_secret_key(plain_key: str) -> bytes:
    return cipher.encrypt(plain_key.encode())

# 解密Secret Key
def decrypt_secret_key(encrypted_key: bytes) -> str:
    return cipher.decrypt(encrypted_key).decode()
```

### 10.3 安全Headers配置

```python
# middleware/security.py
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

middleware = [
    Middleware(TrustedHostMiddleware, allowed_hosts=["*.yourcompany.com.kh"]),
    Middleware(CORSMiddleware, 
               allow_origins=["https://paygo.yourcompany.com.kh"],
               allow_credentials=True,
               allow_methods=["GET", "POST", "PUT", "DELETE"],
               allow_headers=["*"]),
]

# 安全Headers
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

## 第十一章 迭代路线图与里程碑规划

### 11.1 迭代路线图

```
Month 1          Month 2          Month 3          Month 4          Month 5
|                |                |                |                |
├─ Phase 1: 核心运营能力 ───────────────┤
│  Week1-2       Week3-4         Week5-6         Week7-8          │
│  ├─ M1 DB ─────┤                │                │               │
│  │  PostgreSQL  │                │                │               │
│  │  Redis缓存   │                │                │               │
│  ├──────────────┼─ M2 Bakong ───┤                │               │
│  │              │  支付/Webhook  │                │               │
│  │              ├────────────────┼─ M3 SMS ──────┤               │
│  │              │                │  网关/模板     │               │
│  │              │                ├────────────────┼─ M4 OpenPAYGO ┤
│  │              │                │                │  完整实现     │
│  │              │                │                │  模拟器升级   │
│  │              │                │                ├───────────────┤
│  │              │                │                │ M5 安全升级  │
│                │                │                │               │
├────────────────┴────────────────┼─ Phase 2: 运营管理能力 ────────┤
│                                 │  Week9-12      Week13-16      │
│                                 │  ├─ M6 客户360 ─┤               │
│                                 │  ├─ M7 合同引擎 ┤               │
│                                 │  ├─ M8 逾期预警 ┤               │
│                                 │  └─ M9 仪表盘 ──┘               │
│                                 │                ├─ M10 RBAC ────┤
│                                                               │
├─────────────────────────────────┴────────────────┼─ Phase 3: 规模化 ─┤
│                                                  │  Week17-20        │
│                                                  │  M11 遥测监控      │
│                                                  │  M12 售后工单      │
│                                                  │  M15 性能优化      │
```

### 11.2 里程碑定义

| 里程碑 | 时间 | 交付物 | 成功标准 |
|--------|------|--------|---------|
| **MVP-1** | 第4周末 | 可接受真实支付的系统 | Bakong支付→自动生成Token→SMS发送，全流程自动化 |
| **MVP-2** | 第8周末 | 具备核心运营能力的平台 | 包含M1-M5全部功能，可管理200+设备 |
| **V1.0** | 第12周末 | 完整运营级平台 | 包含M6-M10，支持多MFI协作，完整报表系统 |
| **V2.0** | 第20周末 | 规模化运营平台 | 包含M11-M15，支持10,000+设备，高可用部署 |

### 11.3 关键依赖关系

```
M1（数据库）─────────→ 所有其他模块的基础依赖
 │
 ├──→ M2（Bakong支付）
 ├──→ M3（SMS网关）
 ├──→ M4（OpenPAYGO）
 └──→ M5（安全升级）
       │
       ├──→ M6（客户管理）
       ├──→ M7（合同引擎）
       ├──→ M8（逾期预警）
       ├──→ M9（仪表盘）
       └──→ M10（RBAC）
```

---

## 第十二章 Superpowers框架升级手册

### 12.1 Superpowers框架概述

Superpowers是一个完整的agentic软件开发框架，由Jesse Vincent（obra）创建，专为AI辅助编程设计。该框架基于一组可组合的技能（skills）和严格的开发纪律，确保AI代理能够高质量地完成软件开发任务。

**核心原则：**
- **TDD强制**：所有功能必须先写测试再写实现（test-driven-development技能）
- **计划先行**：每个开发阶段前必须编写实施计划（writing-plans技能）
- **子代理开发**：复杂任务使用子代理执行（subagent-driven-development技能）
- **双重审查**：规格合规审查 + 代码质量审查
- **验证完成**：所有功能必须通过测试验证（verification-before-completion技能）
- **频繁提交**：每个小步骤完成后提交代码

### 12.2 技能系统详解

Superpowers框架通过**skills**（技能）系统指导AI代理的行为。每个技能是一个独立的目录，包含SKILL.md文件和相关资源。

#### 12.2.1 核心技能清单

| 技能名称 | 用途 | 触发条件 |
|----------|------|----------|
| `test-driven-development` | 强制TDD开发流程 | 任何功能实现或Bug修复前 |
| `writing-plans` | 编写详细的实施计划 | 有多步骤任务需要执行时 |
| `subagent-driven-development` | 子代理分工开发 | 独立任务较多时 |
| `executing-plans` | 按计划逐步执行 | 计划已编写完成时 |
| `verification-before-completion` | 完成前验证 | 任务声称完成前 |
| `using-git-worktrees` | Git工作树管理 | 需要并行开发分支时 |
| `systematic-debugging` | 系统化调试 | 遇到Bug需要修复时 |
| `receiving-code-review` | 接收代码审查 | 收到代码审查反馈时 |
| `requesting-code-review` | 请求代码审查 | 代码完成后请求审查 |
| `finishing-a-development-branch` | 完成开发分支 | 分支开发完成时 |

#### 12.2.2 技能使用模式

```
用户提出需求
    ↓
[writing-plans] 编写实施计划
    ↓
[subagent-driven-development] 或 [executing-plans] 执行计划
    ↓
  每个任务执行前：
    [test-driven-development] 先写测试
    实现代码
    运行测试（绿）
    重构（可选）
    git commit
    ↓
[verification-before-completion] 验证所有功能
    ↓
[requesting-code-review] 请求代码审查（如需要）
```

### 12.3 项目Superpowers配置

#### 12.3.1 项目级CLAUDE.md

在项目根目录创建/更新`CLAUDE.md`文件，作为项目的全局上下文：

```markdown
# 柬埔寨太阳能PAYGO平台 - CLAUDE.md

## 项目概述
柬埔寨太阳能发电系统PAYGO平台运营级系统。基于OpenPAYGO Token标准，与MFI合作提供分期付款太阳能系统。

## 技术栈
- 后端：Python FastAPI + SQLAlchemy 2.0（异步）
- 数据库：PostgreSQL 15 + Redis 7
- 前端：Jinja2模板 + 纯CSS（绿色主题#059669）
- Token：OpenPAYGO标准v2.1
- 支付：Bakong（柬埔寨国家银行数字支付平台）
- SMS：Cellcard/Smart企业网关（SMPP协议）

## 开发规范
- 强制TDD：每个功能必须先有失败的测试，再写实现代码
- 代码注释使用中文
- 所有API接口使用 `/api/` 前缀
- 认证方式：JWT（Access Token 15分钟 + Refresh Token 7天）
- 每次变更后运行全部测试验证：`pytest tests/ -v`
- 每个功能完成后编写简短的中文提交信息
- 使用Alembic管理数据库迁移
- 设备Secret Key使用AES-256加密存储

## Superpowers框架配置
- 强制使用TDD：所有功能必须先写测试再写实现
- 计划先行：每个开发阶段前必须编写实施计划（保存到docs/superpowers/plans/）
- 子代理开发：复杂任务使用子代理执行
- 双重审查：规格合规审查 + 代码质量审查
- 验证前完成：所有功能必须通过测试验证
- 频繁提交：每个小步骤完成后提交代码

## 目录结构
```
paygo-platform/
├── app/                    # FastAPI应用
│   ├── main.py             # 主应用入口
│   ├── config.py           # 配置管理
│   ├── models/             # SQLAlchemy模型
│   ├── schemas/            # Pydantic模型
│   ├── routers/            # API路由
│   ├── services/           # 业务逻辑服务
│   ├── core/               # 安全/认证/工具
│   └── dependencies.py     # FastAPI依赖
├── controller/             # 设备控制器模拟器
├── migrations/             # Alembic迁移脚本
├── docs/superpowers/       # Superpowers文档
│   ├── plans/              # 实施计划
│   └── specs/              # 设计规格
├── tests/                  # 测试用例
└── requirements.txt
```

## 启动命令
```bash
# 开发环境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行所有测试
pytest tests/ -v

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head
```
```

#### 12.3.2 技能特定配置

在项目`docs/superpowers/`目录下创建技能配置：

```
docs/superpowers/
├── plans/                          # 实施计划目录
│   ├── 2026-05-19-m1-database-migration.md
│   ├── 2026-05-20-m2-bakong-integration.md
│   ├── 2026-05-22-m3-sms-gateway.md
│   └── ...
└── specs/                          # 设计规格
    ├── database-schema.md
    ├── bakong-api-spec.md
    ├── sms-gateway-spec.md
    └── openpaygo-token-spec.md
```

### 12.4 升级实施方法论

#### 12.4.1 阶段式升级流程

每个模块（M1-M10）的升级遵循以下标准化流程：

```
┌─────────────────────────────────────────────────────────┐
│  Phase A: 规划（Planning）                               │
│  1. 用户需求分析 → 2. 编写规格文档 → 3. 编写实施计划       │
│  工具：writing-plans技能                                  │
├─────────────────────────────────────────────────────────┤
│  Phase B: 开发（Development）                            │
│  4. TDD循环：写测试 → 运行失败 → 写实现 → 运行通过 → 提交 │
│  工具：test-driven-development技能                        │
├─────────────────────────────────────────────────────────┤
│  Phase C: 审查（Review）                                 │
│  5. 规格合规审查 → 6. 代码质量审查                       │
│  工具：subagent-driven-development中的review流程         │
├─────────────────────────────────────────────────────────┤
│  Phase D: 验证（Verification）                           │
│  7. 运行全部测试 → 8. 集成测试 → 9. 性能测试             │
│  工具：verification-before-completion技能                │
├─────────────────────────────────────────────────────────┤
│  Phase E: 交付（Delivery）                               │
│  10. 合并代码 → 11. 更新文档 → 12. 部署验证              │
│  工具：finishing-a-development-branch技能                │
└─────────────────────────────────────────────────────────┘
```

#### 12.4.2 TDD开发规范

每个功能模块的开发必须严格遵循TDD流程：

```python
# 第1步：写测试（测试文件：tests/test_m1_database.py）
# 测试规则：测试函数命名规范 test_<模块>_<功能>_<场景>

async def test_customer_create_with_postgresql(db_session: AsyncSession):
    """测试：使用PostgreSQL创建客户记录"""
    # Arrange: 准备测试数据
    customer_data = {
        "full_name": "测试客户",
        "phone_number": "+855123456789",
        "province": "金边",
        "mfi_id": str(uuid.uuid4())
    }
    
    # Act: 执行操作
    customer = Customer(**customer_data)
    db_session.add(customer)
    await db_session.commit()
    
    # Assert: 验证结果
    result = await db_session.execute(
        select(Customer).where(Customer.phone_number == "+855123456789")
    )
    saved = result.scalar_one()
    assert saved.full_name == "测试客户"
    assert saved.id is not None
    assert saved.created_at is not None

# 第2步：运行测试 → 预期失败（Red）
# pytest tests/test_m1_database.py::test_customer_create_with_postgresql -v
# 预期：FAILED - NameError: name 'Customer' is not defined

# 第3步：写最小实现（app/models/customer.py）
class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    mfi_id = Column(UUID, ForeignKey("mfis.id"), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True)
    province = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

# 第4步：运行测试 → 预期通过（Green）
# pytest tests/test_m1_database.py::test_customer_create_with_postgresql -v
# 预期：PASSED

# 第5步：重构（如有需要）
# - 提取重复代码
# - 优化查询性能
# - 添加索引

# 第6步：提交
# git add .
# git commit -m "M1: 实现Customer模型和创建测试"
```

#### 12.4.3 测试分层策略

| 测试类型 | 命名规范 | 数量目标 | 运行频率 |
|---------|---------|---------|---------|
| 单元测试 | `test_<模块>_unit_<功能>` | 200+ | 每次提交 |
| 集成测试 | `test_<模块>_integration_<场景>` | 50+ | 每次提交 |
| API测试 | `test_api_<路由>_<方法>_<场景>` | 100+ | 每次提交 |
| 端到端测试 | `test_e2e_<业务流程>` | 20+ | 每日CI |
| 性能测试 | `test_perf_<模块>_<指标>` | 10+ | 每周 |

### 12.5 代码质量保证

#### 12.5.1 代码审查标准

| 审查维度 | 检查项 | 通过标准 |
|---------|--------|---------|
| 规格合规 | 是否按需求实现 | 所有AC（验收条件）满足 |
| 测试覆盖 | 是否有足够测试 | 行覆盖率>90%，分支覆盖率>80% |
| 代码风格 | 是否符合PEP 8 | flake8零警告 |
| 类型注解 | 是否有类型提示 | 主要函数100%类型注解 |
| 文档注释 | 是否有中文注释 | 复杂逻辑必须注释 |
| 安全审查 | 是否有安全隐患 | 无SQL注入/XSS/明文存储 |
| 性能审查 | 是否有性能问题 | N+1查询已消除 |

#### 12.5.2 代码审查提示词模板

```
## 规格合规审查
请审查以下代码是否满足需求规格：
- 需求ID: {需求ID}
- 需求描述: {需求描述}
- 验收条件: {验收条件列表}

审查代码: {代码路径}
请逐项检查验收条件是否满足，如有不满足请指出具体问题。

## 代码质量审查
请审查以下代码的质量：
- 代码路径: {代码路径}
- 测试路径: {测试路径}

请从以下维度审查：
1. 测试覆盖率和质量
2. 代码风格和可读性
3. 类型注解完整性
4. 潜在的性能问题
5. 安全隐患
6. 错误处理完整性
```

### 12.6 常见问题与解决方案

#### 12.6.1 TDD执行困难场景

| 场景 | 解决方案 |
|------|---------|
| 第三方API调用 | 使用unittest.mock或respx进行Mock |
| 数据库事务 | 使用pytest-asyncio + 事务回滚 |
| 异步代码测试 | 使用pytest.mark.asyncio装饰器 |
| 文件系统操作 | 使用tmp_path fixture + 内存文件系统 |
| 定时任务测试 | 使用freezegun冻结时间 |
| Token生成随机性 | 使用固定seed或mock random |

#### 12.6.2 子代理任务分配原则

```
适合子代理的任务：                    不适合子代理的任务：
├── 独立的功能模块开发                  ├── 需要全局架构决策的任务
├── 编写测试用例                        ├── 涉及多个模块紧耦合的修改
├── 编写API路由和schema                 ├── 数据库迁移脚本审查
├── 编写前端页面模板                    └── 安全关键代码的首次实现
└── 编写文档和注释
```

---

## 第十三章 各功能模块Claude Code提示词汇总

> 本章提供每个功能模块的完整Claude Code提示词，复制到Claude Code中即可使用。

### 13.1 提示词使用指南

**使用方法：**
1. 打开VS Code，启动Claude Code
2. 将对应的提示词粘贴到Claude Code输入框
3. Claude Code会自动加载Superpowers框架的对应技能
4. 按照计划逐步执行，每个步骤完成后会自动提交

**注意事项：**
- 提示词中的`{占位符}`需要根据实际情况替换
- 每个模块的执行预计需要2-4小时（取决于复杂度）
- 执行过程中请勿中断，Claude Code会自动处理依赖关系
- 完成后运行`pytest tests/ -v`验证全部通过

---

### 模块M1: PostgreSQL数据库迁移

```markdown
## 任务：将内存数据库迁移至PostgreSQL

### 背景
当前系统使用内存dict存储数据，需要迁移至PostgreSQL 15实现数据持久化。

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能
- 保存到 docs/superpowers/plans/2026-05-19-m1-database-migration.md
- 计划需包含：文件结构、模型定义、迁移脚本、缓存集成、测试策略

**Step 2: TDD开发**
使用 test-driven-development 技能，按以下顺序实现：

1. 安装依赖：asyncpg, sqlalchemy[asyncio], alembic, redis
2. 创建数据库配置（app/config/database.py）
   - PostgreSQL异步连接池（默认20连接）
   - Redis连接
   - 数据库会话管理（async generator）
3. 创建SQLAlchemy模型：
   - MFI模型（mfis表）
   - Customer模型（customers表）- 扩展柬埔寨地址字段
   - Device模型（devices表）- Secret Key加密存储
   - Contract模型（contracts表）
   - Payment模型（payments表）
   - Token模型（tokens表）
   - TokenAuditLog模型（token_audit_log表）
   - User模型（users表）- 密码bcrypt哈希
4. 创建Alembic迁移脚本
   - 初始化迁移（生成所有表）
   - 添加索引（phone_number, serial_number, contract_number）
5. 重写DB层（app/db.py）
   - 保持现有API兼容（get_db, get_customer, save_customer等）
   - 内部实现改为PostgreSQL查询
   - Redis缓存热点数据
6. 运行全部现有测试确保通过（79个测试）

**Step 3: 验证**
- 运行 pytest tests/ -v，全部79个测试通过
- 新增PostgreSQL相关测试（连接池、CRUD、缓存）
- 数据库健康检查端点 /health/db

**Step 4: 提交**
- 完成后执行 git commit -m "M1: PostgreSQL数据库迁移完成，全部测试通过"
```

---

### 模块M2: Bakong支付系统集成

```markdown
## 任务：集成Bakong支付系统

### 背景
集成柬埔寨国家银行Bakong支付系统，支持KH/USD双币种，实现支付到Token发放自动化。

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能
- 保存到 docs/superpowers/plans/2026-05-20-m2-bakong-integration.md

**Step 2: TDD开发**
使用 test-driven-development 技能，按以下顺序实现：

1. 创建Bakong API客户端（app/services/bakong_client.py）
   - HMAC-SHA256签名生成
   - 支付发起（create_payment）
   - 支付查询（query_payment）
   - KHQR码生成（generate_khqr）
   - 日终对账（get_daily_statement）
   - 使用httpx异步HTTP客户端

2. 创建Webhook处理器（app/routers/webhooks.py）
   - POST /webhooks/bakong - 接收支付状态变更
   - 签名验证（防篡改）
   - 幂等处理（使用Redis去重）
   - 支付金额与合同匹配验证
   - 自动触发Token生成
   - 自动触发SMS发送

3. 创建支付服务层（app/services/payment_service.py）
   - process_payment_confirmation() - 处理支付确认
   - verify_payment_amount() - 验证支付金额匹配
   - handle_payment_discrepancy() - 处理金额不匹配
   - generate_repayment_schedule() - 生成还款计划

4. 创建Bakong配置（app/config/bakong.py）
   - API密钥和密钥管理（环境变量）
   - 沙箱/生产环境切换
   - 回调URL配置

5. 创建支付路由（app/routers/payments.py）
   - GET /api/v1/payments - 支付记录查询
   - GET /api/v1/payments/{id} - 支付详情
   - POST /api/v1/payments/{id}/refund - 退款处理
   - GET /api/v1/reconciliation - 对账界面

6. 创建开发测试模拟器
   - MockBakongClient - 模拟Bakong API响应
   - 支持模拟支付成功/失败/回调

**Step 3: 验证**
- 单元测试：Bakong客户端签名生成、支付流程
- 集成测试：Webhook处理、Token自动发放
- 模拟端到端测试：支付→Token→SMS完整流程

**Step 4: 提交**
- git commit -m "M2: Bakong支付系统集成完成，支持Webhook自动处理"
```

---

### 模块M3: SMS网关集成

```markdown
## 任务：集成SMS网关

### 背景
集成柬埔寨本地SMS网关（Cellcard/Smart），实现Token自动发送、还款提醒、逾期通知。

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能
- 保存到 docs/superpowers/plans/2026-05-22-m3-sms-gateway.md

**Step 2: TDD开发**
使用 test-driven-development 技能，按以下顺序实现：

1. 创建SMS网关抽象层（app/services/sms_gateway.py）
   - SMSGateway抽象基类
   - CellcardSMSGateway（SMPP v3.4实现）
   - SmartSMSGateway（备用通道）
   - MockSMSGateway（开发环境模拟）
   - 网关工厂模式（根据环境自动选择）

2. 创建SMS模板引擎（app/services/sms_templates.py）
   - 双语模板支持（英语/高棉语）
   - 模板变量替换（{days}, {token}, {amount}, {due_date}）
   - 模板配置管理（数据库可配置）

3. 预定义SMS模板：
   - token_issued - Token发放通知
   - payment_reminder - 还款提醒（提前3天）
   - overdue_warning_7d - 逾期7天警告
   - overdue_warning_16d - 逾期16天降额通知
   - overdue_lock_31d - 逾期31天锁定通知
   - loan_closed - 贷款结清祝贺

4. 创建SMS服务层（app/services/sms_service.py）
   - send_token_sms() - Token发送
   - send_payment_reminder() - 还款提醒
   - send_overdue_notice() - 逾期通知
   - process_incoming_sms() - 双向SMS处理
   - get_sms_status() - 发送状态查询

5. 创建双向SMS处理器
   - BALANCE关键词 → 返回剩余天数
   - HELP关键词 → 返回客服信息
   - TOKEN关键词 → 重新发送Token

6. 创建Celery定时任务
   - daily_payment_reminder - 每日还款提醒扫描
   - daily_overdue_check - 每日逾期检测
   - weekly_summary - 周汇总报表

7. 创建SMS管理路由（app/routers/sms.py）
   - GET /api/v1/sms/log - 发送记录查询
   - GET /api/v1/sms/templates - 模板管理
   - POST /api/v1/sms/send - 手动发送SMS
   - POST /webhooks/sms/incoming - 接收客户回复

**Step 3: 验证**
- 单元测试：模板渲染、网关Mock发送
- 集成测试：支付成功→Token SMS发送
- 定时任务测试：提醒任务正确触发

**Step 4: 提交**
- git commit -m "M3: SMS网关集成完成，支持双语模板和双向SMS"
```

---

### 模块M4: OpenPAYGO完整实现

```markdown
## 任务：完整实现OpenPAYGO Token标准

### 背景
当前仅支持ADD_TIME基础类型，需要完整实现所有Token类型、自动递减、控制器模拟器。

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能
- 保存到 docs/superpowers/plans/2026-05-25-m4-openpaygo-full.md

**Step 2: TDD开发**
使用 test-driven-development 技能，按以下顺序实现：

1. 升级Token生成服务（app/services/token_service.py）
   - 完整支持5种Token类型：
     * ADD_TIME - 增加天数
     * SET_TIME - 设置天数（用于降额/锁定）
     * DISABLE_PAYG - 永久解锁
     * COUNTER_SYNC - 计数器同步
     * STARTING_CODE - 首次激活码
   - Token序列预生成（Redis队列）
   - Token使用审计日志
   - Token撤销机制

2. 实现remaining_days自动递减（app/tasks/scheduled.py）
   - Celery Beat每日00:00 UTC+7执行
   - 递减逻辑：正常设备每日-1
   - 到期检测：<=3天发送提醒
   - 宽限期管理：0天进入3天宽限期（50%功率）
   - 锁定执行：宽限期结束完全锁定

3. 升级控制器模拟器（controller/simulator.py）
   - PAYGODeviceSimulator类重构
   - 完整状态机实现：
     * 正常状态（100%功率）
     * 降额状态（50%功率，宽限期）
     * 锁定状态（0%功率）
     * 永久解锁（DISABLE_PAYG后）
   - 持久化存储（SQLite文件）
   - Grace period计数器
   - 无效Token尝试限制（5次锁定）

4. 创建批量设备模拟器（controller/batch_simulator.py）
   - BatchDeviceSimulator类
   - 支持注册/注销模拟设备
   - 批量daily_tick执行
   - 自动化测试接口（HTTP API）

5. 创建Token管理路由（app/routers/tokens.py）
   - POST /api/v1/tokens/generate - 生成Token
   - POST /api/v1/tokens/validate - 验证Token
   - POST /api/v1/tokens/revoke - 撤销Token
   - GET /api/v1/tokens/audit - 审计日志查询
   - POST /api/v1/tokens/batch-generate - 批量预生成

6. 创建定时任务路由
   - POST /api/v1/tasks/daily-decrement - 手动触发递减
   - GET /api/v1/tasks/schedule - 查看定时任务状态

**Step 3: 验证**
- 单元测试：每种Token类型生成和验证
- 集成测试：Token全流程（生成→发送→输入→验证）
- 定时任务测试：递减逻辑、宽限期、锁定
- 模拟器测试：状态机转换、持久化

**Step 4: 提交**
- git commit -m "M4: OpenPAYGO完整实现，支持全Token类型和自动递减"
```

---

### 模块M5: 安全架构升级

```markdown
## 任务：安全架构升级

### 背景
当前密码明文存储、HTTP传输，需要全面升级安全架构。

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能
- 保存到 docs/superpowers/plans/2026-05-28-m5-security-upgrade.md

**Step 2: TDD开发**
使用 test-driven-development 技能，按以下顺序实现：

1. 密码安全（app/core/security.py）
   - bcrypt哈希（rounds=12）
   - 密码强度验证（最少8位，含大小写+数字）
   - 历史密码检查（防止重复使用）

2. JWT认证（app/core/auth.py）
   - Access Token生成（15分钟有效期）
   - Refresh Token生成（7天有效期）
   - Token刷新机制
   - Token吊销机制（Redis黑名单）

3. 设备密钥加密（app/core/encryption.py）
   - AES-256加密（Fernet）
   - 主密钥环境变量管理
   - 密钥轮换支持

4. 安全中间件（app/middleware/security.py）
   - HTTPS强制（HSTS）
   - 安全Headers（CSP/X-Frame/XSS）
   - API速率限制（100次/分钟）
   - CORS配置

5. 审计日志（app/services/audit_service.py）
   - 操作审计（用户/时间/IP/操作/结果）
   - Token审计（生成/发送/使用）
   - 安全事件审计（登录/密码修改/权限变更）
   - 审计日志不可篡改（独立表+WAL）

6. 升级认证路由（app/routers/auth.py）
   - POST /api/auth/login - 登录（JWT）
   - POST /api/auth/refresh - Token刷新
   - POST /api/auth/logout - 注销（Token吊销）
   - POST /api/auth/change-password - 修改密码
   - GET /api/auth/me - 当前用户信息

**Step 3: 验证**
- 单元测试：密码哈希、JWT生成/验证、加密解密
- 集成测试：登录流程、Token刷新、权限控制
- 安全测试：SQL注入、XSS、暴力破解防护

**Step 4: 提交**
- git commit -m "M5: 安全架构升级，JWT认证+AES加密+审计日志"
```

---

### 模块M6: 客户360视图

```markdown
## 任务：客户360视图与MFI管理

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能
- 保存到 docs/superpowers/plans/2026-06-02-m6-customer-360.md

**Step 2: TDD开发**
使用 test-driven-development 技能，按以下顺序实现：

1. MFI管理（app/routers/mfis.py）
   - MFI的CRUD操作
   - MFI编码唯一性验证
   - MFI统计信息

2. 客户模型扩展
   - 柬埔寨地址结构（省/社区/村）
   - GPS坐标（纬度/经度）
   - 信用评分字段
   - MFI关联

3. 客户360视图API（app/routers/customers.py升级）
   - GET /api/v1/customers/{id}/360 - 完整视图
   - 包含：基本信息、合同列表、设备状态、支付历史、Token历史、SMS记录

4. 客户管理前端模板
   - 客户列表页（搜索/筛选/分页）
   - 客户详情页（360视图标签页）
   - 客户创建/编辑表单
   - GPS地图展示

5. 客户导入功能
   - CSV模板下载
   - CSV批量导入（验证+去重）
   - 导入结果报告

**Step 3: 验证**
- API测试：360视图数据完整性
- 前端测试：页面渲染正确

**Step 4: 提交**
- git commit -m "M6: 客户360视图与MFI管理"
```

---

### 模块M7: 合同与还款计划引擎

```markdown
## 任务：合同管理与还款计划引擎

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能

**Step 2: TDD开发**
使用 test-driven-development 技能：

1. 合同模型扩展
   - 贷款产品配置（利率/期限/首付比例）
   - 合同状态机（pending→approved→active→closed）
   - 还款计划存储

2. 还款计划引擎（app/services/repayment_engine.py）
   - 等额本息计算
   - 还款计划生成（按月）
   - 提前还款重新计算
   - 逾期利息计算

3. 合同管理API（app/routers/contracts.py）
   - 合同CRUD
   - 还款计划查询
   - 合同审批流程
   - KHQR码展示

4. 合同PDF生成
   - 双语合同模板
   - 电子签名预留

**Step 3: 验证**
- 单元测试：还款计算准确性
- 集成测试：合同创建→还款计划生成

**Step 4: 提交**
- git commit -m "M7: 合同管理与还款计划引擎"
```

---

### 模块M8: 逾期预警与自动锁定

```markdown
## 任务：逾期预警与自动锁定系统

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能

**Step 2: TDD开发**
使用 test-driven-development 技能：

1. 逾期检测引擎（app/services/overdue_engine.py）
   - 每日逾期扫描
   - 逾期天数计算
   - 风险等级评估

2. 分级预警执行器
   - 阶段1（1-7天）：SMS提醒
   - 阶段2（8-15天）：高风险标记
   - 阶段3（16-30天）：设备降额Token
   - 阶段4（31-60天）：设备锁定Token
   - 阶段5（60+天）：回收工单

3. 定时任务
   - daily_overdue_scan - 每日逾期扫描
   - auto_lock_executor - 自动锁定执行

4. 逾期管理界面
   - 逾期客户清单
   - 预警规则配置
   - 批量操作

**Step 3: 验证**
- 单元测试：逾期天数计算、分级判断
- 集成测试：逾期→Token生成→设备状态变更

**Step 4: 提交**
- git commit -m "M8: 逾期预警与自动锁定系统"
```

---

### 模块M9: 运营仪表盘

```markdown
## 任务：运营仪表盘与报表系统

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能

**Step 2: TDD开发**
使用 test-driven-development 技能：

1. 仪表盘API（app/routers/dashboard.py）
   - GET /api/v1/dashboard/summary - 业务概览
   - GET /api/v1/dashboard/revenue-trend - 收入趋势
   - GET /api/v1/dashboard/device-status - 设备状态分布
   - GET /api/v1/dashboard/overdue-heatmap - 逾期热力图

2. 报表API（app/routers/reports.py）
   - GET /api/v1/reports/revenue - 收入报表
   - GET /api/v1/reports/overdue - 逾期分析
   - GET /api/v1/reports/gogla - GOGLA KPI

3. 前端仪表盘模板
   - 概览卡片（Chart.js）
   - 趋势图（折线图）
   - 分布图（饼图）
   - 地图（Leaflet.js）

4. 报表导出
   - PDF生成
   - Excel导出

**Step 3: 验证**
- API测试：数据准确性
- 前端测试：图表渲染

**Step 4: 提交**
- git commit -m "M9: 运营仪表盘与报表系统"
```

---

### 模块M10: RBAC权限系统

```markdown
## 任务：RBAC权限与多租户隔离

### 执行要求

**Step 1: 编写实施计划**
- 使用 writing-plans 技能

**Step 2: TDD开发**
使用 test-driven-development 技能：

1. RBAC模型
   - Role模型（超级管理员/MFI管理员/运营/财务/客服/技术员）
   - Permission模型（细粒度权限）
   - Role-Permission关联

2. 多租户隔离
   - MFI数据范围过滤
   - API级别租户隔离

3. 用户管理
   - 用户CRUD
   - 角色分配
   - 操作日志

4. 权限中间件
   - API路由权限检查
   - 数据范围过滤

**Step 3: 验证**
- 单元测试：权限判断
- 集成测试：多租户数据隔离

**Step 4: 提交**
- git commit -m "M10: RBAC权限与多租户隔离"
```

---

## 附录A 数据库完整Schema设计

```sql
-- 完整数据库Schema（PostgreSQL 15）

-- 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- MFI表
CREATE TABLE mfis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    contact_person VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    address TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mfi_id UUID REFERENCES mfis(id),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hash
    role VARCHAR(30) NOT NULL DEFAULT 'operator',
    status VARCHAR(20) DEFAULT 'active',
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 客户表
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mfi_id UUID NOT NULL REFERENCES mfis(id),
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    id_card_number VARCHAR(50),
    address TEXT,
    province VARCHAR(50),
    commune VARCHAR(50),
    village VARCHAR(50),
    gps_latitude DECIMAL(10,8),
    gps_longitude DECIMAL(11,8),
    credit_score INTEGER DEFAULT 50,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(mfi_id, phone_number)
);

-- 设备表
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    serial_number VARCHAR(50) NOT NULL UNIQUE,
    model VARCHAR(50) NOT NULL,
    capacity_kw DECIMAL(5,2),
    secret_key BYTEA NOT NULL,
    token_counter INTEGER DEFAULT 1,
    starting_code VARCHAR(15),
    payg_enabled BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'installed',
    customer_id UUID REFERENCES customers(id),
    contract_id UUID,
    last_online_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 合同表
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_number VARCHAR(30) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    mfi_id UUID NOT NULL REFERENCES mfis(id),
    device_id UUID,
    total_amount DECIMAL(12,2) NOT NULL,
    down_payment DECIMAL(12,2) NOT NULL,
    loan_amount DECIMAL(12,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    term_months INTEGER NOT NULL,
    monthly_payment DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    remaining_days INTEGER DEFAULT 0,
    grace_period_end DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 还款计划表
CREATE TABLE repayment_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id),
    installment_number INTEGER NOT NULL,
    due_date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    principal DECIMAL(10,2) NOT NULL,
    interest DECIMAL(10,2) NOT NULL,
    remaining_balance DECIMAL(12,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    paid_at TIMESTAMP,
    paid_amount DECIMAL(10,2),
    UNIQUE(contract_id, installment_number)
);

-- 支付记录表
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    bakong_tx_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    paid_at TIMESTAMP,
    token_generated BOOLEAN DEFAULT FALSE,
    token_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Token记录表
CREATE TABLE tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id),
    contract_id UUID NOT NULL,
    token_value VARCHAR(15) NOT NULL,
    token_type VARCHAR(20) NOT NULL,
    days_added INTEGER DEFAULT 0,
    counter_used INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'generated',
    generated_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    used_at TIMESTAMP,
    sms_message_id VARCHAR(100)
);

-- Token审计日志表
CREATE TABLE token_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL,
    token_type VARCHAR(20) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    counter INTEGER NOT NULL,
    days INTEGER,
    generated_at TIMESTAMP DEFAULT NOW(),
    generated_by VARCHAR(50) NOT NULL
);

-- SMS发送记录表
CREATE TABLE sms_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    template_name VARCHAR(50),
    message_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 审计日志表
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引创建
CREATE INDEX idx_customers_phone ON customers(phone_number);
CREATE INDEX idx_customers_mfi ON customers(mfi_id);
CREATE INDEX idx_devices_serial ON devices(serial_number);
CREATE INDEX idx_devices_customer ON devices(customer_id);
CREATE INDEX idx_contracts_number ON contracts(contract_number);
CREATE INDEX idx_contracts_customer ON contracts(customer_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_payments_contract ON payments(contract_id);
CREATE INDEX idx_payments_bakong ON payments(bakong_tx_id);
CREATE INDEX idx_tokens_device ON tokens(device_id);
CREATE INDEX idx_sms_phone ON sms_log(phone_number);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

---

## 附录B Bakong API对接规范

### B.1 API认证

```python
# HMAC-SHA256签名生成
def generate_signature(api_secret: str, payload: str, timestamp: str) -> str:
    message = f"{timestamp}.{payload}"
    return hmac.new(
        api_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

# 请求Headers
headers = {
    "Content-Type": "application/json",
    "X-API-Key": api_key,
    "X-Timestamp": timestamp,
    "X-Signature": signature
}
```

### B.2 核心API端点

| 端点 | 方法 | 请求体 | 响应 |
|------|------|--------|------|
| `/api/v1/payments` | POST | `{amount, currency, from_account, to_account, description, external_reference, callback_url}` | `{transaction_id, status, amount, created_at}` |
| `/api/v1/payments/{tx_id}` | GET | - | `{transaction_id, status, amount, paid_at}` |
| `/api/v1/khqr` | POST | `{amount, currency, merchant_name, merchant_city, bill_number, description}` | `{qr_data_base64, expires_at}` |
| `/api/v1/statements` | GET | `?date=YYYY-MM-DD` | `{transactions: [...]}` |

### B.3 Webhook Payload

```json
{
  "event": "payment.completed",
  "transaction_id": "TXN-20260519-001",
  "external_reference": "PAYGO-CONTRACT-12345",
  "amount": 150.00,
  "currency": "USD",
  "from_account": "+855123456789",
  "to_account": "SOLAR-COMPANY-001",
  "paid_at": "2026-05-19T14:30:00+07:00",
  "signature": "sha256=..."
}
```

---

## 附录C SMS网关接口规范

### C.1 SMPP协议配置

```python
# SMPP连接配置
SMPP_CONFIG = {
    "host": "smpp.cellcard.com.kh",
    "port": 2775,
    "system_id": "your_system_id",
    "password": "your_password",
    "system_type": "",
    "source_addr": "XHZTech",  # 发送方ID
    "use_ssl": True,
    "bind_timeout": 30,
    "enquire_link_interval": 60
}
```

### C.2 HTTP API接口

```python
# HTTP API发送
async def send_sms_http(phone: str, message: str) -> str:
    payload = {
        "to": phone,
        "message": message,
        "from": "XHZTech",
        "unicode": True,  # 支持高棉语Unicode
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.cellcard.com.kh/sms/send",
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        return response.json()["message_id"]
```

### C.3 双向SMS处理

```python
# 接收客户回复SMS
@router.post("/webhooks/sms/incoming")
async def receive_sms(from_number: str, message: str):
    message = message.upper().strip()
    
    if message == "BALANCE":
        return await handle_balance_query(from_number)
    elif message == "HELP":
        return await handle_help_request(from_number)
    elif message == "TOKEN":
        return await handle_token_resend(from_number)
    else:
        return await handle_unknown_message(from_number, message)
```

---

## 附录D 测试策略与用例清单

### D.1 测试分层

```
tests/
├── unit/                           # 单元测试（无外部依赖）
│   ├── test_models.py              # 模型测试
│   ├── test_schemas.py             # Schema验证测试
│   ├── test_token_generator.py     # Token生成测试
│   ├── test_repayment_engine.py    # 还款计算测试
│   └── test_security.py            # 安全函数测试
├── integration/                    # 集成测试（含数据库）
│   ├── test_database.py            # 数据库操作测试
│   ├── test_bakong_client.py       # Bakong客户端测试
│   ├── test_sms_gateway.py         # SMS网关测试
│   └── test_token_flow.py          # Token完整流程测试
├── api/                            # API测试
│   ├── test_auth_api.py            # 认证API
│   ├── test_customers_api.py       # 客户API
│   ├── test_contracts_api.py       # 合同API
│   ├── test_payments_api.py        # 支付API
│   ├── test_tokens_api.py          # Token API
│   └── test_devices_api.py         # 设备API
├── e2e/                            # 端到端测试
│   ├── test_full_payment_flow.py   # 完整支付流程
│   ├── test_overdue_workflow.py    # 逾期处理流程
│   └── test_device_lifecycle.py    # 设备生命周期
└── conftest.py                     # 共享fixture
```

### D.2 关键测试用例

| 模块 | 测试用例 | 类型 | 优先级 |
|------|---------|------|--------|
| M1 | test_customer_create_and_retrieve | 集成 | P0 |
| M1 | test_device_secret_key_encryption | 单元 | P0 |
| M1 | test_database_connection_pool | 集成 | P0 |
| M2 | test_bakong_payment_webhook_processing | 集成 | P0 |
| M2 | test_payment_amount_mismatch_handling | 单元 | P0 |
| M2 | test_khqr_generation | 单元 | P1 |
| M3 | test_token_sms_template_rendering | 单元 | P0 |
| M3 | test_sms_gateway_mock_send | 集成 | P0 |
| M3 | test_daily_payment_reminder_task | 集成 | P1 |
| M4 | test_add_time_token_generation | 单元 | P0 |
| M4 | test_disable_payg_token_generation | 单元 | P0 |
| M4 | test_daily_remaining_days_decrement | 集成 | P0 |
| M4 | test_grace_period_expiration_lock | 集成 | P0 |
| M4 | test_controller_full_token_validation | 单元 | P0 |
| M5 | test_password_bcrypt_hashing | 单元 | P0 |
| M5 | test_jwt_token_generation_and_verification | 单元 | P0 |
| M5 | test_api_rate_limiting | API | P1 |
| M8 | test_overdue_tier1_sms_reminder | 集成 | P1 |
| M8 | test_overdue_tier3_derating_token | 集成 | P1 |
| E2E | test_complete_payment_to_unlock_flow | E2E | P0 |

---

## 附录E 参考资料与开源组件

### E.1 开源项目

| 项目 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| [paygo-platform](https://github.com/zhizhengqin/paygo-platform) | v0.6.3 | 基础原型 | MIT |
| [OpenPAYGO-python](https://github.com/EnAccess/OpenPAYGO-python) | v2.1 | Token生成 | MIT |
| [OpenPAYGO-HW](https://github.com/EnAccess/OpenPAYGO-HW) | v2.1 | 设备端参考 | MIT |
| [FastAPI](https://fastapi.tiangolo.com/) | v0.110 | Web框架 | MIT |
| [SQLAlchemy](https://www.sqlalchemy.org/) | v2.0 | ORM | MIT |
| [Alembic](https://alembic.sqlalchemy.org/) | v1.13 | 数据库迁移 | MIT |
| [Celery](https://docs.celeryq.dev/) | v5.3 | 定时任务 | BSD |
| [Superpowers](https://github.com/obra/superpowers) | v5.1 | 开发框架 | MIT |

### E.2 行业标准

| 标准 | 说明 |
|------|------|
| OpenPAYGO Token | EnAccess基金会开源标准 |
| GOGLA KPI | 全球离网照明协会标准指标 |
| Bakong API | 柬埔寨国家银行数字支付API |
| KHQR | 柬埔寨统一二维码标准 |
| SMPP v3.4 | 短消息点对点协议 |

### E.3 技术文档

- [OpenPAYGO Token Specification v2.1](https://enaccess.org/openpaygo-token/)
- [Bakong Developer Documentation](https://api.bakong.gov.kh/docs)
- [Superpowers Framework Documentation](https://github.com/obra/superpowers/tree/main/docs)

---

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | V2.0 |
| 最后更新 | 2026-05-19 |
| 编制人 | AI辅助编制 |
| 审核人 | 待审核 |
| 状态 | 待审批 |
| 下次评审 | 2026-06-19 |

**修订记录：**

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| V1.0 | 2026-05-12 | 初始技术架构方案 | 技术团队 |
| V2.0 | 2026-05-19 | 运营级功能需求分析与Superpowers升级计划 | AI辅助 |

---

*本计划书基于柬埔寨太阳能PAYGO平台技术架构方案V1.0、CLAUD.md原型文档，以及Angaza/PaygOps行业标杆平台功能分析编制。所有功能模块均提供完整的Claude Code提示词，可直接用于VS Code + Claude Code + Superpowers框架进行开发。*
