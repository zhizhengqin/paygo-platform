# PAYGO 太阳能平台 — 运营后台操作手册

柬埔寨太阳能 PAYGO（Pay-As-You-Go）运营管理平台。通过 MFI 合作，客户分期付款购买太阳能系统，还款后生成 OpenPAYGO Token 延长设备使用期限。

---

## 1. 快速启动

```bash
# 确保 PostgreSQL 15 和 Redis 8 已运行
cd paygo-platform
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**访问**：http://localhost:8000/dashboard
**登录**：`admin` / `admin123`

> 首次启动自动创建 16 张表，种子 5 档贷款产品 + 3 条告警规则 + 支付汇率。运行 `scripts/seed_demo_data.py` 可加载完整演示数据（4 个客户 + 合同 + 还款记录）。

**平台顶部导航栏（8 个模块）**：

```
运营仪表盘 | 客户管理 | 合同管理 | Token 管理 | 告警中心 | 设备地图 | 报表中心 | 系统设置
```

---

## 2. 完整业务闭环测试（按角色）

### 角色说明

| 角色 | 职责 | 覆盖模块 |
|:---|:---|:---|
| 运营总监 | 查看全局数据、审批关键操作 | 仪表盘、报表中心 |
| 运营专员 | 日常客户服务、Token 补发、告警处理 | 客户管理、Token 管理、告警中心 |
| 业务经理 | 合同审批、还款跟踪、MFI 管理 | 合同管理、客户管理 |
| 技术支持 | 设备监控、告警处理、系统健康 | 设备地图、告警中心、系统设置 |

---

### 2.1 运营总监：每日晨检流程

**目标**：3 分钟内掌握平台全局运行状态

#### 步骤 1：打开仪表盘首页

1. 登录后默认进入「运营仪表盘」
2. 查看 **8 张 KPI 卡片**：
   - 总客户数 / 活跃设备 / 本月收入(USD) / 逾期锁定(率)
   - 本月 Token 生成 / 执行中合同 / 待处理告警 / 逾期率
3. 点击右上角时间切换按钮：**7天 / 30天 / 90天**（默认 30 天）
4. 顶部 MFI 下拉框选择特定机构（可选，默认"全部 MFI"）

#### 步骤 2：查看趋势图表

- **收入趋势折线图**：观察近 30 天收入波动，判断业务健康度
- **Token 生成柱状图**：还款活跃度
- **告警级别饼图**：P0(红)/P1(黄)/P2(蓝) 分布
- **近 7 天告警趋势折线图**：告警是上升还是下降
- **设备状态饼图**：活跃(绿)/逾期锁定(红)/永久解锁(黄)

#### 步骤 3：快速下钻

- 点击「待处理告警」卡片 → 跳转告警中心查看详情
- 点击「逾期锁定」卡片 → 跳转客户管理查看逾期客户
- 点击「总客户数」→ 跳转客户管理

#### 步骤 4：查看报表（可选）

1. 点击导航栏「报表中心」
2. 默认显示本月汇总（新增客户/总收入/Token 生成/逾期率）
3. 查看 **ESG 碳减排**：CO₂ 减排量（吨）
4. 选择日期范围 → 点击「查询」可自定义统计周期
5. 点击「导出 CSV」下载报表

---

### 2.2 运营专员：客户服务日常操作

**目标**：处理客户咨询、Token 补发、模拟还款

#### 场景 A：新增客户

1. 点击导航栏「**客户管理**」
2. 点击左侧「**+ 新增**」按钮
3. 填写表单：
   - 姓名：如 `Chan Dara`
   - 电话：柬埔寨格式 `+85512345678`
   - 设备编号：如 `SN-KH-005`
   - 设备密钥：点击「随机」自动生成 32 位 hex，或手动输入
4. 点击「确认添加」→ 客户出现在左侧列表

#### 场景 B：查看客户 360 视图

1. 在左侧客户列表**搜索框**输入姓名或电话（实时搜索，300ms 防抖）
2. 点击目标客户 → 右侧显示完整 360 视图：
   - **基本信息**：姓名、电话、设备编号、密钥(部分隐藏)、地址、身份证、GPS、MFI
   - **标签管理**：查看现有标签，点击「+ 添加标签」输入 VIP/高风险/新客户/投诉频繁
   - **模拟支付**：下拉选择金额
   - **合同列表**：每个合同显示编号+状态+贷款金额（可点击跳转合同详情）
   - **Token 历史时间线**：最多 15 条，⚪未使用/🟢已使用/🔴已作废
3. 如果该客户有逾期合同，会显示红色「X 个合同已逾期」提醒

#### 场景 C：模拟支付（生成 Token）

1. 选中客户，在详情面板找到「模拟支付」
2. 下拉选择金额：**$5.00 → 30天** 或 **$10.00 → 60天**
3. 点击「确认支付」
4. 弹窗显示：
   - **9 位 OpenPAYGO Token**（如 `023554141`）
   - **模拟短信内容**（收件人电话 + Token + 有效天数）
5. 点击「完成」→ 客户详情自动刷新

#### 场景 D：模拟还款（通过合同）

1. 切换到「合同管理」→ 选择一个「执行中」的合同
2. 在「模拟还款」区看到待还期数按钮
3. 点击 **第 N 期 · $XX.XX · 日期**
4. 弹窗显示 ADD_TIME Token（30 天）
5. 观察还款进度条变化（绿色增加）

#### 场景 E：Token 补发（客户反馈未收到 SMS）

1. 切换到「**Token 管理**」
2. 左侧列表找到目标 Token（可按状态筛选，⚪=未使用）
3. 点击 Token → 右侧显示详情（Token 值/类型/客户/金额/Counter/时间/关联合同）
4. 状态为「未使用」的 Token，点击「**补发 Token**」
5. 确认弹窗 → 新 Token 生成（Counter+1），原 Token 标记「已作废」
6. Toast 提示「新 Token 已生成: XXXXXXXX」

#### 场景 F：Token 作废（安全事件）

1. 在 Token 详情页，点击「**作废 Token**」
2. 输入作废原因（如"客户投诉 Token 泄露"）
3. Token 状态变为 SUPERSEDED，记录操作人和原因

---

### 2.3 业务经理：合同全生命周期管理

**目标**：走通签合同 → 审批 → 还款 → 结清完整流程

#### 主流程：从头创建并执行一份合同

**第 1 步：确认贷款产品**

1. 切换到「合同管理」
2. 点击左侧「**⚙ 贷款产品配置**」
3. 确认 5 档产品存在（6kW-12月 ~ 30kW-36月）

**第 2 步：创建合同**

1. 点击「**+ 新合同**」
2. 选择客户（需先在客户管理中创建）
3. 选择贷款产品
4. 点击「确认创建」→ 合同编号自动生成（如 `KH-2026-00001`），状态=草稿

**第 3 步：审批通过**

1. 点击合同 → 右侧显示详情
2. 点击「**审批通过**」
3. 合同状态变为「执行中」
4. 自动生成**等额本息还款计划表**：
   - 每期显示：期数 / 应还日 / 月供 / 本金 / 利息 / 剩余本金 / 状态(⏳待还)
5. 还款进度条显示 `0 / N 期 · 0%`

**第 4 步：模拟还款（第 1 期）**

1. 在「模拟还款」区点击「**第 1 期 · $XX.XX**」
2. 弹窗显示 ADD_TIME Token 和模拟短信
3. 还款进度条更新为 `1 / N 期 · X%`
4. 还款计划表中该期状态变为 **已付**

**第 5 步：检测逾期**

1. 如果某期到期未付，点击「**检测逾期**」按钮
2. 系统自动：
   - 将到期未付期数标记为「逾期」
   - 合同状态变为「逾期」
   - 关联客户设备自动「锁定」
3. Toast 提示「检测到 N 条逾期计划」

**第 6 步：提前结清**

1. 合同处于「执行中」或「逾期」状态
2. 点击「**提前结清**」→ 确认弹窗
3. 系统自动：
   - 生成 **DISABLE_PAYG Token**（永久解锁码）
   - 所有未付期数标记为已付
   - 合同状态 → closed
   - 客户状态 → permanent（永久解锁）

#### 合同状态流转图

```
draft（草稿）→ active（执行中）→ overdue（逾期）→ closed（已结清）
                   ↓                    ↓
              recovered（回收）   recovered（回收）
