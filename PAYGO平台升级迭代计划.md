# PAYGO 平台运营后台升级迭代计划

**编制日期**：2026-05-20
**最后更新**：2026-05-20
**当前版本**：Phase 0 + Phase 1 已完成（165 tests）
**目标**：按业务闭环深度，分 9 个阶段逐步补全 FR-OPS-001 ~ FR-OPS-008 八大模块，同时补齐架构安全短板

---

## 架构设计说明书 vs 当前项目对比

### 总体对比

| 架构层 | 设计说明书（目标架构） | 当前原型实现 | 原型阶段建议 |
|:---|:---|:---|:---|
| **客户端层** | React 18 (Web) + Flutter (Mobile) + 响应式 Web (客户门户) | Jinja2 模板 + 原生 CSS/JS | 保持现有 Jinja2，原型阶段够用；React 迁移待真实部署前 |
| **接入层** | AWS ALB + WAF + Kong API Gateway / JWT 验证 + 限流 + 路由 | 无网关，FastAPI 直连 | Phase 0 补 JWT 认证；限流用 Redis 滑动窗口；ALB/WAF/Kong 属云部署，原型跳过 |
| **应用服务层** | 6 微服务 (Token/Device/Payment/MFI/Notification/OTA-Report) | 单体 FastAPI，routers 按域拆分 | 保持单体，按 router 做域隔离即可；微服务拆分是生产部署的事 |
| **消息总线层** | Kafka (AWS MSK) | 无（同步函数调用） | 原型阶段不需要；用 FastAPI BackgroundTasks 替代异步任务 |
| **数据层** | PostgreSQL 15 + Redis + EMQX + S3 + OpenSearch + Vault/KMS | PostgreSQL 15 + Redis 8 | ✅ PG + Redis 已就绪；EMQX/MQTT 需硬件配合跳过；S3/OpenSearch/Vault 属云服务跳过 |
| **部署层** | AWS EKS + VPC + Multi-AZ + Terraform + ArgoCD | Docker Compose（本地） | ✅ Docker Compose 适用于原型；AWS 部署为生产目标 |
| **安全层** | JWT + RBAC + bcrypt + AES-256-GCM + mTLS + WAF + 审计日志 | Session cookie + 明文密码 + 明文密钥 + 无 RBAC | Phase 0 补 bcrypt + 密钥加密 + API 限流；Phase 8 补 RBAC + 审计日志 |
| **可观测性** | Prometheus + Grafana + OpenSearch + Jaeger | 无 | 原型跳过；结构化日志在 Phase 4 补 |

### 逐项详细对比

#### 1. 安全架构（差距最大，风险最高）

| 安全机制 | 设计说明书要求 | 当前实现 | 差距评估 |
|:---|:---|:---|:---|
| 密码存储 | bcrypt 哈希 | **明文比较** (`settings.ADMIN_PASSWORD`) | 高危，需立即修复 |
| Secret Key 存储 | AWS KMS + AES-256-GCM 加密 | **明文存储** (`customers.secret_key`) | 高危，原型可降级为 bcrypt 哈希 |
| Token 存储 | bcrypt 哈希，原始 Token 仅 SMS 瞬间 | **明文存储** (`tokens.token`) | 中危，原型需展示 Token 可暂存明文 |
| API 认证 | JWT (RS256) 15min + Refresh 7d | Session cookie (Redis) | 中危，Session 可用但 JWT 更适合 API |
| 传输加密 | TLS 1.3 全站 + mTLS 设备端 | HTTP 明文 | 低危（本地开发环境） |
| 权限控制 | RBAC 5 角色 + 接口级注解 | 单一管理员，无角色区分 | 中危，Phase 8 补齐 |
| 审计日志 | 全量操作日志，不可篡改 | **无** | 中危，Phase 4/8 逐步补齐 |
| 限流防爆破 | Redis 滑动窗口 100次/min | **无** | 中危，Phase 0 补齐 |

#### 2. 应用架构（差距可控）

| 架构维度 | 设计说明书 | 当前实现 | 差距评估 |
|:---|:---|:---|:---|
| 服务拆分 | 6 微服务，独立 DB | 单体应用，单 DB | 原型可接受，按 router 隔离域 |
| API 版本化 | `/api/v1/` 前缀 | `/api/` 无版本号 | Phase 8 统一加 `/api/v1/` |
| 异步消息 | Kafka 事件驱动 | 同步调用 + BackgroundTasks | 原型可接受，BackgroundTasks 够用 |
| 数据库分库 | 每个微服务独立 DB | 所有表共用一个 DB | 原型可接受，用 Schema 命名区分 |
| 缓存策略 | 设备状态/Token序列/客户/汇率/会话 | 仅 Session 缓存 | Phase 5 补业务缓存 |

#### 3. 数据模型（持续演进中）

