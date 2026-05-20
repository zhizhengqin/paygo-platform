# M7 合同与还款计划引擎 — 设计文档

## 目标
为运营后台新增合同管理模块，支持贷款产品配置、合同全生命周期管理、等额本息还款计划自动生成。导航栏新增「合同管理」tab。

## 合同状态流转

```
draft → approved → active → overdue → closed
                        ↓
                    recovered
```

| 状态 | 含义 | 触发 |
|------|------|------|
| `draft` | 草稿 | 创建合同时初始状态 |
| `approved` | 已审批 | MFI 审批通过，自动生成还款计划 |
| `active` | 执行中 | 审批通过后进入，客户正常还款 |
| `overdue` | 逾期 | 超过还款日未还，自动/手动标记 |
| `closed` | 已结清 | 全部期数还清 |
| `recovered` | 已回收 | 严重违约，设备已回收 |

## 新增数据模型

### loan_products（贷款产品表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(8) PK | LP-xxxx 格式 |
| name | String(100) | 产品名称，如 "10kW-24月标准" |
| capacity_kw | Numeric(5,2) | 系统规模：6/10/15/20/30 |
| term_months | Integer | 贷款期限：12/18/24/36 |
| interest_rate | Numeric(5,2) | 年利率 % |
| down_payment_pct | Numeric(5,2) | 首付比例 % |
| total_amount | Numeric(12,2) | 系统总价 USD |
| status | String(20) | active / disabled |
| created_at | DateTime | 创建时间 |

### contracts（合同表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(8) PK | CT-xxxx 格式 |
| contract_no | String(30) unique | KH-2026-00001 格式 |
| customer_id | String(8) FK | 关联客户 |
| product_id | String(8) FK | 关联贷款产品 |
| down_payment | Numeric(12,2) | 首付金额 |
| loan_amount | Numeric(12,2) | 贷款本金 = total_amount - down_payment |
| monthly_payment | Numeric(10,2) | 月供（等额本息公式计算） |
| status | String(20) | draft/approved/active/overdue/closed/recovered |
| start_date | Date | 合同开始日 |
| end_date | Date | 合同结束日 |
| remaining_days | Integer | 设备剩余使用天数 |
| approved_at | DateTime | 审批通过时间 |
| created_at | DateTime | 创建时间 |

`monthly_payment` 使用等额本息公式：
```
月供 = 贷款本金 × [月利率 × (1+月利率)^期数] / [(1+月利率)^期数 - 1]
```

### repayment_schedule（还款计划表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(8) PK | RS-xxxx 格式 |
| contract_id | String(8) FK | 关联合同 |
| period_no | Integer | 期数（1-N） |
| due_date | Date | 应还日期 |
| principal | Numeric(10,2) | 当期本金 |
| interest | Numeric(10,2) | 当期利息 |
| total | Numeric(10,2) | 当期总额 = principal + interest |
| balance | Numeric(12,2) | 剩余本金（还款后） |
| status | String(20) | pending / paid / overdue |

合同审批通过（approved）时，自动生成全部期数的还款计划。

## API 设计

### 贷款产品 API（/api/loan-products）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/loan-products | 列表（支持 status 筛选） |
| GET | /api/loan-products/{id} | 详情 |
| POST | /api/loan-products | 新增（管理员） |
| PUT | /api/loan-products/{id} | 编辑 |
| DELETE | /api/loan-products/{id} | 软删除（设 status=disabled） |

### 合同 API（/api/contracts）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/contracts | 列表（支持 status/customer_id 筛选） |
| GET | /api/contracts/{id} | 详情（含还款计划） |
| POST | /api/contracts | 创建（初始状态 draft） |
| PUT | /api/contracts/{id}/approve | 审批通过 → approved → active，生成还款计划 |
| PUT | /api/contracts/{id}/status | 状态变更（mark_overdue / close / recover） |
| DELETE | /api/contracts/{id} | 删除（仅 draft 状态可删） |

## 页面布局

「合同管理」tab 复用客户管理的左右布局：

```
┌──────────────────────────────────────────────────────────┐
│  左侧 (300px)                      │  右侧 (flex:1)        │
│ ┌──────────────────────────────┐  │                      │
│ │  合同列表          [数量]     │  │  合同详情卡片          │
│ │  + 新合同                    │  │  - 合同编号 + 状态     │
│ ├──────────────────────────────┤  │  - 客户 + 产品信息     │
│ │  KH-2026-001  Sok Heng  ⬤   │  │  - 贷款金额 + 月供     │
│ │  KH-2026-002  Alice     ⬤   │  │  - 审批/状态操作按钮    │
│ │  KH-2026-003  Bob       ⬤   │  │                      │
│ │  ...                        │  │  还款计划表            │
│ ├──────────────────────────────┤  │  - 等额本息明细       │
│ │  ⚙ 贷款产品配置              │  │  - 每期：本金/利息/余额 │
│ └──────────────────────────────┘  │  - 已还/待还/逾期标记   │
└──────────────────────────────────────────────────────────┘
```

## 导航栏扩展

在 base.html 的 nav-tabs 中新增：
```html
<a class="nav-tab" data-tab="contracts" onclick="switchTab('contracts')">合同管理</a>
```

## 种子数据

系统初始化时预置 5 档贷款产品：
- 6kW — $690 × 12/24月
- 10kW — $1,150 × 12/24月
- 15kW — $1,725 × 12/24/36月
- 20kW — $2,300 × 24/36月
- 30kW — $3,450 × 24/36月

## 改动文件清单

| 文件 | 操作 | 内容 |
|------|------|------|
| `app/models.py` | 修改 | 新增 LoanProduct / Contract / RepaymentSchedule 模型 |
| `app/store.py` | 修改 | 合同 CRUD + 还款计划生成 + 贷款产品 CRUD + 等额本息计算 |
| `app/routers/contracts.py` | 新建 | 贷款产品 + 合同 API |
| `app/main.py` | 修改 | 注册 contracts router |
| `templates/base.html` | 修改 | nav-tabs 加「合同管理」 |
| `templates/dashboard.html` | 修改 | switchTab('contracts') 分支 + 合同管理 JS |
| `static/style.css` | 修改 | 还款计划表 + 合同详情样式 |
| `tests/test_contracts_api.py` | 新建 | 合同 API 测试 |

## 与现有模块的关联

- 合同创建时需要选择客户 — 复用现有客户列表 API
- active 合同的月供支付 — 复用现有 simulate-payment API（关联 contract_id）
- 合同审批时自动生成 Token — 复用现有 Token 生成逻辑