```

---

### 2.4 设备控制器模拟（Web + 终端双模式）

**目标**：模拟 PAYGO Dongle 硬件行为，验证 Token 输入→设备解锁/续期的完整链路

#### Web 版模拟器（推荐，安卓手机可用）

1. 点击导航栏右上角「**📱 设备模拟器**」或直接访问 `/controller`
2. 页面展示深色终端风格界面
3. 下拉选择要模拟的设备（如 `Sok Heng · DEV-KH-001`）

**界面显示**：
```
── 太阳能控制器 ──────────────────
设备   DEV-KH-001
客户   Sok Heng
密钥   a1b2c3d4…
状态   已激活
Count  4
继电器 ● 供电中
```

**输入 Token 验证**：
1. 在平台完成一笔模拟支付 → 获得 9 位 Token（如 `023554141`）
2. 在控制器页面的输入框输入 Token
3. 点击「验证 Token」或按回车
4. 验证成功：`✓ 验证成功 · +30 天`（见下方截图）

![控制器验证成功](docs/screenshots/13-controller-validated.png)

5. 重复输入同一 Token → `✗ Token 已使用（防重放）`

![控制器防重放](docs/screenshots/14-controller-replay.png)

6. DISABLE_PAYG Token：`✓✓ 贷款已结清 · 设备永久解锁`

**安卓手机访问**：
```
1. 手机连接与服务器同一 WiFi
2. 浏览器打开 http://<服务器局域网IP>:8000/controller
3. 登录平台 → 选择设备 → 输入 Token
```

#### 终端模拟器（桌面开发调试）

```bash
cd paygo-platform
source venv/bin/activate
cd controller && python controller.py
```

终端界面提供完整的 Dongle 模拟：
- 初始设置输入 32 位 hex 密钥
- N 键输入 9 位 Token → 本地 OpenPAYGO 解码验证
- D 键快进天数（模拟时间流逝）
- R 键重置设备
- 实时显示：密钥/状态/剩余天数/继电器/Count

---

### 2.5 告警处理（运营专员 + 技术支持）

**目标**：处理平台告警，走通认领→处理→关闭工作流

#### 场景：逾期告警触发→处理

1. 首先确保有逾期合同（合同管理 → 检测逾期）
2. 切换到「**告警中心**」
3. 左侧告警列表按级别排序（P0 红色 / P1 黄色 / P2 蓝色 优先）
4. 左侧底部显示统计：
   - 总数 / 今日 / 待处理 / 已关闭

**处理一条告警：**

1. 点击一条「待处理」告警
2. 右侧显示详情：
   - 级别 + 标题 + 详情描述
   - 规则编码（ALM-001/002/003）
   - 触发时间
   - 关联合同 ID + 客户 ID
3. 点击「**认领告警**」→ 状态变为「已认领」，记录认领人
4. 实际处理（电话联系客户等）
5. 点击「**标记解决**」→ 输入解决备注（如"已联系客户，承诺明日还款"）
6. 告警状态变为「已关闭」

**升级告警：**

1. 对于 P1 或 P2 告警，点击「**升级**」
2. P2 → P1，P1 → P0
3. 操作日志记录升级事件

**查看操作日志：**

- 告警详情底部显示完整操作时间线：触发 → 认领 → 升级 → 解决

---

### 2.6 技术支持：设备地图监控

**目标**：通过地图直观监控所有设备状态

1. 切换到「**设备地图**」
2. 地图自动定位到柬埔寨全境（Leaflet + OpenStreetMap）
3. 有 GPS 坐标的设备以**彩色圆点**标注：
   - 🟢 绿色 = 活跃
   - 🔴 红色 = 逾期锁定
   - 🟡 黄色 = 永久解锁

**图层切换**：
- 点击顶部按钮：全部 / 活跃 / 逾期锁定 / 永久解锁 → 过滤标注点

**设备搜索**：
- 在搜索框输入设备序列号或客户名 → 单结果自动聚焦 zoom 14

**设备弹窗**：
- 点击标注点 → Popup 显示：客户名、设备编号、状态

---

### 2.7 系统管理员：系统设置

**目标**：管理平台基础配置和用户

1. 切换到「**系统设置**」

**系统健康检查**：
- 查看数据库状态（ok/error）
- 查看 Redis 状态
- 整体状态：ok / degraded

**MFI 机构管理**：
- 查看已有 MFI 列表
- 输入名称 + 支行 → 点击「新增」

**支付汇率管理**：
- 查看当前汇率映射（金额 → 天数）

**用户管理**：
- 查看已有用户（用户名 + 角色）
- 输入用户名 + 密码 + 选择角色 → 点击「新增」
- 可用角色：运营专员 / 运营主管 / 技术支持 / 只读

---

## 3. 完整业务闭环走通验证清单

按以下顺序逐一操作，验证平台全部功能：

```
□ 1. [仪表盘] 登录 → 首页 8 张 KPI 卡片正常显示
□ 2. [仪表盘] ECharts 图表渲染（收入/Token/告警/设备）
□ 3. [仪表盘] 时间切换 7天/30天，数据刷新
□ 4. [客户管理] 新增客户（姓名+电话+设备编号+随机密钥）
□ 5. [客户管理] 搜索框输入客户姓名 → 筛选正常
□ 6. [客户管理] 点击客户 → 360 视图正常展示
□ 7. [客户管理] 添加标签 "VIP" → 标签显示在详情和列表
□ 8. [客户管理] 模拟支付 $5 → Token 弹窗展示
□ 9. [合同管理] 切换 tab → 合同列表显示
□ 10. [合同管理] 查看贷款产品配置 → 5 档产品存在
□ 11. [合同管理] 创建合同（选客户+产品）→ 草稿状态
□ 12. [合同管理] 审批通过 → 还款计划表生成
□ 13. [合同管理] 模拟还款第1期 → Token 生成，进度条更新
□ 14. [合同管理] 点击检测逾期 → 逾期合同标记
□ 15. [合同管理] 提前结清 → DISABLE_PAYG Token 生成
□ 15a.[控制器] 打开 /controller → 选择设备 → 输入 Token → 验证成功
□ 15b.[控制器] 尝试输入已使用 Token → 防重放拒绝
□ 15c.[控制器] DISABLE_PAYG Token → 永久解锁提示
□ 16. [Token管理] 切换 tab → Token 列表显示
□ 17. [Token管理] 查看统计卡片（总数/今日/本月/已作废）
□ 18. [Token管理] 点击 Token 查看详情
□ 19. [Token管理] 作废 Token → 输入原因 → 状态变化
□ 20. [Token管理] 补发 Token → 新 Token 生成
□ 21. [Token管理] 批量生成 → 生成成功
□ 22. [告警中心] 切换 tab → 告警列表显示（3 条种子规则）
□ 23. [告警中心] 点击告警 → 详情 + 操作日志
□ 24. [告警中心] 认领 → 标记解决 → 升级 工作流正常
□ 25. [设备地图] 切换 tab → Leaflet 地图渲染
□ 26. [设备地图] 图层切换（全部/活跃/逾期/永久）正常
□ 27. [设备地图] 搜索设备序列号 → 自动定位
□ 28. [报表中心] 切换 tab → 报表汇总正常
□ 29. [报表中心] ESG 碳减排数据显示
□ 30. [报表中心] CSV 导出下载正常
□ 31. [系统设置] 切换 tab → 健康检查状态正常
□ 32. [系统设置] 新增 MFI 机构
□ 33. [系统设置] 新增用户
□ 34. [登录] 登出 → 重新登录 → session 正常
□ 35. [登录] 连续 5 次错误密码 → 账户锁定提示
```

---

## 4. 演示数据加载

```bash
cd paygo-platform
source venv/bin/activate
PYTHONPATH="." python scripts/seed_demo_data.py
```

### 演示数据概览

| 指标 | 值 |
|:---|:---|
| 总客户数 | 4 |
| 活跃设备 | 2 |
| 逾期锁定 | 1 |
| 贷款产品 | 5 档（6kW ~ 30kW） |
| 合同 | 3 份（含还款计划） |

| 客户 | 电话 | 设备 | 合同 | 状态 |
|:---|:---|:---|:---|:---|
| Sok Heng | 0888888001 | DEV-KH-001 | 10kW-24月 | 🟢 活跃（还款中） |
| Alice | 011222333 | DEV-KH-002 | 6kW-12月 | 🟢 活跃（还款中） |
| Bob | 044555666 | DEV-KH-003 | 15kW-24月 | 🔴 逾期锁定 |
| Sarun | 077123456 | DEV-KH-004 | 无 | ⚪ 待签约 |

---

## 5. API 接口速查

所有接口需先登录。认证方式：Session Cookie 或 JWT Bearer Token。

### 5.1 仪表盘

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/dashboard/stats` | 基础 KPI |
| GET | `/api/dashboard/enhanced-stats?days=30` | 增强统计（含趋势） |

