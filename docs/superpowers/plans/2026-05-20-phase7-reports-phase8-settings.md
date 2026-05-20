# Phase 7+8: 报表中心 + 系统设置 实施计划

**Goal:** 完成最后两个模块：报表中心（聚合查询+CSV导出+ESG计算）和系统设置（RBAC+SMS模板+健康检查）

---

## Phase 7: 报表中心

### Task 7.1: Store + API — 报表聚合查询
- New: `app/routers/reports.py` — `/api/reports/summary?start=&end=` 日报/周报/月报
- `/api/reports/esg` — CO2 减排计算
- CSV export via StreamingResponse

### Task 7.2: UI — 报表中心 Tab
- Date range picker + report type selector
- Preview table + CSV download button
- ESG metrics display

---

## Phase 8: 系统设置

### Task 8.1: Users 模型 + SMS 模板模型 + 迁移
### Task 8.2: Store + API — 用户管理 + SMS 模板 + 健康检查
### Task 8.3: UI — 系统设置 Tab
- MFI 管理（已有 API，增加 UI）
- 支付汇率配置 UI
- SMS 模板管理 UI
- 用户管理 UI
- 系统健康检查面板