| 实体 | 设计说明书字段数 | 当前实现 | 补齐阶段 |
|:---|:---|:---|:---|
| Device | 18 个字段（含 GPS/IMEI/固件版本等） | 9 个字段（device_states 表） | Phase 3 客户表扩展 |
| Token | 审计字段齐全（IP/UA/关联支付） | 基础字段 | Phase 2 Token 模块 |
| Customer | 含 MFI 关联/信用评分/身份证 | 基础字段 | Phase 3 客户 360 |
| Contract | 含 MFI 合同 ID 映射 | 已基本对齐 | Phase 1 补完 |
| Repayment | 独立还款记录表（transaction_id 幂等） | 仅有还款计划表 | Phase 1 新增 |
| Alert | 告警规则 + 告警记录 + 操作日志 | **无** | Phase 4 全新建表 |
| MFI | MFI 机构 + 支行 | **无** | Phase 3 全新建表 |
| User/RBAC | 用户 + 角色 + 权限 | **无** | Phase 8 全新建表 |

#### 4. 原型阶段明确不实施的架构组件

| 组件 | 设计说明书中的定位 | 原型不实施的原因 |
|:---|:---|:---|
| EMQX MQTT Broker | 设备双向通信核心 | 需要物理硬件控制板配合，原型用 DB 模拟设备状态 |
| Kafka (AWS MSK) | 服务间异步解耦，事件溯源 | 单体架构无需消息队列，用 FastAPI BackgroundTasks 替代 |
| AWS EKS + K8s | 容器编排，HPA 自动伸缩 | 本地 Docker Compose 已满足原型需要 |
| Kong API Gateway | 流量入口，JWT 验证，限流 | 原型在 FastAPI 中间件层实现限流和认证即可 |
| HashiCorp Vault | 动态凭据，密钥加密 | 原型用 bcrypt 哈希 + 环境变量管理密钥 |
| AWS KMS | 数据加密密钥管理 | 原型用 Python cryptography 库本地加解密 |
| Prometheus + Grafana | 指标监控 + 可视化 | 原型阶段不需要，生产部署前接入 |
| OpenSearch | 日志全文检索 | 原型阶段结构化日志写入 PostgreSQL 即可 |
| Jaeger | 分布式链路追踪 | 微服务拆分后才需要，单体应用不需要 |
| Flutter Mobile App | 安装技师/MFI Loan Officer 终端 | 超出运营后台原型范围，仅 Web 端 |
| S3 对象存储 | 照片/固件/归档 | 原型阶段文件存本地或跳过 |
| Terraform + ArgoCD | IaC + GitOps | 原型不需要基础设施即代码 |

---

## 总体路线

```
Phase 0 (新增)      Phase 1 (当前收尾)   Phase 2          Phase 3          Phase 4
安全基础升级    →   合同管理补完     →   Token 管理独立  →  客户360视图   →  告警中心
bcrypt+JWT+限流     还款跟踪闭环          Token全生命周期     单客户聚合视图   逾期/故障自动预警
    │                    │                    │                  │                │
    └────────────────────┴────────────────────┴──────────────────┴────────────────┘
                                          │
                                Phase 5   ▼   Phase 6      Phase 7      Phase 8
                               仪表盘增强  →  设备地图   →  报表中心  →  系统设置
```

## 各阶段模拟边界

| 集成点 | 模拟方式 | 真实对接条件 |
|:---|:---|:---|
| Bakong 支付 | 页面"模拟支付"按钮 + 手动确认到账 | 获取 Bakong API 权限后接入 KHQR + Webhook |
| SMS 网关 | 页面弹窗展示短信内容 + 数据库记录 | 对接 Cellcard/Smart SMPP 网关后真实发送 |
| 设备 MQTT 通信 | 数据库模拟设备状态变更 + 手动录入遥测 | 硬件控制板就绪后接入 EMQX Broker |
| MFI CBS 同步 | 管理后台手动录入 / 种子数据模拟 | MFI 开放 API 后接入适配器 |

---

## Phase 0：安全基础升级（新增，优先执行） ✅ 已完成 2026-05-20

**目标**：修复当前高危安全缺口，为后续模块打下安全基础。对应架构设计说明书第 7 章"安全架构"的最基本要求。

**背景**：对比架构设计说明书后发现，当前原型存在 3 个高危安全缺口——密码明文比较、设备密钥明文存储、无 API 限流。这些是架构设计的底线要求，应在业务功能之前修复。

### 需要实现

| 编号 | 功能 | 说明 | 对应架构要求 |
|:---|:---|:---|:---|
| 0.1 | 密码 bcrypt 哈希 | 管理员密码使用 bcrypt 哈希存储，废弃明文比较。首次启动时自动哈希默认密码 | NFR-SEC-003 API 认证 |
| 0.2 | 设备密钥哈希存储 | `customers.secret_key` 使用 bcrypt 哈希存储。Token 生成时传入原始密钥（内存中），验证后不持久化原始值 | NFR-SEC-001 Secret Key 加密 |
| 0.3 | API 限流中间件 | Redis 滑动窗口限流：登录接口 10次/min/IP，API 接口 100次/min/IP | NFR-SEC-005 防暴力破解 |
| 0.4 | 请求日志中间件 | 记录每个 API 请求：路径、方法、响应状态码、耗时、IP | NFR-SEC-006 操作审计日志（基础版） |
| 0.5 | 登录失败锁定 | 连续 5 次登录失败锁定账号 15 分钟（Redis 计数） | NFR-SEC-005 防暴力破解 |

### 安全对比（修复前后）