### 5.2 客户管理

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/customers?search=&status=&mfi_id=` | 客户列表（筛选） |
| POST | `/api/customers` | 新增客户 |
| GET | `/api/customers/{id}` | 客户详情 |
| GET | `/api/customers/{id}/360` | 客户 360 聚合视图 |
| DELETE | `/api/customers/{id}` | 删除客户 |
| POST | `/api/customers/{id}/simulate-payment` | 模拟支付 |
| POST | `/api/customers/{id}/lock` | 锁定设备 |
| POST | `/api/customers/{id}/permanent-unlock` | 永久解锁 |
| PUT | `/api/customers/{id}/tags` | 更新标签 |
| GET | `/api/devices/geo` | 设备地图数据 |

### 5.3 合同管理

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/loan-products` | 贷款产品列表 |
| POST | `/api/loan-products` | 新增产品 |
| GET | `/api/contracts` | 合同列表 |
| POST | `/api/contracts` | 创建合同 |
| GET | `/api/contracts/{id}` | 合同详情（含还款计划） |
| PUT | `/api/contracts/{id}/approve` | 审批通过 |
| PUT | `/api/contracts/{id}/status` | 状态变更 |
| POST | `/api/contracts/{id}/pay` | 还款一期 |
| POST | `/api/contracts/check-overdue` | 检测逾期 |
| POST | `/api/contracts/{id}/settle` | 提前结清 |

