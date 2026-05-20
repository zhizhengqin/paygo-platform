# Final Polish: 云部署前收尾

**可实施：**
1. JWT 认证升级 — 替换 session cookie，stateless
2. API 版本化 `/api/v1/` — 统一前缀
3. 批量 Token 生成 UI — Token 管理 tab
4. 还款日历热力图 — 客户 360 视图

**不可实施：**
- Bakong/KHQR 真实支付 — 需 Bakong API 权限
- SMS SMPP 网关 — 需运营商账号
- MQTT/EMQX 设备通信 — 需硬件控制板
- AWS KMS 密钥管理 — 需 AWS 账号
- TLS/mTLS — 需域名+证书
- Flutter Mobile App — 独立项目