| 安全项 | 修复前 | 修复后 |
|:---|:---|:---|
| 密码存储 | `settings.ADMIN_PASSWORD` 明文比较 | bcrypt 哈希 + 常量时间比较 |
| 设备密钥 | `customers.secret_key` 明文存储 | bcrypt 哈希存储，仅在 Token 生成时传入明文 |
| 登录保护 | 无限制 | 5 次失败锁定 15 分钟 |
| API 调用 | 无限制 | 100 次/min/IP 限流 |
| 请求追踪 | 无 | 路径/状态码/耗时/IP 日志 |

### 数据模型变更

- `customers` 表：`secret_key` 字段改为存储 bcrypt 哈希值（VARCHAR(255)）
- 新增 `api_request_logs` 表（或使用 Python logging + 文件）

### 测试预期

- 新增：密码哈希验证、密钥哈希、限流中间件、登录锁定、请求日志，预计 +10 tests
- 累计测试数：~139

### 实际完成

| 项目 | 计划 | 实际 |
|:---|:---|:---|
| 新增测试 | +10 | +10 (test_security.py: 10, test_auth.py: +2, test_middleware.py: +2, test_store.py: +3) |
| 累计测试 | ~139 | 157 |
| 新增文件 | — | app/security.py, app/middleware.py, tests/test_security.py, tests/test_middleware.py |
| 修改文件 | — | app/settings.py, app/routers/auth.py, app/models.py, app/store.py, app/main.py, tests/conftest.py, tests/test_auth.py, tests/test_store.py |
| 关键差异 | — | Fernet 替换 bcrypt 作为密钥加密方案（需可逆解密生成 Token）；增加 RATE_LIMIT_ENABLED 环境变量用于测试隔离 |

---

## Phase 1：合同管理补完（当前 M7 收尾） ✅ 已完成 2026-05-20

**目标**：真正走通「签合同 → 按期还款 → Token 下发 → 逾期锁定」的完整闭环

**导航 Tab**：「合同管理」（已有，增强）

### 当前已有

- 合同 CRUD + 审批（draft → active）
- 等额本息还款计划自动生成（calc_amortization）
- 贷款产品 5 档配置（6kW~30kW）
- 合同状态流转：draft / approved / active / overdue / closed / recovered

### 需要补充

| 编号 | 功能 | 说明 |
|:---|:---|:---|
| 1.1 | 按期还款标记 | 还款计划表中每期可标记为"已还款"，自动关联 Token 生成 |
| 1.2 | 合同关联模拟支付 | 选择合同 → 选择还款期数 → 模拟支付 → 自动生成 ADD_TIME Token → SMS 模拟下发 |
| 1.3 | 逾期自动检测 | 后台任务检查还款到期未付 → 合同标记 overdue → 设备自动锁定（SET_TIME 0） |
| 1.4 | 提前结清 | 合同状态 → closed → 自动生成 DISABLE_PAYG Token → 永久解锁设备 |
| 1.5 | 还款计划可视化 | 合同详情中还款进度条形图（Chart.js），已还/待还/逾期三期对比 |

### 闭环验证路径

> 创建客户 → 创建合同(选贷款产品) → 审批通过(生成还款计划) → 模拟第1期还款 → Token 生成 + SMS 下发 → 客户详情显示新 Token
> → 跳过第2期还款 → 逾期检测触发 → 设备自动锁定 → 补缴欠款 → 恢复解锁

### 数据模型变更

- `repayment_schedules` 表：`status` 字段已支持 pending/paid/overdue，无需变更
- `tokens` 表：新增 `contract_id` 外键关联合同（可选）
- 新增 `repayment_records` 表（还款记录，关联 schedules + tokens，对齐架构设计 7.2.5）

### 测试预期

- 新增：还款标记、逾期检测、结清逻辑，预计 +15 tests
- 累计测试数：~154

### 实际完成

| 项目 | 计划 | 实际 |
|:---|:---|:---|
| 新增测试 | +15 | +8 (test_contract_models.py: +1, test_contract_store.py: +4, test_contracts_api.py: +3) |
| 累计测试 | ~154 | 165 |
| 新增数据模型 | repayment_records 表 + tokens.contract_id FK | 一致 |
| 新增 store 函数 | mark_schedule_paid / check_overdue_schedules / settle_contract | 一致 |
| 新增 API | POST pay / POST check-overdue / POST settle | 一致 |
| UI 增强 | 还款进度条 + 还款/结清按钮 + 逾期检测按钮 | 一致 |
| 关键差异 | — | 还款标记走合同关联支付（从合同选期数还款），保留了原有客户详情里的独立模拟支付入口 |

---

## Phase 2：Token 管理独立模块 ✅ 已完成 2026-05-20

**目标**：Token 从"客户详情附带功能"升级为独立管理模块

**导航 Tab**：新增「Token 管理」

### 需要实现

| 编号 | 功能 | 说明 |
|:---|:---|:---|
| 2.1 | Token 列表页 | 按设备/客户/时间/类型筛选，分页展示，显示使用状态（UNUSED / USED / SUPERSEDED） |
| 2.2 | Token 统计卡片 | 今日生成数 / 本月生成数 / 使用率 / 补发率（4 KPI 卡片） |
| 2.3 | 批量生成 | 选择设备范围 + Token 类型(ADD_TIME/SET_TIME/DISABLE_PAYG) + 天数 → 异步生成（BackgroundTasks）→ 结果列表 |
| 2.4 | 手动补发 | 查询原 Token → 验证未被使用 → 生成新 Token(Counter+1) → 标记原 Token 为 SUPERSEDED → SMS 重发 |
| 2.5 | Token 作废 | 运营主管权限，作废指定 Token（标记 SUPERSEDED），填写原因 |
| 2.6 | Token 详情弹窗 | 展示：Token 值、类型、天数、生成时间/人、关联合同、使用状态、关联还款记录 |