### 5.4 Token 管理

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/tokens?customer_id=&status=&limit=` | Token 列表 |
| GET | `/api/tokens/stats` | Token 统计 |
| GET | `/api/tokens/{id}` | Token 详情 |
| POST | `/api/tokens/{id}/reissue` | 补发 Token |
| POST | `/api/tokens/{id}/void` | 作废 Token |
| POST | `/api/tokens/batch-generate` | 批量生成 |

### 5.5 告警中心

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/alerts/rules` | 告警规则 |
| GET | `/api/alerts/stats` | 告警统计 |
| GET | `/api/alerts?status=&level=` | 告警列表 |
| POST | `/api/alerts` | 创建告警 |
| GET | `/api/alerts/{id}` | 告警详情（含日志） |
| POST | `/api/alerts/{id}/claim` | 认领 |
| POST | `/api/alerts/{id}/resolve` | 解决 |
| POST | `/api/alerts/{id}/escalate` | 升级 |

### 5.6 MFI + 报表 + 设置

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/mfis` | MFI 列表 |
| POST | `/api/mfis` | 新增 MFI |
| GET | `/api/reports/summary?start_date=&end_date=` | 报表汇总 |
| GET | `/api/reports/esg` | ESG 碳减排 |
| GET | `/api/reports/export` | CSV 导出 |
| GET | `/api/settings/health` | 健康检查 |
| GET | `/api/settings/payment-rates` | 支付汇率 |
| GET | `/api/settings/users` | 用户列表 |
| POST | `/api/settings/users` | 新增用户 |
| GET | `/api/v1/health` | API v1 健康探活 |
| POST | `/api/controller/validate-token` | 控制器 Token 验证（Web 模拟器用） |

### curl 示例

```bash
# 登录
curl -c cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  http://localhost:8000/login

