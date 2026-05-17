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

## 核心业务流程
1. 客户通过MFI申请太阳能贷款
2. MFI审批通过后，安装团队上门安装太阳能系统
3. 系统安装完成后，客户在设备上输入Starting Code首次激活
4. 客户每月通过Bakong/MFI App还款
5. 平台收到还款后，自动生成ADD_TIME Token（延长使用天数）
6. Token通过SMS发送给客户，客户在设备键盘输入Token解锁
7. 逾期超过30天，设备自动锁定（发电量归零）
8. 贷款结清后，生成DISABLE_PAYG Token永久解锁设备

## 技术栈
- 后端框架：Python FastAPI
- Token库：openpaygo（OpenPAYGO Token开源库）
- 前端：HTML + JavaScript + Bootstrap 5（CDN）
- 数据库：内存数据库（原型阶段），后续迁移至PostgreSQL
- 部署：Render（后端）+ Vercel（前端）

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
│   ├── main.py              # FastAPI主应用入口
│   ├── models.py            # Pydantic数据模型
│   ├── database.py          # 内存数据库
│   └── routers/
│       ├── __init__.py
│       ├── tokens.py        # Token生成服务
│       ├── devices.py       # 设备管理接口
│       └── payments.py      # 支付回调接口
├── static/
│   └── dashboard.html       # 运营后台页面
├── tests/
│   ├── __init__.py
│   ├── test_tokens.py       # Token服务测试
│   ├── test_devices.py      # 设备管理测试
│   ├── test_payments.py     # 支付服务测试
│   └── conftest.py          # 测试夹具
├── skills/                  # Superpowers技能
├── docs/superpowers/
│   ├── plans/               # 开发计划
│   └── specs/               # 规格文档
├── device_simulator.py      # 设备模拟器
├── requirements.txt         # Python依赖
├── .env                     # 环境变量
├── .gitignore              # Git忽略规则
├── README.md               # 项目说明
├── CLAUDE.md               # 本文件
└── AGENTS.md               # 代理角色定义
```

## 开发规范
- 强制TDD：每个功能必须有先失败的测试，再写实现代码
- 代码注释使用中文
- API接口返回中文错误信息
- 所有接口使用/api/v1/前缀
- Token类型：ADD_TIME（增加天数）、SET_TIME（设置天数）、DISABLE_PAYG（永久解锁）
- 测试设备密钥使用32位十六进制字符串
- 原型阶段SMS发送仅打印日志
- 每次变更后运行全部测试验证
- 每个功能完成后编写简短的中文提交信息

## 启动命令
```bash
# 开发环境启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_tokens.py -v

# 访问API文档
http://localhost:8000/docs

# 访问运营后台
http://localhost:8000/dashboard
```

## 测试设备数据
- SN-KH-001: Victron MultiPlus-II 6kW, Sokha Pich, +85512345678, 密钥dac86b1a29ab82edc5fbbc41ec9530f6
- SN-KH-002: Growatt MIN 10kW, Dara Chea, +85598765432
- SN-KH-003: ONESUN 15kW, Maly Kong, +85570123456