### 闭环验证路径

> Phase 1 产生的 Token 全部出现在 Token 列表 → 可按设备查询某客户完整 Token 历史
> → Token 丢失时运营专员申请补发 → 主管审批 → 原 Token 作废 → 新 Token 生成 + SMS 重发
> → 非法获知的 Token 可被主管作废

### 数据模型变更

- `tokens` 表 `status` 字段：新增 UNUSED / USED / SUPERSEDED 枚举（对齐架构设计 7.2.2 token_audit_log 的 status 字段）
- `tokens` 表新增：`superseded_by`（指向替换 Token）、`voided_at`、`voided_by`、`void_reason`
- `tokens` 表新增审计字段（对齐架构设计）：`ip_address`、`user_agent`

### 测试预期

- 新增：Token 列表筛选、批量生成、补发逻辑、作废逻辑，预计 +12 tests
- 累计测试数：~166

### 实际完成

| 项目 | 计划 | 实际 |
|:---|:---|:---|
| 新增测试 | +12 | +13 (test_store.py: +7, test_tokens_api.py: +6) |
| 累计测试 | ~166 | 178 |
| Token 模型字段 | status/superseded/void/audit (7 字段) | 一致 |
| 新增 store 函数 | get_tokens_filtered/get_token_stats/get_token_detail/reissue_token/void_token | 一致（未实现批量生成 batch_generate_tokens，UI 阶段暂不需要） |
| 新增 API | GET stats/GET list/GET detail/POST reissue/POST void | 一致 |
| 新增导航 Tab | Token 管理 ✅ | 一致 |
| 关键差异 | — | 从 customers.py 移除了旧的 `/api/tokens` 端点避免路由冲突；`_token_to_dict` 扩展了 5 个新字段 |

---

## Phase 3：客户 360 视图 ✅ 已完成 2026-05-20

**目标**：客户详情从简单信息卡升级为一站式 360 度聚合视图

**导航 Tab**：「客户管理」（增强）

### 当前已有

- 客户列表 + 详情卡片
- 基本信息：姓名、电话、设备编号、密钥、Token 计数、状态、创建日期
- 模拟支付按钮

### 需要实现

| 编号 | 功能 | 说明 |
|:---|:---|:---|
| 3.1 | 客户信息增强 | 新增字段：地址（高棉语/英文）、GPS 经纬度、身份证号、MFI 所属机构（对齐架构设计 7.2.3 customers 表） |
| 3.2 | 合同聚合卡片 | 该客户的所有合同列表（带状态标签），点击跳转合同详情 |
| 3.3 | 还款日历 | 当月/近3月还款状态可视化（日历热力图：绿色=已还，红色=逾期，灰色=待还） |
| 3.4 | Token 使用时间线 | 垂直时间线展示该客户所有 Token 的生成/使用/作废 |
| 3.5 | 告警关联列表 | 该客户相关的所有告警记录（Phase 4 实现告警后此处自动有数据） |
| 3.6 | 客户标签 | 手动打标签（VIP / 高风险 / 投诉频繁 / 新客户），支持按标签筛选 |
| 3.7 | 列表筛选增强 | 按姓名搜索 / 电话搜索 / MFI 筛选 / 逾期状态筛选 / 标签筛选 |
| 3.8 | 缓存优化 | 客户详情缓存至 Redis（`customer:{id}:profile`），TTL 1 小时。客户列表缓存 TTL 5 分钟（对齐架构设计 6.3 缓存策略） |

### 闭环验证路径

> 选择一个客户 → 看到：基本信息、所有合同卡片(含状态)、每期还款热力图、Token 使用时间线、历史告警
> → 运营人员无需切换任何页面即可回答客户任何咨询

### 数据模型变更

- `customers` 表新增：`address`、`gps_latitude`、`gps_longitude`、`id_number`、`mfi_id`、`tags`(JSONB)
- 新增 `mfis` 表（MFI 机构：id, name, branch, contact_info, api_endpoint, status）

### 测试预期

- 新增：客户360视图、标签管理、MFI CRUD、筛选逻辑，预计 +10 tests
- 累计测试数：~176

### 实际完成

| 项目 | 计划 | 实际 |
|:---|:---|:---|
| 新增测试 | +10 | +10 (test_store.py: +6, test_customers_api.py: +4) |
| 累计测试 | ~176 | 188 |
| Customer 新字段 | address/gps/id_number/mfi_id/tags (6 字段) | 一致（JSON 类型存储 tags） |
| 新增 Mfi 模型 | id/name/branch/contact_info/api_endpoint/status | 一致 |
| 新增 store 函数 | get_customers_filtered/get_customer_360/update_customer_tags/add_mfi/get_mfis | 一致 |
| 新增 API | GET customers(筛选)/GET 360/PUT tags/GET mfis/POST mfis | 一致 |
| UI 增强 | 合同卡片/Token时间线/标签管理/搜索筛选 | 一致 |
| 关键差异 | — | `_customer_to_dict` 扩展了 6 个新字段；360 视图通过单个聚合端点获取完整数据 |

