# 柬埔寨太阳能PAYGO运营后端平台
# 需求规格说明书（PRD）

**文档编号**：XHZ-PAYGO-PRD-001  
**版本号**：V1.0  
**密级**：内部机密  
**编制单位**：新华智科技（柬埔寨）有限公司  
**编制日期**：2026年5月20日  
**审批状态**：待评审  

---

## 修订记录

| 版本 | 日期 | 修订人 | 修订内容 | 审批人 |
|:---|:---|:---|:---|:---|
| V0.1 | 2026-05-15 | 产品组 | 初稿框架搭建 | — |
| V0.2 | 2026-05-18 | 架构组 | 补充非功能需求与ADR引用 | — |
| V1.0 | 2026-05-20 | 项目组 | 整合评审意见，发布基线版 | 待审批 |

---

## 目录

1. [项目概述](#1-项目概述)
2. [术语与定义](#2-术语与定义)
3. [干系人与用户画像](#3-干系人与用户画像)
4. [功能需求](#4-功能需求)
5. [非功能需求](#5-非功能需求)
6. [核心业务流程](#6-核心业务流程)
7. [数据需求](#7-数据需求)
8. [接口需求](#8-接口需求)
9. [合规与法规需求](#9-合规与法规需求)
10. [附录](#10-附录)

---

## 1. 项目概述

### 1.1 项目背景

新华智科技（柬埔寨）有限公司计划在柬埔寨市场推广6kW–30kW分布式太阳能发电系统，采用**PAYGO（Pay-As-You-Go，即付即用）**模式与本地小额信贷机构（MFI）联合运营。客户通过MFI贷款购买太阳能系统，按月还款；还款成功后，平台自动生成并下发激活Token，客户输入Token后设备恢复供电。逾期未还款则远程锁定。

### 1.2 项目目标

构建一套**自建PAYGO运营后端平台**，支撑以下核心目标：

| 目标编号 | 目标描述 | 成功指标 |
|:---|:---|:---|
| G1 | 实现Token全生命周期管理（生成→下发→验证→审计） | Token生成成功率≥99.9%，验证延迟<100ms |
| G2 | 实现设备远程监控与智能告警 | 设备在线率≥95%，告警延迟<5分钟 |
| G3 | 实现与MFI核心银行系统（CBS）及Bakong支付系统的无缝对接 | 支付闭环自动化率≥98% |
| G4 | 支撑200套首批试点及未来10,000套规模扩展 | 系统并发支撑≥1,000台设备同时在线 |
| G5 | 满足柬埔寨国家银行（NBC）数据本地化与消费者保护合规要求 | 通过NBC技术服务商报备审核 |

### 1.3 系统边界

**系统内（In-Scope）**：
- Token生成与验证服务（基于OpenPAYGO标准）
- 设备注册、遥测接收、远程控制、OTA升级
- 支付网关对接（Bakong KHQR、P2P转账、Webhook）
- MFI CBS适配器（客户/合同/还款/逾期数据同步）
- 运营后台Web端、安装技师Mobile App、MFI Loan Officer App、客户自助门户
- SMS网关（Token下发、还款提醒、逾期警告）

**系统外（Out-of-Scope）**：
- 硬件控制板固件开发（由嵌入式团队独立负责，平台仅通过MQTT/接口对接）
- MFI内部核心银行系统改造（仅提供适配接口）
- 太阳能系统现场安装施工（由安装团队负责）

### 1.4 参考文档

- 《柬埔寨太阳能PAYGO系统自建平台与硬件改造实操手册 V1.0》（新华智科技，2026-05-12）
- OpenPAYGO Token Specification v2.1（EnAccess Foundation）
- Bakong API Developer Guide（National Bank of Cambodia）
- 柬埔寨消费者保护法（Consumer Protection Law 2019）

---

## 2. 术语与定义

| 术语 | 英文全称 | 定义 |
|:---|:---|:---|
| PAYGO | Pay-As-You-Go | 即付即用模式，客户按期还款获取激活Token，逾期则远程断电 |
| Token | OpenPAYGO Token | 基于AES-128加密的一次性激活码，通常为15位数字，用于延长设备使用天数或解锁 |
| MFI | Microfinance Institution | 小额信贷机构，如LOLC Cambodia、PRASAC、ACLEDA Bank等 |
| CBS | Core Banking System | MFI核心银行系统，如Temenos T24、Oracle Flexcube |
| Bakong | — | 柬埔寨国家银行运营的零售支付系统，支持KHQR扫码、P2P转账 |
| Dongle | PAYGO Dongle | 串接于逆变器与负载之间的智能控制模块，负责Token验证与电力通断 |
| Secret Key | — | 每台设备唯一的128位密钥，用于Token加解密，存储于加密芯片（ATSHA204A）及平台KMS中 |
| Counter | Token Counter | 单调递增的计数器，防止Token重放攻击 |
| ADD_TIME | — | Token类型之一，为客户增加若干天使用时长 |
| SET_TIME | — | Token类型之一，将客户剩余天数设置为指定值 |
| DISABLE_PAYG | — | Token类型之一，永久关闭PAYGO锁定（结清后使用） |
| COUNTER_SYNC | — | Token类型之一，同步设备与平台计数器（解决离线漂移） |
| mTLS | Mutual TLS | 双向传输层安全认证，用于设备与MQTT Broker之间的身份验证 |
| APN | Access Point Name | 移动网络接入点，如Smart（smart.com.kh）、Cellcard（cellcard.com.kh）、Metfone（metfone.com.kh） |
| NBC | National Bank of Cambodia | 柬埔寨国家银行，负责金融科技监管与支付系统审批 |
| SLA | Service Level Agreement | 服务等级协议，平台承诺的系统可用性与响应时间指标 |

---

## 3. 干系人与用户画像

### 3.1 干系人矩阵

| 干系人 | 角色定位 | 核心诉求 | 使用频率 | 优先级 |
|:---|:---|:---|:---|:---|
| 新华智运营总监 | 平台所有者 | 实时掌握业务数据、逾期率、设备故障率 | 每日 | P0 |
| 新华智运营专员 | 日常运营人员 | 快速处理客户咨询、Token补发、工单流转 | 每日 | P0 |
| 安装技师 | 现场实施人员 | 离线环境下完成设备安装、激活、拍照留档 | 每日 | P0 |
| MFI Loan Officer | 信贷专员 | 现场录入客户资料、评估信用、收取现金还款 | 每日 | P0 |
| 终端客户 | 太阳能系统购买者 | 查看剩余天数、获取Token、报修故障 | 每周 | P1 |
| MFI IT管理员 | 技术对接方 | 稳定的数据同步、清晰的API文档、故障排查支持 | 每周 | P1 |
| NBC监管人员 | 合规审查方 | 数据存储位置透明、审计日志完整、消费者投诉渠道 | 按需 | P1 |

### 3.2 用户画像（Persona）

#### 画像A：Sokha（安装技师）
- **背景**：25岁柬埔寨男性，高棉语母语，基础英文，熟悉太阳能系统安装
- **场景**：骑摩托车携带设备前往客户家中，现场无WiFi，依赖手机4G或离线缓存
- **痛点**：客户地址不准确、设备二维码磨损、Token输入后设备无响应
- **需求**：离线工单缓存、扫码识别设备、蓝牙/WiFi直连设备调试、一键故障上报

#### 画像B：Dara（MFI Loan Officer）
- **背景**：30岁柬埔寨女性，高棉语/英文双语，在PRASAC支行工作3年
- **场景**：前往农村客户家中进行贷前调查，现场评估客户还款能力
- **痛点**：纸质申请表易丢失、客户信用历史分散在不同系统、现金还款后Token延迟下发
- **需求**：离线填写申请表、自动信用评分、电子签名、现金收款即时触发Token

#### 画像C：Kim（运营专员）
- **背景**：35岁华人，中文/高棉语双语，金边办公室工作
- **场景**：每日早晨查看仪表盘，处理夜间告警，回复客户WhatsApp咨询
- **痛点**：告警过多无法分级、客户重复咨询相同问题、MFI数据同步延迟导致逾期误判
- **需求**：告警分级与工单自动分配、客户自助查询门户、MFI数据实时同步状态看板

---

## 4. 功能需求

### 4.1 功能模块总览

```
┌─────────────────────────────────────────────────────────────┐
│                    PAYGO运营后端平台                          │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│  4.2 Token  │  4.3 设备   │  4.4 支付   │  4.5 MFI对接        │
│   服务模块   │  管理模块   │  网关模块   │   适配器模块        │
├─────────────┼─────────────┼─────────────┼─────────────────────┤
│  4.6 运营   │  4.7 安装   │  4.8 MFI    │  4.9 客户           │
│   后台模块   │  技师App    │ Loan Officer│  自助门户           │
│             │             │    App      │                     │
└─────────────┴─────────────┴─────────────┴─────────────────────┘
           ├─────────────────────────────────────────┤
           │         4.10 通信与通知模块（SMS/MQTT/邮件）   │
           └─────────────────────────────────────────┘
```

### 4.2 Token服务模块（核心引擎）

#### FR-TOK-001：Token生成
- **优先级**：P0
- **描述**：平台根据设备序列号、Secret Key、当前Counter、Token类型及天数参数，生成符合OpenPAYGO标准的15位数字Token。
- **输入**：device_serial, token_type(ADD_TIME/SET_TIME/DISABLE_PAYG/COUNTER_SYNC), days(可选), generated_by(操作人ID)
- **处理**：调用OpenPAYGO-python库，AES-128加密，Counter单调递增
- **输出**：15位数字Token、Token哈希（bcrypt存储）、审计日志记录
- **约束**：
  - 生成前校验：设备存在、合同状态为ACTIVE、无未处理冻结工单
  - Counter防回滚：新Counter必须 > 数据库当前值
  - 批量预生成：支持为未来12个月预生成Token序列，存储于Redis

#### FR-TOK-002：Token验证
- **优先级**：P0
- **描述**：接收设备通过SMS或MQTT上报的Token，验证其有效性并返回结果。
- **输入**：device_serial, token_string(15位数字)
- **处理**：
  1. 查询设备Secret Key（KMS解密）
  2. 尝试解码Token，提取Counter和类型
  3. 校验Counter > 设备当前Counter
  4. 校验Token哈希匹配（防篡改）
  5. 更新设备剩余天数、Counter、最后验证时间
- **输出**：验证结果（VALID/INVALID/EXPIRED/REPLAY）、更新后的设备状态
- **约束**：验证接口必须支持离线场景（设备在无网络时输入Token，下次联网时批量上报）

#### FR-TOK-003：Token审计与追溯
- **优先级**：P0
- **描述**：完整记录每一次Token生成与验证操作，支持按设备、客户、时间、操作人多维度查询。
- **审计字段**：id, device_serial, token_type, token_hash, counter, days, generated_at, generated_by, ip_address, user_agent, payment_id(关联还款)
- **保留策略**：永久保留，归档至AWS S3（Parquet格式，按年分区）

#### FR-TOK-004：Token手动补发
- **优先级**：P1
- **描述**：运营专员在客户SMS未送达或Token丢失时，手动触发补发。
- **流程**：查询原Token → 校验原Token未被使用 → 生成新Token（Counter+1）→ SMS重发 → 标记原Token为SUPERSEDED
- **权限**：仅运营主管及以上角色可执行，需填写补发原因

### 4.3 设备管理模块

#### FR-DEV-001：设备注册
- **优先级**：P0
- **描述**：安装技师在现场通过Mobile App完成设备入库与激活。
- **录入字段**：
  - 硬件信息：serial_number（唯一，激光刻印或二维码）、model、capacity_kw、firmware_version、hardware_version、imei、imsi
  - 位置信息：gps_latitude, gps_longitude, installation_address（高棉语/英文双语）
  - 关联信息：customer_id, contract_id, mfi_branch_id
  - 激活信息：starting_code（首套Token，用于Dongle初始配对）、secret_key（KMS加密存储）
- **流程**：App扫码 → 蓝牙读取设备信息 → 录入客户信息 → 拍照上传（设备铭牌、安装位置、客户签字）→ 平台生成Starting Code → 技师现场输入激活

#### FR-DEV-002：实时状态监控
- **优先级**：P0
- **描述**：通过MQTT接收设备遥测数据，实时展示设备运行状态。
- **遥测数据项**：
  - 发电侧：pv_power(W), daily_energy(kWh), total_energy(kWh)
  - 储能侧：battery_soc(%), battery_voltage(V), battery_current(A)
  - 负载侧：load_power(W), grid_power(W)
  - 通信侧：signal_strength(dBm), network_type(4G/3G/2G)
  - 状态侧：fault_code(0=正常), lock_status(LOCKED/UNLOCKED), remaining_days
- **刷新频率**：遥测上报间隔默认5分钟，告警数据实时上报

#### FR-DEV-003：告警规则引擎
- **优先级**：P0
- **描述**：基于遥测数据自动触发告警，生成工单并通知相关人员。
- **告警规则**：

| 告警编码 | 规则名称 | 触发条件 | 级别 | 通知对象 | 响应SLA |
|:---|:---|:---|:---|:---|:---|
| ALM-001 | 发电量骤降 | 日发电量 < 预期值50%，连续3天 | P1 | 运营专员+安装技师 | 24h |
| ALM-002 | 电池老化 | SOC持续<20%超过48小时 | P1 | 运营专员+客户 | 24h |
| ALM-003 | 设备被盗 | GPS偏移>500米（非安装技师主动变更） | P0 | 运营主管+警方接口 | 2h |
| ALM-004 | 通信失联 | 信号丢失>72小时 | P1 | 运营专员 | 48h |
| ALM-005 | 逾期锁定 | 合同逾期>3天，系统自动锁定 | P0 | MFI Loan Officer+客户 | 即时 |
| ALM-006 | 固件异常 | fault_code ≠ 0 | P2 | 技术支持 | 72h |

#### FR-DEV-004：OTA固件升级
- **优先级**：P1
- **描述**：通过MQTT commands通道向设备下发固件升级包。
- **流程**：上传固件包至S3 → 选择目标设备（按型号/批次/区域筛选）→ 灰度发布（10%→50%→100%）→ 设备下载并校验SHA-256 → 重启升级 → 上报新版本号 → 平台确认升级成功
- **回滚机制**：升级失败自动回滚至上一版本，最多重试3次

### 4.4 支付网关模块

#### FR-PAY-001：Bakong支付接入
- **优先级**：P0
- **描述**：对接柬埔寨国家银行Bakong系统，支持KHQR扫码支付、P2P转账、Webhook回调。
- **功能点**：
  - KHQR生成：根据合同号、还款期数、金额生成符合EMVCo标准的QR码
  - P2P转账：客户通过任意银行App扫描KHQR完成转账
  - Webhook接收：Bakong异步回调支付结果，平台验签后触发Token生成
  - 支付查询：主动查询Bakong支付状态（Webhook未到达时的兜底机制）

#### FR-PAY-002：现金还款录入
- **优先级**：P0
- **描述**：MFI Loan Officer或柜台人员录入客户现金还款，手动触发Token生成。
- **流程**：选择客户合同 → 输入还款金额 → 上传现金收据照片 → 选择还款期数 → 确认 → 平台生成Token → SMS下发
- **约束**：现金还款需MFI主管复核（金额>$100时），复核后Token才下发

#### FR-PAY-003：三方对账
- **优先级**：P1
- **描述**：每日凌晨自动执行Bakong流水、MFI CBS、平台Token记录的三方对账。
- **对账维度**：交易笔数、交易金额、交易状态、Token生成记录
- **差异处理**：
  - 支付成功但Token未生成：自动补发Token，告警通知
  - Token已生成但支付未到账：冻结Token，生成催收工单
  - 金额不匹配：生成人工复核工单
  - 重复支付：幂等性校验，自动退款或计入下期

#### FR-PAY-004：双币种管理
- **优先级**：P0
- **描述**：平台同时支持KHR（柬埔寨瑞尔）和USD（美元），默认以USD计价，KHR按NBC官方汇率换算。
- **规则**：
  - 汇率源：NBC官网每日10:00自动抓取
  - 精度：USD保留2位小数，KHR保留0位小数（柬埔寨惯例）
  - 显示：客户界面优先显示USD，KHR作为参考

### 4.5 MFI对接适配器模块

#### FR-MFI-001：客户信息同步
- **优先级**：P0
- **描述**：从MFI CBS同步客户基本信息至平台，避免重复录入。
- **同步字段**：customer_id(CBS主键)、name、phone、email、id_number、address、credit_score、branch_id
- **同步模式**：
  - 实时：MFI CBS通过API推送客户新增/变更事件
  - 定时：每日凌晨全量同步（差异比对，仅同步变更记录）
  - 手动：运营专员触发紧急同步

#### FR-MFI-002：贷款合同同步
- **优先级**：P0
- **描述**：同步贷款合同信息，建立设备-合同-客户的关联关系。
- **同步字段**：contract_id, customer_id, loan_amount, interest_rate, term_months, monthly_payment, start_date, status(PENDING/ACTIVE/CLOSED/DEFAULTED)
- **约束**：合同状态变更为DEFAULTED时，平台自动触发设备锁定流程

#### FR-MFI-003：还款记录同步
- **优先级**：P0
- **描述**：同步MFI CBS中的还款记录，作为Token生成的触发源之一。
- **同步字段**：repayment_id, contract_id, amount, currency, payment_date, transaction_id, payment_method(CASH/BANK_TRANSFER/Bakong)
- **幂等性**：以transaction_id为唯一键，防止重复生成Token

#### FR-MFI-004：逾期状态同步
- **优先级**：P0
- **描述**：实时同步客户逾期状态，驱动设备锁定/解锁决策。
- **规则**：
  - 逾期1-3天：SMS还款提醒（每日一次）
  - 逾期4-7天：SMS逾期警告 + MFI Loan Officer催收任务
  - 逾期>7天：自动锁定设备（发送DISABLE_PAYG或限制输出Token）
  - 逾期结清：客户还款后，MFI CBS更新状态 → 平台自动解锁 → 发送ADD_TIME Token

#### FR-MFI-005：设备抵押登记
- **优先级**：P1
- **描述**：将设备作为贷款抵押物登记至MFI CBS。
- **字段**：device_serial, contract_id, mortgage_date, mortgage_value, release_date(结清后)

### 4.6 运营后台Web端模块

#### FR-OPS-001：仪表盘（Dashboard）
- **优先级**：P0
- **描述**：实时展示核心业务指标，支持按时间范围、区域、MFI筛选。
- **核心指标**：
  - 今日新增安装量、累计安装量
  - 活跃设备数、离线设备数、故障设备数
  - 今日还款额、本月还款额、逾期率（按金额/笔数）
  - Token生成成功率、SMS送达率
  - 告警统计（按级别/类型）
- **可视化**：ECharts折线图、柱状图、饼图；Mapbox柬埔寨地图（设备热力图）

#### FR-OPS-002：设备地图
- **优先级**：P0
- **描述**：在柬埔寨地图上展示所有设备位置与状态。
- **功能**：
  - 图层切换：全部设备 / 在线 / 离线 / 故障 / 逾期锁定
  - 设备弹窗：序列号、客户名、剩余天数、日发电量、最后通信时间
  - 轨迹回放：设备GPS历史轨迹（防盗追踪）
  - 区域框选：批量导出选中区域的设备清单

#### FR-OPS-003：客户管理
- **优先级**：P0
- **描述**：客户全生命周期管理。
- **功能**：
  - 客户列表：支持按姓名、电话、MFI、逾期状态筛选
  - 客户详情页：基本信息、合同列表、还款日历、设备列表、Token历史、告警历史
  - 信用评分：集成MFI信用评分，支持平台自定义评分模型
  - 客户标签：手动打标签（VIP、高风险、投诉频繁等）

#### FR-OPS-004：合同管理
- **优先级**：P0
- **描述**：贷款合同管理与跟踪。
- **功能**：
  - 合同列表：状态筛选、到期提醒
  - 合同详情：还款计划表（甘特图）、实际还款记录、逾期天数、剩余本金
  - 合同操作：提前结清（生成DISABLE_PAYG Token）、展期申请、违约标记

#### FR-OPS-005：Token管理
- **优先级**：P0
- **描述**：Token的批量生成、查询、补发、作废。
- **功能**：
  - 批量生成：选择设备范围 + Token类型 + 天数 → 异步生成任务 → 结果导出Excel
  - Token历史：按设备/客户/时间查询，显示使用状态（UNUSED/USED/SUPERSEDED）
  - 手动补发：FR-TOK-004
  - Token作废：运营主管权限，作废后该Token无法使用，需生成新Token

#### FR-OPS-006：告警中心
- **优先级**：P0
- **描述**：告警的统一处理与工单流转。
- **功能**：
  - 实时告警列表：按级别/状态/类型筛选，支持声音提醒
  - 告警处理：认领 → 处理 → 填写处理结果 → 关闭
  - 工单升级：P1告警24小时未处理自动升级至P0并通知主管
  - 历史统计：告警趋势分析、技师响应时效分析

#### FR-OPS-007：报表中心
- **优先级**：P1
- **描述**：多维度业务报表与数据导出。
- **报表类型**：
  - 日报/周报/月报：安装量、还款额、逾期率、故障率
  - 财务分析：收入确认、MFI分成、资金回收率
  - 设备性能：发电量排名、故障率排名、电池衰减分析
  - ESG碳减排：基于发电量自动计算CO₂减排量（吨）
- **导出格式**：Excel、PDF、CSV

#### FR-OPS-008：系统设置
- **优先级**：P1
- **描述**：平台基础配置与权限管理。
- **功能**：
  - MFI对接配置：API endpoint、认证密钥、同步频率、数据映射规则
  - SMS模板管理：Token下发模板、还款提醒模板、逾期警告模板（支持高棉语/英文/中文）
  - 支付路由：Bakong主通道、现金兜底、汇率配置
  - 用户权限：RBAC模型（角色：超级管理员、运营主管、运营专员、技术支持、只读）

### 4.7 安装技师Mobile App模块

#### FR-APP-TECH-001：工单管理
- **优先级**：P0
- **描述**：接收、查看、执行安装/维修工单。
- **功能**：工单列表（待办/进行中/已完成）、工单详情（客户地址、设备清单、导航）、工单状态流转（出发→到达→安装→测试→完成）

#### FR-APP-TECH-002：设备注册
- **优先级**：P0
- **描述**：现场完成设备注册与激活。
- **功能**：扫码/手动输入序列号 → 蓝牙读取设备信息 → 录入客户信息 → 拍照上传 → 生成Starting Code → 现场输入激活 → 测试Token输入

#### FR-APP-TECH-003：离线模式
- **优先级**：P0
- **描述**：无网络环境下缓存数据，恢复网络后自动同步。
- **缓存策略**：工单数据、客户信息、设备注册表单、照片（压缩后本地存储）
- **同步机制**：恢复网络后自动检测未同步数据，批量上传，冲突时提示技师选择

#### FR-APP-TECH-004：客户培训
- **优先级**：P1
- **描述**：向客户演示Token输入方法，录制确认签字。
- **功能**：播放高棉语教学视频 → 引导客户输入测试Token → 客户签字确认（电子签名）→ 上传培训完成记录

### 4.8 MFI Loan Officer App模块

#### FR-APP-MFI-001：客户申请录入
- **优先级**：P0
- **描述**：现场录入客户贷款申请资料。
- **功能**：拍照身份证、填写申请表（离线可用）、估算用电需求（根据房屋面积/电器清单自动推荐功率配置）

#### FR-APP-MFI-002：信用评估
- **优先级**：P0
- **描述**：基于客户收入、资产、历史信用自动计算推荐贷款额度。
- **模型输入**：月收入、土地/房产证明、历史MFI还款记录、家庭人口
- **输出**：推荐贷款额度、建议首付比例、风险提示

#### FR-APP-MFI-003：合同签署
- **优先级**：P0
- **描述**：现场生成电子合同并完成签署。
- **流程**：选择模板 → 自动填充客户信息 → 展示合同条款（高棉语）→ 客户电子签名 → Loan Officer签名 → 生成PDF → 上传平台

#### FR-APP-MFI-004：还款收集
- **优先级**：P0
- **描述**：现场收取现金并录入系统。
- **功能**：选择客户 → 显示应还金额 → 输入实收金额 → 上传收据照片 → 确认 → 触发Token生成

#### FR-APP-MFI-005：催收管理
- **优先级**：P1
- **描述**：查看逾期客户列表并执行催收任务。
- **功能**：逾期客户地图（按距离排序）、导航至客户地址、记录催收结果（客户承诺还款日期/拒绝还款/失联）、一键锁定设备（需主管审批）

### 4.9 客户自助门户模块

#### FR-PORTAL-001：余额查询
- **优先级**：P0
- **描述**：客户查看剩余天数、历史Token、还款记录。
- **入口**：Web响应式页面（手机浏览器访问），无需下载App

#### FR-PORTAL-002：在线客服
- **优先级**：P1
- **描述**：集成WhatsApp Business API或Facebook Messenger，客户一键发起咨询。

#### FR-PORTAL-003：故障报修
- **优先级**：P0
- **描述**：客户上传故障照片，描述问题，生成工单。
- **流程**：选择故障类型（无电/发电量低/设备异响/Token无效）→ 上传照片 → 描述问题 → 生成工单号 → 运营后台接收 → 分配技师

#### FR-PORTAL-004：教育内容
- **优先级**：P2
- **描述**：太阳能使用指南、节能技巧、维护知识。
- **形式**：高棉语图文、短视频（适配柬埔寨低带宽环境）

### 4.10 通信与通知模块

#### FR-COM-001：SMS网关
- **优先级**：P0
- **描述**：通过柬埔寨本地运营商发送短信。
- **通道**：Cellcard企业短信网关（主通道）+ Smart Axiata（备用通道）
- **协议**：SMPP v3.4（bind_transmitter模式）
- **模板**：

| 模板编码 | 场景 | 高棉语模板（示例） | 英文模板（示例） |
|:---|:---|:---|:---|
| SMS-001 | Token下发 | លេខកូដរបស់អ្នកគឺ {token} សម្រាប់ {days} ថ្ង៙ | Your token is {token} for {days} days. |
| SMS-002 | 还款提醒 | សូមរំលស់ប្រាក់ {amount} មុន {date} | Please repay {amount} before {date}. |
| SMS-003 | 逾期警告 | ការបង់ប្រាក់របស់អ្នកហួសកំណត់ {days} ថ្ង៙ | Your payment is overdue by {days} days. |
| SMS-004 | 锁定通知 | ប្រព័ន្ធត្រូវបានផ្អាក សូមទំនាក់ទំនង {phone} | System locked. Contact {phone}. |

- **字符限制**：高棉语Unicode单条70字符，超长自动拆分多条

#### FR-COM-002：双向SMS
- **优先级**：P1
- **描述**：客户回复特定指令获取信息。
- **指令映射**：
  - 回复"BALANCE"或"1" → 返回剩余天数
  - 回复"HELP"或"2" → 返回客服电话
  - 回复"TOKEN"或"3" → 若已还款未收到Token，触发补发

#### FR-COM-003：MQTT通信
- **优先级**：P0
- **描述**：设备与平台的双向通信通道。
- **Broker**：EMQX Enterprise（部署于AWS EKS）
- **主题规范**：
  - 设备上报：`devices/{serial}/telemetry`（遥测数据）
  - 设备属性：`devices/{serial}/attributes`（固件版本、硬件版本、IMEI等）
  - 平台下发指令：`devices/{serial}/commands`（Token同步、OTA升级、远程锁定/解锁）
- **QoS**：遥测数据QoS 0（允许丢失），指令下发QoS 1（确保送达）
- **Retain**：commands主题启用Retain Flag，设备上线后立即收到最新指令

#### FR-COM-004：语音外呼（预留）
- **优先级**：P2
- **描述**：逾期提醒可录制高棉语语音，通过自动外呼系统拨打。
- **预留接口**：与Twilio或本地语音服务商对接

---

## 5. 非功能需求

### 5.1 性能需求

| 需求编号 | 指标 | 目标值 | 测试方法 |
|:---|:---|:---|:---|
| NFR-PER-001 | Token生成API响应时间 | P99 < 100ms | Locust压测，100并发 |
| NFR-PER-002 | Token验证API响应时间 | P99 < 50ms | Locust压测，200并发 |
| NFR-PER-003 | MQTT消息处理吞吐量 | ≥10,000 msg/s | 模拟1,000台设备并发上报 |
| NFR-PER-004 | 运营后台页面加载时间 | P99 < 2s | Lighthouse性能审计 |
| NFR-PER-005 | 报表导出（1万条记录） | < 30s | 实际导出计时 |
| NFR-PER-006 | 数据库查询（设备列表） | P99 < 500ms | 百万级数据量测试 |

### 5.2 安全需求

| 需求编号 | 描述 | 实现方式 |
|:---|:---|:---|
| NFR-SEC-001 | Secret Key加密存储 | AWS KMS生成DEK，AES-256-GCM加密，密文存PostgreSQL |
| NFR-SEC-002 | Token不可逆存储 | Token字段bcrypt哈希存储，原始Token仅存在于SMS发送瞬间 |
| NFR-SEC-003 | API认证 | JWT Token，有效期15分钟，Refresh Token 7天，支持强制失效 |
| NFR-SEC-004 | 传输加密 | 全站HTTPS（TLS 1.3），MQTT over TLS 1.3 + mTLS |
| NFR-SEC-005 | 输入校验 | 所有接口防SQL注入、XSS、CSRF，参数长度/类型/范围校验 |
| NFR-SEC-006 | 权限控制 | RBAC模型，接口级权限注解，操作审计日志 |
| NFR-SEC-007 | 防重放攻击 | Token Counter单调递增，API请求带时间戳签名（5分钟窗口） |
| NFR-SEC-008 | 密钥轮换 | Secret Key支持定期轮换（每12个月），轮换过程设备不中断服务 |
| NFR-SEC-009 | 渗透测试 | 上线前第三方安全公司黑盒测试，修复所有高危漏洞 |

### 5.3 可靠性需求

| 需求编号 | 描述 | 目标值 |
|:---|:---|:---|
| NFR-REL-001 | 系统可用性 | ≥99.5%（年度停机时间<43.8小时） |
| NFR-REL-002 | Token服务可用性 | ≥99.9%（独立部署，故障隔离） |
| NFR-REL-003 | 数据持久化 | RDS多可用区部署，自动备份，RPO<5分钟 |
| NFR-REL-004 | 灾难恢复 | RTO<4小时（数据库从备份恢复），RPO<1小时 |
| NFR-REL-005 | 故障自愈 | 容器健康检查失败自动重启，API网关自动剔除异常实例 |

### 5.4 可扩展性需求

| 需求编号 | 描述 | 目标值 |
|:---|:---|:---|
| NFR-SCA-001 | 设备并发在线 | 首期200套，1年内2,000套，3年内10,000套 |
| NFR-SCA-002 | 支付并发处理 | ≥50笔/秒 |
| NFR-SCA-003 | 微服务横向扩展 | 各服务支持独立扩缩容，Kubernetes HPA自动伸缩 |
| NFR-SCA-004 | 多MFI接入 | 架构支持同时接入≥5家MFI，每家MFI独立适配器 |

### 5.5 本地化需求

| 需求编号 | 描述 | 实现方式 |
|:---|:---|:---|
| NFR-LOC-001 | 高棉语界面 | 运营后台、App、客户门户全面支持高棉语（Unicode） |
| NFR-LOC-002 | 多语言切换 | 高棉语、中文、英文三种语言，用户偏好自动记忆 |
| NFR-LOC-003 | 高棉语SMS | SMS模板支持高棉语，单条70字符Unicode限制 |
| NFR-LOC-004 | 时区处理 | 全平台使用Asia/Phnom_Penh时区（UTC+7），夏令时不调整 |
| NFR-LOC-005 | 日期格式 | 支持高棉历与公历双显示（可选），默认公历DD/MM/YYYY |
| NFR-LOC-006 | 数字格式 | 高棉语数字（០-៩）与阿拉伯数字双支持 |

### 5.6 兼容性需求

| 需求编号 | 描述 | 目标值 |
|:---|:---|:---|
| NFR-COM-001 | 浏览器兼容 | Chrome/Edge/Safari/Firefox最新2个主版本 |
| NFR-COM-002 | Mobile App兼容 | Android 8.0+，iOS 14+ |
| NFR-COM-003 | 网络兼容 | 支持4G/3G/2G自动降级，弱网环境下核心功能可用 |
| NFR-COM-004 | 设备兼容 | 支持Victron+Dongle、国产+自研板、PayGo Switch三种硬件方案 |

---

## 6. 核心业务流程

### 6.1 主流程：客户还款→Token解锁全流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 客户还款  │───→│ MFI CBS  │───→│ 平台适配器│───→│ 支付验证  │───→│ Token生成 │───→│ SMS下发  │
│          │    │ 记录还款  │    │ 同步数据  │    │ 对账确认  │    │ 加密签名  │    │ 15位数字 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                                                      │
                                                                                      ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 设备解锁  │←───│ Dongle   │←───│ 设备输入  │←───│ 客户收到  │←───│ 手机接收  │←───│ 送达确认  │
│ 恢复供电  │    │ 验证通过 │    │ Token    │    │ SMS      │    │ SMS      │    │ 平台记录  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

**流程说明**：
1. 客户通过Bakong扫码、MFI App转账或柜台现金完成还款
2. MFI CBS记录还款，通过适配器同步至PAYGO平台
3. 平台验证还款金额与合同匹配，触发Token生成
4. 平台通过SMS网关发送15位数字Token至客户手机
5. 客户在Dongle键盘输入Token
6. Dongle本地验证Token有效性（AES解密+Counter校验）
7. 验证通过后闭合继电器，恢复供电，同时通过MQTT上报平台

### 6.2 异常流程：逾期锁定

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 逾期检测  │───→│ 宽限期管理│───→│ 锁定决策  │───→│ 指令下发  │───→│ 设备断电  │
│ CBS同步   │    │ 3天宽限期 │    │ 逾期>7天  │    │ LIMIT_50%│    │ 限制输出  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
       │                                                              │
       ▼                                                              ▼
┌──────────┐                                                  ┌──────────┐
│ SMS通知   │                                                  │ 持续逾期  │
│ 客户+MFI │                                                  │ >30天    │
└──────────┘                                                  │ 完全锁定  │
                                                              └──────────┘
```

**流程说明**：
1. 每日凌晨同步MFI CBS逾期状态
2. 逾期1-3天：仅SMS提醒，不锁定（宽限期）
3. 逾期4-7天：SMS警告 + MFI催收任务
4. 逾期>7天：平台下发限制输出指令（如限制逆变器输出50%）
5. 逾期>30天：完全锁定（发送SET_TIME 0或DISABLE_PAYG）
6. 客户结清后：MFI CBS更新状态 → 平台自动解锁 → 发送ADD_TIME Token

### 6.3 异常流程：Token补发

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 客户未收到│───→│ 联系客服  │───→│ 运营核实  │───→│ 主管审批  │───→│ 生成新Token│
│ SMS未送达 │    │ 电话/WhatsApp│   │ 原Token状态│   │ 补发原因  │    │ Counter+1 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
       │                                                              │
       ▼                                                              ▼
┌──────────┐                                                  ┌──────────┐
│ 记录补发  │                                                  │ SMS重发  │
│ 审计日志  │                                                  │ 标记原Token│
│           │                                                  │ SUPERSEDED│
└──────────┘                                                  └──────────┘
```

### 6.4 异常流程：设备被盗追踪

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ GPS偏移   │───→│ 平台告警  │───→│ 人工核实  │───→│ 确认被盗  │───→│ 远程锁定  │
│ >500米   │    │ ALM-003  │    │ 联系客户  │    │ 排除误报  │    │ 完全断电  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
       │                                                              │
       ▼                                                              ▼
┌──────────┐                                                  ┌──────────┐
│ 通知警方  │                                                  │ 追踪轨迹  │
│ +MFI     │                                                  │ 持续上报GPS│
└──────────┘                                                  └──────────┘
```

---

## 7. 数据需求

### 7.1 核心实体关系

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Customer   │◄─────►│  Contract   │◄─────►│   Device    │◄─────►│    Token    │
│   客户      │  1:N   │   合同      │  1:1   │   设备      │  1:N   │   Token     │
└─────────────┘       └─────────────┘       └─────────────┘       └─────────────┘
       │                    │                      │
       │                    │                      │
       ▼                    ▼                      ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ Repayment   │       │  MFI_Branch │       │  Alert/工单  │
│   还款记录   │       │   MFI支行   │       │   告警      │
└─────────────┘       └─────────────┘       └─────────────┘
```

### 7.2 数据字典（核心表）

#### 7.2.1 devices（设备表）

| 字段名 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| serial_number | VARCHAR(32) | PK | 设备唯一序列号 |
| secret_key | BYTEA | NOT NULL | AES-256-GCM加密后的Secret Key |
| token_counter | INTEGER | NOT NULL, DEFAULT 0 | 当前Token Counter |
| model | VARCHAR(50) | NOT NULL | 设备型号 |
| capacity_kw | DECIMAL(5,2) | NOT NULL | 系统功率（kW） |
| firmware_version | VARCHAR(20) | | 固件版本 |
| hardware_version | VARCHAR(20) | | 硬件版本 |
| imei | VARCHAR(20) | UNIQUE | GSM模块IMEI |
| imsi | VARCHAR(20) | | SIM卡IMSI |
| gps_latitude | DECIMAL(10,8) | | 安装纬度 |
| gps_longitude | DECIMAL(11,8) | | 安装经度 |
| installation_address | TEXT | | 安装地址（高棉语/英文） |
| customer_id | UUID | FK | 关联客户 |
| contract_id | UUID | FK | 关联合同 |
| mfi_branch_id | UUID | FK | 关联MFI支行 |
| payg_enabled | BOOLEAN | DEFAULT TRUE | PAYGO功能开关 |
| lock_status | VARCHAR(20) | DEFAULT 'UNLOCKED' | 锁定状态 |
| remaining_days | INTEGER | DEFAULT 0 | 剩余使用天数 |
| last_communication | TIMESTAMP | | 最后通信时间 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

#### 7.2.2 token_audit_log（Token审计日志表）

| 字段名 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | UUID | PK | 唯一ID |
| device_serial | VARCHAR(32) | FK, INDEX | 设备序列号 |
| token_type | VARCHAR(20) | NOT NULL | ADD_TIME/SET_TIME/DISABLE_PAYG/COUNTER_SYNC |
| token_hash | VARCHAR(255) | NOT NULL | bcrypt哈希值 |
| counter | INTEGER | NOT NULL | 使用的Counter值 |
| days | INTEGER | | 增加/设置的天数 |
| generated_at | TIMESTAMP | NOT NULL | 生成时间 |
| generated_by | UUID | FK | 操作人ID（系统触发为NULL） |
| ip_address | INET | | 操作人IP |
| user_agent | TEXT | | 客户端信息 |
| payment_id | UUID | FK | 关联还款记录 |
| status | VARCHAR(20) | DEFAULT 'UNUSED' | UNUSED/USED/SUPERSEDED |

#### 7.2.3 customers（客户表）

| 字段名 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | UUID | PK | 唯一ID |
| mfi_customer_id | VARCHAR(50) | UNIQUE | MFI系统中的客户ID |
| name | VARCHAR(100) | NOT NULL | 客户姓名（高棉语/英文） |
| phone | VARCHAR(20) | NOT NULL, UNIQUE | 手机号（柬埔寨格式：+855...） |
| email | VARCHAR(100) | | 邮箱 |
| id_number | VARCHAR(50) | UNIQUE | 身份证号/护照号 |
| address | TEXT | | 居住地址 |
| credit_score | INTEGER | | MFI信用评分 |
| mfi_branch_id | UUID | FK | 所属MFI支行 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### 7.2.4 contracts（合同表）

| 字段名 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | UUID | PK | 唯一ID |
| mfi_contract_id | VARCHAR(50) | UNIQUE | MFI系统中的合同ID |
| customer_id | UUID | FK, INDEX | 客户ID |
| device_serial | VARCHAR(32) | FK, UNIQUE | 设备序列号 |
| loan_amount | DECIMAL(12,2) | NOT NULL | 贷款金额（USD） |
| interest_rate | DECIMAL(5,2) | NOT NULL | 年利率（%） |
| term_months | INTEGER | NOT NULL | 贷款期限（月） |
| monthly_payment | DECIMAL(10,2) | NOT NULL | 月还款额 |
| start_date | DATE | NOT NULL | 合同生效日 |
| status | VARCHAR(20) | DEFAULT 'PENDING' | PENDING/ACTIVE/CLOSED/DEFAULTED |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### 7.2.5 repayments（还款记录表）

| 字段名 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| id | UUID | PK | 唯一ID |
| mfi_repayment_id | VARCHAR(50) | UNIQUE | MFI系统中的还款ID |
| contract_id | UUID | FK, INDEX | 合同ID |
| amount | DECIMAL(10,2) | NOT NULL | 还款金额 |
| currency | VARCHAR(3) | DEFAULT 'USD' | 币种 |
| payment_date | TIMESTAMP | NOT NULL | 还款时间 |
| transaction_id | VARCHAR(100) | UNIQUE | 交易流水号 |
| payment_method | VARCHAR(20) | NOT NULL | CASH/BANK_TRANSFER/Bakong |
| token_generated | BOOLEAN | DEFAULT FALSE | 是否已生成Token |
| token_id | UUID | FK | 关联Token记录 |

### 7.3 数据量估算

| 数据类型 | 单条大小 | 首期200套/年 | 1年2,000套 | 3年10,000套 |
|:---|:---|:---|:---|:---|
| 设备遥测 | ~500B | 52MB/年 | 520MB/年 | 2.6GB/年 |
| Token审计日志 | ~2KB | 4.8MB/年 | 48MB/年 | 240MB/年 |
| 还款记录 | ~1KB | 2.4MB/年 | 24MB/年 | 120MB/年 |
| 告警记录 | ~1KB | 1MB/年 | 10MB/年 | 50MB/年 |
| 照片/文件 | ~2MB | 400GB/年 | 4TB/年 | 20TB/年 |

**存储策略**：结构化数据存PostgreSQL，文件/照片存S3（生命周期：1年后转低频存储，3年后归档）

---

## 8. 接口需求

### 8.1 内部微服务接口（REST API）

#### Token Service API

| 方法 | 路径 | 描述 | 认证 |
|:---|:---|:---|:---|
| POST | /api/v1/tokens/generate | 生成Token | JWT |
| POST | /api/v1/tokens/validate | 验证Token | API Key（设备端） |
| GET | /api/v1/tokens/history/{serial} | 查询Token历史 | JWT |
| POST | /api/v1/tokens/batch-generate | 批量生成Token | JWT |
| POST | /api/v1/tokens/reissue | 补发Token | JWT |

#### Device Service API

| 方法 | 路径 | 描述 | 认证 |
|:---|:---|:---|:---|
| POST | /api/v1/devices/register | 设备注册 | JWT |
| GET | /api/v1/devices/{serial} | 设备详情 | JWT |
| GET | /api/v1/devices/{serial}/status | 实时状态 | JWT |
| POST | /api/v1/devices/{serial}/commands | 下发指令 | JWT |
| POST | /api/v1/devices/ota | OTA升级 | JWT |

#### Payment Service API

| 方法 | 路径 | 描述 | 认证 |
|:---|:---|:---|:---|
| POST | /api/v1/payments/khqr | 生成KHQR | JWT |
| POST | /webhooks/bakong | Bakong回调 | HMAC签名 |
| POST | /api/v1/payments/cash | 现金还款录入 | JWT |
| GET | /api/v1/payments/reconciliation | 对账查询 | JWT |

#### MFI Adapter API

| 方法 | 路径 | 描述 | 认证 |
|:---|:---|:---|:---|
| POST | /api/v1/mfi/sync/customers | 同步客户 | JWT + MFI证书 |
| POST | /api/v1/mfi/sync/contracts | 同步合同 | JWT + MFI证书 |
| POST | /api/v1/mfi/sync/repayments | 同步还款 | JWT + MFI证书 |
| GET | /api/v1/mfi/sync/status | 同步状态 | JWT |

### 8.2 外部接口

#### Bakong API（柬埔寨国家银行）
- **接口文档**：Bakong API Developer Guide v2.0
- **认证方式**：API Key + HMAC-SHA256签名
- **核心接口**：
  - `POST /v1/payments/initiate`：发起支付
  - `GET /v1/payments/{id}`：查询支付状态
  - `POST /v1/khqr/generate`：生成KHQR码
  - Webhook：`POST /webhooks/bakong`（平台提供，Bakong调用）

#### SMS网关接口（Cellcard/Smart）
- **协议**：SMPP v3.4
- **连接方式**：TCP长连接，bind_transmitter
- **编码**：高棉语使用UCS-2，英文使用GSM 7-bit
- **送达报告**：启用delivery receipt，平台异步更新SMS状态

#### MQTT接口（设备通信）
- **Broker**：EMQX Enterprise，端口8883（TLS）
- **认证**：设备证书mTLS + 用户名密码（双重认证）
- **Payload格式**：JSON，UTF-8编码
- **心跳间隔**：300秒

---

## 9. 合规与法规需求

### 9.1 NBC（柬埔寨国家银行）合规

| 需求编号 | 描述 | 优先级 |
|:---|:---|:---|
| REG-NBC-001 | 作为MFI技术服务商，向NBC报备系统架构、数据存储位置、接口规范 | P0 |
| REG-NBC-002 | 客户敏感数据（身份信息、还款记录）存储于柬埔寨境内或经NBC批准的跨境数据中心 | P0 |
| REG-NBC-003 | 提供完整审计日志供NBC检查，保留期限≥7年 | P0 |
| REG-NBC-004 | Bakong支付对接需通过NBC安全评估，获取正式接入许可 | P0 |

### 9.2 消费者保护合规

| 需求编号 | 描述 | 优先级 |
|:---|:---|:---|
| REG-CST-001 | SMS提醒必须包含MFI名称、客服电话、投诉渠道 | P0 |
| REG-CST-002 | 设备锁定前必须提前3天发送警告通知 | P0 |
| REG-CST-003 | 提供高棉语客户投诉渠道（电话、WhatsApp、在线表单） | P0 |
| REG-CST-004 | 客户数据使用需获得明确授权，支持数据导出与删除请求 | P1 |

### 9.3 数据隐私合规

| 需求编号 | 描述 | 优先级 |
|:---|:---|:---|
| REG-DAT-001 | 符合柬埔寨《电子商务法》数据保护条款 | P0 |
| REG-DAT-002 | 客户数据加密存储，传输全程TLS加密 | P0 |
| REG-DAT-003 | 内部员工访问客户数据需审批并记录审计日志 | P0 |
| REG-DAT-004 | 数据跨境传输需NBC批准，优先本地化存储 | P1 |

### 9.4 设备进口合规

| 需求编号 | 描述 | 优先级 |
|:---|:---|:---|
| REG-IMP-001 | PAYGO控制板/太阳能设备进口柬埔寨需办理IEC（进口电子证书） | P0 |
| REG-IMP-002 | 缴纳进口关税，保留报关单据备查 | P0 |
| REG-IMP-003 | 设备符合柬埔寨电力标准（220V/50Hz） | P0 |

---

## 10. 附录

### 附录A：需求优先级定义

| 优先级 | 定义 | 处理策略 |
|:---|:---|:---|
| P0 | 核心需求，缺失则系统无法上线 | 必须在MVP阶段完成 |
| P1 | 重要需求，缺失影响用户体验或运营效率 | 在V1.1-V1.2阶段完成 |
| P2 | 增强需求，缺失不影响核心功能 | 在V2.0阶段或后续迭代考虑 |

### 附录B：硬件方案兼容性矩阵

| 硬件方案 | Token验证方式 | MQTT支持 | OTA支持 | 适配优先级 |
|:---|:---|:---|:---|:---|
| A: Victron + Solarworx Dongle | Dongle本地验证 | 是（VE.Direct转MQTT） | 是 | P0 |
| B: 国产逆变器 + 自研ESP32板 | 控制板本地验证 | 是（原生MQTT） | 是 | P0 |
| C: Solarworx PayGo Switch | Switch本地验证 | 否（仅SMS上报） | 否 | P1 |

### 附录C：MFI对接优先级

| MFI名称 | 优先级 | 关键切入点 | 预计对接周期 |
|:---|:---|:---|:---|
| LOLC Cambodia | 第一优先 | ESG债券、绿色贷款、83个分支 | 2-3个月 |
| PRASAC | 第二优先 | 绿色贷款先驱、农村覆盖、180+分支 | 2-3个月 |
| ACLEDA Bank | 第三优先 | 最大商业银行、资金实力雄厚 | 3-4个月 |
| AMK Microfinance | 第四优先 | 深厚农村根基、数字化程度高 | 3-4个月 |
| Amret Microfinance | 第五优先 | 女性客户比例高、覆盖广泛 | 4-6个月 |

### 附录D：柬埔寨移动网络APN配置

| 运营商 | APN | 4G频段 | SMS网关 |
|:---|:---|:---|:---|
| Smart Axiata | smart.com.kh | B1/B3/B7/B8/B28 | SMPP企业网关 |
| Cellcard | cellcard.com.kh | B1/B3/B7/B8/B28 | SMPP企业网关（推荐） |
| Metfone | metfone.com.kh | B1/B3/B8 | 企业短信API |

---

**— 本文档为新华智科技（柬埔寨）有限公司内部机密 —**
**编制日期：2026年5月20日**
