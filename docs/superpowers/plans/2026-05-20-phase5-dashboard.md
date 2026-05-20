# Phase 5: 仪表盘增强 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 运营仪表盘从简单概览升级为多维度数据驾驶舱：增强 KPI、ECharts 趋势图、告警概览、MFI 筛选、快捷下钻。

**Architecture:** 增强 `/api/dashboard/enhanced-stats` 接口（聚合收入趋势/Token趋势/告警统计），UI 使用 ECharts 替换 Chart.js，增加时间范围筛选器和 MFI 全局下拉。

**Tech Stack:** FastAPI, SQLAlchemy, ECharts (CDN), Jinja2

---

### Task 1: Store — 增强仪表盘统计函数

**Files:** Modify `app/store.py`, `tests/test_dashboard_api.py`

增强 `get_dashboard_stats` → 新增 `get_enhanced_dashboard_stats`，包含：
- 收入趋势（近30天每日）
- Token 生成趋势（近30天每日）
- 告警统计（按级别/近7天）
- MFI 筛选参数支持
- 缓存支持（Redis TTL 5min）

```python
async def get_enhanced_dashboard_stats(db: AsyncSession, days: int = 30, mfi_id: str = None) -> dict:
    # 基础 KPI
    # 收入趋势: select date(generated_at), sum(amount) from tokens group by date
    # Token 趋势: select date(generated_at), count(*) from tokens group by date
    # 告警统计: count by level, 7-day trend
    # ...
```

- [ ] 写测试 → 实现 → pytest tests/test_dashboard_api.py -v → commit

---

### Task 2: API — 增强仪表盘端点

**Files:** Modify `app/routers/dashboard.py`

```python
@router.get("/dashboard/enhanced-stats")
async def enhanced_dashboard_stats(
    request: Request, days: int = 30, mfi_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    await _check_auth(request)
    return await get_enhanced_dashboard_stats(db, days=days, mfi_id=mfi_id)
```

- [ ] 添加缓存（Redis key: `dashboard:enhanced:{days}:{mfi_id}`, TTL 300s）
- [ ] commit

---

### Task 3: UI — 仪表盘全面增强

**Files:** Modify `templates/dashboard.html` (showDashboard 函数)

核心变更：
1. **时间范围筛选器** — 7天/30天/本月/本季度 按钮组
2. **增强 KPI 卡片 8 张** — 新增安装量/逾期率/Token成功率/离线设备
3. **ECharts 折线图** — 近30天收入趋势（替代当前简版）
4. **ECharts 柱状图** — 近30天 Token 生成趋势
5. **告警概览区** — 按级别饼图 + 近7天趋势折线
6. **设备状态四分类饼图** — 在线/离线/故障/逾期
7. **MFI 全局筛选器** — 顶部 dropdown
8. **快捷下钻** — 点击逾期率→告警中心，点击收入→报表

ECharts CDN 引用已在页面顶部有 Chart.js，添加：
```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
```

- [ ] 重写 showDashboard 函数
- [ ] commit

---

### Task 4: 回归测试 + 修复

```bash
pytest tests/ -q  # Expected ~203 tests PASS
```

---

### Task 5: 冒烟测试
启动应用，验证仪表盘新 UI 正常渲染