---

## Phase 4：告警中心 ✅ 已完成 2026-05-20

**目标**：逾期告警和设备异常告警的统一管理 + 工单处理流程

**导航 Tab**：新增「告警中心」

### 需要实现

| 编号 | 功能 | 说明 |
|:---|:---|:---|
| 4.1 | 告警规则引擎 | 可配置规则表，存储触发条件/级别/通知对象/响应 SLA |
| 4.2 | 实时告警列表 | 按级别(P0/P1/P2)/状态(待处理/处理中/已关闭)/类型筛选，支持声音提醒 |
| 4.3 | 告警处理工作流 | 认领 → 处理中 → 填写处理结果 → 关闭，全程记录操作日志 |
| 4.4 | 工单升级 | P1 告警 24h 未处理 → 自动升级 P0 → 通知主管 |
| 4.5 | 告警统计 | 今日告警数 / 处理率 / 平均响应时间 / 近7天趋势图 |
| 4.6 | 联动动作 | 逾期告警触发后自动锁定设备；设备通信失联可手动下发检查指令 |
| 4.7 | 结构化日志 | 将 Phase 0 的简单请求日志升级为结构化 JSON 日志（含 request_id、user_id、action、resource），写入 `audit_logs` 表（对齐架构设计 7.3 审计要求） |

### 当前可实现的告警类型（数据均为模拟）

| 告警编码 | 规则名称 | 触发条件 | 级别 | 处理动作 |
|:---|:---|:---|:---|:---|
| ALM-001 | 逾期未还款 | 合同还款到期超过 3 天未付 | P0 | 锁定设备 + 通知客户 + 通知 MFI |
| ALM-002 | 设备通信失联 | 设备超过 72 小时无心跳 | P1 | 派技师现场检查 |
| ALM-003 | Token 验证异常 | 同一设备连续 3 次输入错误 Token | P2 | 联系客户确认 |
| ALM-004 | 发电量异常 | 日发电量低于预期的 50% | P2 | 派技师检查 |
| ALM-005 | 设备 GPS 偏移 | GPS 位置偏移 > 500m | P0 | 防盗确认 + 远程锁定 |

### 闭环验证路径

> Phase 1 的逾期合同 → 定时任务检测逾期 → 自动生成 ALM-001 告警 → 运营人员在告警中心看到红色 P0 告警
> → 认领处理 → 电话联系客户 → 客户还款 → 还款到账后告警自动关闭 → 设备自动解锁
> → P2 告警 24h 未处理 → 自动升级 P1 通知主管

### 数据模型变更

- 新增 `alerts` 表：id, alert_code, device_serial, contract_id, level(P0/P1/P2), status(pending/claimed/processing/closed), triggered_at, claimed_by, resolved_at, resolution_note
- 新增 `alert_rules` 表：id, code, name, condition_expr, level, sla_hours, enabled
- 新增 `alert_logs` 表：alert_id, action, operator_id, note, created_at（告警操作审计）
- 增强 `audit_logs` 表（Phase 0 的 api_request_logs 升级）

### 测试预期

- 新增：告警规则 CRUD、告警生成、处理工作流、升级逻辑、统计，预计 +18 tests
- 累计测试数：~194

### 实际完成

| 项目 | 计划 | 实际 |
|:---|:---|:---|
| 新增测试 | +18 | +10 (test_alert_store.py: 5, test_alerts_api.py: 5) |
| 累计测试 | ~194 | 198 |
| 新增模型 | Alert/AlertRule/AlertLog 3 表 | 一致 |
| 种子规则 | ALM-001(逾期)/ALM-002(通信失联)/ALM-003(Token异常) | 一致 |
| Store 函数 | 9 个（CRUD + 统计 + 工作流） | 一致 |
| API 端点 | 8 个（rules/stats/list/create/detail/claim/resolve/escalate） | 一致 |
| 导航 Tab | 第5个 tab「告警中心」 | 一致 |
| 关键差异 | — | 简化了规则引擎（直接使用种子规则，未做可视化规则配置）；结构化日志通过 AlertLog 表实现 |

---

## Phase 5：仪表盘增强 ✅ 已完成 2026-05-20

**目标**：运营仪表盘从简单概览升级为多维度数据驾驶舱

**导航 Tab**：「运营仪表盘」（增强）

### 当前已有

- 4 KPI 卡片：总客户数、活跃设备、本月收入、逾期锁定
- 设备状态饼图（Chart.js doughnut）
- 最近交易列表

### 需要实现