# 仪表盘增强统计
curl -b cookies.txt http://localhost:8000/api/dashboard/enhanced-stats?days=30

# 创建客户
curl -b cookies.txt -X POST -H "Content-Type: application/json" \
  -d '{"name":"Test","phone":"+855999","device_id":"DEV-T1","secret_key":"'$(python3 -c "import secrets;print(secrets.token_hex(16))")'"}' \
  http://localhost:8000/api/customers

# 创建合同 → 审批 → 还款 → 结清
CUST_ID="Cxxxx"
PROD_ID=$(curl -b cookies.txt http://localhost:8000/api/loan-products | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")
CT_ID=$(curl -b cookies.txt -X POST -H "Content-Type: application/json" \
  -d "{\"customer_id\":\"$CUST_ID\",\"product_id\":\"$PROD_ID\"}" \
  http://localhost:8000/api/contracts | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -b cookies.txt -X PUT http://localhost:8000/api/contracts/$CT_ID/approve
# 获取第一期 schedule_id 后还款
curl -b cookies.txt -X POST -H "Content-Type: application/json" \
  -d '{"schedule_id":"RSxxxx","amount":43.31}' \
  http://localhost:8000/api/contracts/$CT_ID/pay
```

---

## 6. 环境要求与安装

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

## 7. 运行测试

```bash
source venv/bin/activate
pytest tests/ -v     # 200 个测试
```

测试使用独立数据库 `paygo_platform_test`，不影响开发数据。

---

## 8. 项目结构

```
paygo-platform/
├── app/
│   ├── main.py              # FastAPI 入口（lifespan 管理 DB/Redis/中间件/迁移）
│   ├── settings.py          # 数据库/Redis/安全/JWT/限流 配置
│   ├── models.py            # SQLAlchemy ORM（16 张表）
│   ├── database.py          # async engine + session 工厂
│   ├── redis.py             # Redis session/缓存/防重放
│   ├── store.py             # async 数据访问层（CRUD/还款/逾期/告警/标签/360）
│   ├── security.py          # bcrypt + Fernet + JWT
│   ├── middleware.py         # API 限流 + 请求日志
│   └── routers/
│       ├── auth.py          # 登录/登出（bcrypt + JWT + session）
│       ├── customers.py     # 客户 CRUD + 模拟支付 + 锁定/解锁 + 设备地图
│       ├── contracts.py     # 合同 + 贷款产品 + 还款/逾期/结清
│       ├── tokens.py        # Token 管理（列表/详情/补发/作废/批量）
│       ├── alerts.py        # 告警中心（规则/列表/详情/认领/解决/升级）
│       ├── dashboard.py     # 仪表盘统计（基础 + 增强）
│       ├── reports.py       # 报表中心（汇总/ESG/CSV导出）
│       ├── settings.py      # 系统设置（健康检查/汇率/模板/用户）
│       └── config.py        # 支付汇率配置
├── scripts/
│   └── seed_demo_data.py    # 演示数据初始化脚本
├── controller/
│   ├── controller.py        # 终端 UI（Token 输入/密钥绑定）
│   └── state_manager.py     # 状态机 + PostgreSQL 持久化
├── static/
│   ├── style.css            # 全局样式（绿色主题 #059669）
│   └── logo.png
├── templates/
│   ├── base.html            # 布局框架（8 个导航 Tab）
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面 SPA（全部 8 个模块）
└── tests/                   # 200 个测试
```

---

## 9. 环境变量

| 变量 | 默认值 | 说明 |
|:---|:---|:---|
| `DATABASE_URL` | `postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform` | 数据库连接串 |
| `TEST_DATABASE_URL` | 同上，数据库 `paygo_platform_test` | 测试数据库 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `DB_POOL_SIZE` | `10` | 连接池常驻连接数 |
| `DB_MAX_OVERFLOW` | `20` | 连接池峰值溢出 |
| `CACHE_TTL_API` | `60` | API 缓存 TTL（秒） |
| `SESSION_TTL` | `1800` | Session TTL（30分钟） |
| `ANTIREPLAY_TTL` | `604800` | Token 防重放 TTL（7天） |
| `ADMIN_USERNAME` | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD_HASH` | (空) | bcrypt 密码哈希 |
| `SECRET_KEY_MASTER_KEY` | (空=自动生成) | Fernet 加密主密钥 |
| `RATE_LIMIT_PER_MINUTE` | `100` | API 限流（次/分钟/IP） |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | 登录限流 |
| `LOGIN_MAX_FAILURES` | `5` | 登录锁定阈值 |
| `LOGIN_LOCKOUT_MINUTES` | `15` | 锁定时间（分钟） |
| `JWT_SECRET_KEY` | (内置默认) | JWT 签名密钥 |
| `JWT_ACCESS_TOKEN_EXPIRE` | `15` | JWT Access Token 有效期（分钟） |
| `JWT_REFRESH_TOKEN_EXPIRE` | `7` | JWT Refresh Token 有效期（天） |

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
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      SECRET_KEY_MASTER_KEY: ${SECRET_KEY_MASTER_KEY}
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
DB_PASSWORD=<password> JWT_SECRET_KEY=<random> SECRET_KEY_MASTER_KEY=<random> docker compose up -d
```

### 云托管（Render / Railway / Fly.io）

1. 推送代码到 GitHub
2. 创建 Web Service，Build: `pip install -r requirements.txt`
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 配置环境变量指向云 PostgreSQL + Redis
5. 健康检查端点：`GET /api/v1/health`

---

## 11. 原型模拟边界说明

以下功能在原型阶段仅做**模拟**，部署到云也无法真实对接：

| 功能 | 模拟方式 | 需真实对接时 |
|:---|:---|:---|
| Bakong 支付 | 页面按钮 → 手动确认 + 自动触发 Token | 柬埔寨国家银行 API 权限 |
| SMS 网关 | 弹窗展示短信内容 + DB 记录 | Cellcard/Smart SMPP 企业账号 |
| MQTT 设备通信 | DB 手动更新设备状态 | 硬件控制板（ESP32/Dongle） |
| MFI CBS 同步 | 管理后台手动录入 | MFI 核心银行系统 API |