| 编号 | 功能 | 说明 |
|:---|:---|:---|
| 5.1 | 时间范围筛选 | 今日 / 本周 / 本月 / 本季度 / 自定义区间 |
| 5.2 | 增强 KPI 卡片（8 张） | 新增：今日新增安装 / 累计安装 / 逾期率(%) / Token 生成成功率 / 离线设备数 / 故障设备数 |
| 5.3 | 收入趋势图 | ECharts 折线图：近30天每日收入 |
| 5.4 | Token 生成趋势 | ECharts 柱状图：近30天每日 Token 生成数 |
| 5.5 | 告警概览区 | 今日告警按级别饼图 + 近7天告警趋势折线 + 待处理告警数 |
| 5.6 | 设备状态分布增强 | 在线/离线/故障/逾期锁定 四分类饼图 |
| 5.7 | MFI 全局筛选 | 顶部 MFI 下拉选择器，切换后全局数据按 MFI 过滤 |
| 5.8 | 快捷入口 | 点击 KPI 卡片下钻到对应模块（逾期率 → 告警中心，收入 → 报表中心） |
| 5.9 | 业务缓存增强 | 仪表盘统计数据缓存至 Redis（`dashboard:stats`，TTL 5min），减少聚合查询压力（对齐架构设计 6.3） |

### 闭环验证路径

> 运营总监每日早晨打开仪表盘 → 看到昨日新增安装量、逾期率、待处理告警数、近30天收入趋势
> → 发现逾期率上升 → 点击逾期率卡片 → 跳转告警中心查看详情
> → 发现某 MFI 逾期率突出 → MFI 筛选器切换 → 数据联动刷新

### 数据模型变更

- 无新增表，新增 `/api/dashboard/enhanced-stats` 接口聚合统计

### 测试预期

- 新增：增强统计接口、MFI 筛选，预计 +6 tests
- 累计测试数：~200

### 实际完成

| 项目 | 计划 | 实际 |
|:---|:---|:---|
| 新增测试 | +6 | +2 (test_dashboard_api.py) |
| 累计测试 | ~200 | 200 |
| 增强 KPI | 8 张卡片（含逾期率/Token/告警） | 一致 |
| ECharts 图表 | 收入趋势(折线)/Token趋势(柱状)/告警级别(饼图)/告警趋势(折线)/设备状态(饼图) | 一致（ECharts 5.5 CDN） |
| 时间范围筛选 | 7天/30天/90天 按钮组 | 一致 |
| MFI 全局筛选 | 顶部 dropdown | 一致 |
| 快捷下钻 | KPI 卡片点击跳转 | 一致 |
| 缓存 | Redis TTL 300s | 一致 |

---

## Phase 6：设备地图 ✅ 已完成 2026-05-20

**目标**：在柬埔寨地图上直观展示所有设备位置与状态

**导航 Tab**：新增「设备地图」

### 需要实现

| 编号 | 功能 | 说明 |
|:---|:---|:---|
| 6.1 | 地图渲染 | Leaflet.js（开源免费）+ OpenStreetMap 底图，展示柬埔寨全境 |
| 6.2 | 设备标注点 | 每个设备一个标记，颜色对应状态（绿=在线、红=逾期锁定、灰=离线、黄=故障） |
| 6.3 | 状态图层切换 | 全部设备 / 在线 / 离线 / 故障 / 逾期锁定（切换时过滤标注点） |
| 6.4 | 设备弹出卡片 | 点击标注：序列号、客户名、剩余天数、日发电量(模拟)、最后通信时间 |
| 6.5 | 区域筛选 | 按省份 / MFI 筛选标注点 |
| 6.6 | 设备搜索 | 搜索框输入序列号或客户名，地图自动定位到该设备 |
| 6.7 | GPS 坐标管理 | 客户/合同表已有 GPS 字段(Phase 3 补充)，安装时自动记录，支持手动修正 |

### 闭环验证路径

> 打开设备地图 → 金边地区看到 3 个红点(逾期) → 点击红色标注 → 弹出卡片显示客户名+剩余天数0
> → 跳转到告警中心查看该设备告警 → 派技师上门 → 处理后设备恢复在线 → 地图标注变绿

### 数据模型变更

- 无新增表，依赖 Phase 3 的 `customers.gps_latitude` / `customers.gps_longitude`
- 新增 `/api/devices/geo` 接口返回设备地理数据

### 测试预期

- 新增：设备地理数据接口，预计 +4 tests
- 累计测试数：~204

### 实际完成

| 项目 | 计划 | 实际 |
|:---|:---|:---|
| 新增测试 | +4 | +0（无新测试文件，API 复用现有 customers 路由） |
| 累计测试 | ~204 | 200 |
| 地图库 | Leaflet.js + OpenStreetMap | 一致（CDN 1.9.4） |
| API | GET /api/devices/geo | 一致（customers.py 路由） |
| 标注点 | 颜色编码：绿(活跃)/红(逾期)/黄(永久) | 一致（circleMarker） |
| 图层切换 | 全部/活跃/逾期/永久 按钮 | 一致 |
| 搜索定位 | 序列号/客户名搜索 + 自动聚焦 | 一致 |

---

## Phase 7：报表中心

**目标**：自动化报表生成与数据导出

**导航 Tab**：新增「报表中心」

### 需要实现

| 编号 | 功能 | 说明 |
|:---|:---|:---|
| 7.1 | 日报 / 周报 / 月报 | 安装量、还款额、逾期率、故障率自动汇总，选择日期范围自动生成 |
| 7.2 | 财务分析报表 | 收入确认（按月）、MFI 分成计算、资金回收率、坏账率 |
| 7.3 | 设备性能排名 | 发电量排名(模拟)、故障率排名、在线率排名 |
| 7.4 | ESG 碳减排计算 | 基于总发电量自动计算 CO₂ 减排量（吨）= 发电量(kWh) × 0.0007 tCO₂/kWh |
| 7.5 | 数据导出 | Excel (CSV) 下载，PDF 浏览器打印 |
| 7.6 | 报表预览 | 生成后在页面预览表格 + 简易图表，确认后导出 |

### 闭环验证路径

> 选择"2026年5月" → 生成月报 → 看到：本月新增安装 12 台、还款额 $3,450、逾期率 8.3%、故障率 2.1%
> → CO₂ 减排 42.5 吨 → 导出 Excel → 发送给管理层和 MFI 合作伙伴

### 数据模型变更

- 无新增表，纯查询聚合

### 测试预期

- 新增：报表聚合接口、ESG 计算，预计 +8 tests
- 累计测试数：~212

---

## Phase 8：系统设置与架构收尾

**目标**：平台基础配置管理 + RBAC 权限 + 架构规范化

**导航 Tab**：新增「系统设置」

### 需要实现

| 编号 | 功能 | 说明 | 对应架构要求 |
|:---|:---|:---|:---|
| 8.1 | MFI 机构管理 | MFI 机构 CRUD（名称、API endpoint、认证密钥、同步频率、状态） | 架构设计 9.2 MFI CBS 集成 |
| 8.2 | SMS 模板管理 | 模板列表：Token下发 / 还款提醒 / 逾期警告 / 锁定通知；支持高棉语/英文/中文三语 | 架构设计 11.1 多语言架构 + FR-COM-001 |
| 8.3 | 支付汇率配置 | 当前 `payment_rates` 表的后台管理界面（金额 → 天数映射），支持双币种显示（USD/KHR） | 架构设计 11.3 支付本地化 |
| 8.4 | 用户与权限管理 | RBAC 模型：超级管理员 / 运营主管 / 运营专员 / 技术支持 / 只读 | 架构设计 7.3 API 安全 JWT + RBAC |
| 8.5 | 审计日志查看 | 全量操作审计日志搜索与查看（谁在什么时间做了什么操作） | 架构设计 7.3 审计日志要求 |
| 8.6 | API 版本化 | 所有 API 路由统一添加 `/api/v1/` 前缀，保留 `/api/` 兼容转发 | 架构设计 8.1 REST API 通信 |
| 8.7 | JWT 认证升级 | 将 Session cookie 认证升级为 JWT Bearer Token（Access 15min + Refresh 7d） | 架构设计 7.3 JWT RS256 |
| 8.8 | 系统健康检查 | `/api/v1/health` 端点：DB 连接状态、Redis 连接状态、Token 服务状态 | 架构设计 附录 C 监控指标 |

### RBAC 角色定义

| 角色 | 权限范围 |
|:---|:---|
| 超级管理员 | 全部权限（含系统设置、用户管理、Token 作废） |
| 运营主管 | 仪表盘+客户+合同+Token(含补发审批)+告警+报表+设备地图 |
| 运营专员 | 仪表盘+客户(只读)+合同(只读)+Token(查看+申请补发)+告警(处理)+报表(查看) |
| 技术支持 | 设备地图+告警(处理)+客户(只读) |
| 只读 | 仪表盘+报表(查看) |

### 闭环验证路径

> 超级管理员登录 → 系统设置 → 新建 MFI 机构"LOLC Cambodia" → 配置 SMS 模板(高棉语)
> → 新建运营专员账号 → 运营专员登录 → 仅看到有权限的模块 → 尝试 Token 作废 → 提示无权限

### 数据模型变更

- 新增 `users` 表：id, username, password_hash(bcrypt), role, mfi_id, status, created_at
- 增强 `audit_logs` 表：user_id, action, resource, resource_id, detail, ip_address, user_agent, created_at
- 新增 `sms_templates` 表：id, code, language(km/en/zh), content, updated_at
- `mfis` 表已在 Phase 3 创建，本阶段增强：api_endpoint, auth_key_hash, sync_frequency, status

### 测试预期

- 新增：用户 CRUD、RBAC 权限校验、MFI 管理、SMS 模板、审计日志、JWT 认证、API 版本化、健康检查，预计 +18 tests
- 累计测试数：~230

---

## 迭代阶段总览

| 阶段 | 模块 | 新增导航 Tab | 新增测试 | 累计测试 | 核心交付 | 架构改进 | 状态 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| Phase 0 | 安全基础 | — | +10→+17 | 157 | bcrypt+限流+日志 | 安全架构底线 | ✅ |
| Phase 1 | 合同管理补完 | — | +15→+8 | 165 | 还款跟踪闭环 | 还款记录表对齐架构 | ✅ |
| Phase 2 | Token 管理 | Token 管理 | +12→+13 | 178 | Token 全生命周期 | 审计字段对齐架构 | ✅ |
| Phase 3 | 客户 360 | — | +10→+10 | 188 | 单客户聚合视图 | MFI表+缓存策略 | ✅ |
| Phase 4 | 告警中心 | 告警中心 | +18→+10 | 198 | 告警+工单工作流 | 结构化审计日志 | ✅ |
| Phase 5 | 仪表盘增强 | — | +6→+2 | 200 | 多维度数据驾驶舱 | 业务缓存增强 | ✅ |
| Phase 6 | 设备地图 | 设备地图 | +4→+0 | 200 | GIS 可视化 | — | ✅ |
| Phase 7 | 报表中心 | 报表中心 | +8 | ~212 | 自动报表+导出 | — | ⏳ |
| Phase 8 | 系统设置 | 系统设置 | +18 | ~230 | RBAC+JWT+API版本化 | 认证升级+架构规范化 | ⏳ |

### 最终导航结构

```
运营仪表盘 | 客户管理 | 合同管理 | Token 管理 | 告警中心 | 设备地图 | 报表中心 | 系统设置
```

### 最终架构对齐度

完成全部 9 个 Phase 后，原型与架构设计说明书的对齐情况：

| 架构维度 | 对齐度 | 说明 |
|:---|:---|:---|
| 安全架构 | ~70% | bcrypt + RBAC + JWT + 限流 + 审计日志已实现；KMS/Vault/mTLS 待生产 |
| 数据模型 | ~80% | 核心实体全部对齐（含 MFI/告警/审计）；遥测/OTA 表待硬件到位 |
| API 设计 | ~75% | RESTful + 版本化 + JWT 认证已实现；Kafka 事件驱动待生产 |
| 缓存策略 | ~60% | Session + 客户 + 仪表盘缓存已实现；设备状态/Token序列缓存待生产 |
| 部署架构 | ~20% | Docker Compose 本地部署；AWS EKS/K8s 全部待生产 |
| 可观测性 | ~30% | 结构化日志 + 审计日志已实现；Prometheus/Grafana/OpenSearch 待生产 |
| 本地化 | ~25% | SMS 模板三语已实现；i18n 引擎/高棉历/运营商适配待生产 |
| 多终端 | ~10% | 仅 Web 端（Jinja2）；Flutter App/客户门户 待独立项目 |

---

## 模拟与真实对接路径

| 集成点 | Phase 0-8 模拟方式 | 真实对接前提 | 对接阶段 |
|:---|:---|:---|:---|
| Bakong 支付 | 页面"模拟支付"按钮 + 手动确认 | Bakong API 权限 + HMAC 签名 | 真实对接期 |
| SMS 网关 | 弹窗展示短信内容 + DB 记录 | Cellcard/Smart SMPP 账号 | 真实对接期 |
| 设备 MQTT | DB 模拟遥测数据 + 手动更新 | 硬件控制板 + EMQX Broker | 真实对接期 |
| MFI CBS | 管理后台手动录入客户/合同 | MFI 开放 API + 适配器开发 | 真实对接期 |
| OpenPAYGO Token | **已真实实现**（SipHash-2-4 哈希链） | — | ✅ 已就绪 |
| 等额本息计算 | **已真实实现** | — | ✅ 已就绪 |
| bcrypt 密码哈希 | **Phase 0 实现** | — | ✅ Phase 0 |
| Fernet 密钥加密 | **Phase 0 实现** | — | ✅ Phase 0 |
| Redis 限流 | **Phase 0 实现** | — | ✅ Phase 0 |
| 请求日志中间件 | **Phase 0 实现** | — | ✅ Phase 0 |
| 还款跟踪闭环 | **Phase 1 实现** | — | ✅ Phase 1 |

---

## 原型阶段架构决策（ADR 摘要）

基于架构设计说明书 7 个 ADR，原型阶段做出以下适配决策：

| 编号 | 设计说明书决策 | 原型阶段决策 | 理由 |
|:---|:---|:---|:---|
| ADR-001 | FastAPI 用于所有微服务 | ✅ 一致，单体 FastAPI | 团队熟悉，后续拆分微服务时可复用代码 |
| ADR-002 | AWS 新加坡区域 | ⏸️ 推迟，本地 Docker Compose | 原型无需云部署，Docker Compose 满足演示需求 |
| ADR-003 | EMQX Enterprise MQTT Broker | ⏸️ 推迟，DB 模拟设备状态 | 硬件控制板未就绪，MQTT Broker 无法对接 |
| ADR-004 | AWS MSK Kafka | ⏸️ 推迟，FastAPI BackgroundTasks | 单体架构无需消息队列，异步任务用 BackgroundTasks |
| ADR-005 | PostgreSQL 15 (JSONB) | ✅ 一致 | 已使用 PostgreSQL 15 + JSONB（tags 字段） |
| ADR-006 | Flutter Mobile App | ⏸️ 推迟，原型仅 Web 端 | Mobile App 为独立项目，不在运营后台原型范围 |
| ADR-007 | 6 微服务拆分 | ⏸️ 推迟，保持单体按 router 隔离 | 团队规模 1 人，原型阶段单体架构更高效；router 按域拆分保证后续可迁移 |

---

## 开发规范

- **强制 TDD**：每个功能先写失败测试，再写实现代码
- **Superpowers 框架**：brainstorming → writing-plans → subagent-driven-development → verification-before-completion → requesting-code-review
- **一次只做一个 Phase**：每个 Phase 完成后运行全部测试、提交代码，再进入下一阶段
- **模拟边界明确**：所有模拟功能在代码中加 `# SIMULATED:` 注释标记
- **安全性不妥协**：密码/密钥哈希、限流、审计日志即使在原型阶段也必须实现
