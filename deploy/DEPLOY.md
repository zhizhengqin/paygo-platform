# PAYGO Solar Platform — 生产部署手册

---

## 目录

1. [VPS 选购与推荐](#1-vps-选购与推荐)
2. [VPS 初始配置](#2-vps-初始配置)
3. [域名与 DNS](#3-域名与-dns)
4. [安装 Docker](#4-安装-docker)
5. [部署项目](#5-部署项目)
6. [验证部署](#6-验证部署)
7. [日常运维](#7-日常运维)
8. [数据库备份](#8-数据库备份)
9. [故障排查](#9-故障排查)
10. [安全加固](#10-安全加固)

---

## 1. VPS 选购与推荐

### 推荐方案

| 服务商 | 产品 | 配置 | 月费 | 机房 | 推荐场景 |
|--------|------|------|------|------|----------|
| **Hetzner** | CX22 | 2 vCPU / 4GB RAM / 40GB SSD | ~€4.5 | 新加坡/德国 | 性价比最高 |
| **AWS Lightsail** | $10 Plan | 1 vCPU / 2GB RAM / 60GB SSD | $10/月 | 新加坡 | 柬埔寨延迟最低 |
| **Vultr** | Regular | 1 vCPU / 2GB RAM / 55GB SSD | $12/月 | 新加坡 | 稳定可靠 |

> **推荐 Hetzner CX22 新加坡节点**：4GB 内存跑 PostgreSQL + Redis + App 绰绰有余，月费 ~€4.5（约 ¥35），性价比无人能敌。

### 选购步骤（以 Hetzner 为例）

1. 注册 [hetzner.com](https://www.hetzner.com/cloud)
2. Create Server → Location: **Singapore** → Image: **Ubuntu 24.04**
3. Type: **CX22**（2 vCPU / 4GB / 40GB）
4. SSH key：上传你的公钥（`~/.ssh/id_ed25519.pub`）
5. 创建后获得 **VPS IP 地址**，记下来

---

## 2. VPS 初始配置

SSH 登录：

```bash
ssh root@<你的VPS-IP>
```

### 2.1 更新系统

```bash
apt update && apt upgrade -y
```

### 2.2 创建非 root 用户

```bash
adduser deploy
usermod -aG sudo deploy
```

### 2.3 配置 SSH（安全加固）

编辑 `/etc/ssh/sshd_config`：

```bash
# 禁用 root 登录
PermitRootLogin no
# 禁用密码登录（仅用密钥）
PasswordAuthentication no
```

重启 SSH：

```bash
systemctl restart sshd
```

> 重新登录测试：`ssh deploy@<VPS-IP>`，确认可用后再关闭 root 窗口。

### 2.4 防火墙

```bash
# 安装 ufw
apt install ufw -y

# 允许 SSH / HTTP / HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# 启用
ufw enable

# 验证
ufw status verbose
```

### 2.5 时区设置

```bash
timedatectl set-timezone Asia/Phnom_Penh
```

---

## 3. 域名与 DNS

### 3.1 获取域名

任意域名注册商均可（Namecheap、Cloudflare、阿里云万网）。

### 3.2 配置 DNS

在域名 DNS 管理页面添加一条 **A 记录**：

| 类型 | 主机记录 | 记录值 |
|------|----------|--------|
| A | `@`（或你的子域名如 `paygo`） | **VPS IP 地址** |
| A | `www` | **VPS IP 地址**（可选） |

> DNS 生效可能需要几分钟到几小时。用 `dig your-domain.com` 检查。

---

## 4. 安装 Docker

以 `deploy` 用户登录，执行官方安装脚本：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

退出重新登录使 docker 组生效：

```bash
exit
ssh deploy@<VPS-IP>
```

验证：

```bash
docker --version
docker compose version
# Docker version 27.x.x
# Docker Compose version v2.x.x
```

---

## 5. 部署项目

### 5.1 拉取代码

```bash
git clone https://github.com/<你的仓库>/paygo-platform.git
cd paygo-platform
```

> 如果仓库是私有的，先配置 SSH key 或使用 Personal Access Token。

### 5.2 配置环境变量

```bash
cp deploy/.env.example deploy/.env
nano deploy/.env
```

修改以下两项：

```ini
DOMAIN=paygo.your-domain.com    # 你的真实域名
DB_PASSWORD=你的强密码           # 数据库密码，例如: Xk9#mP2$vL7@qW
```

### 5.3 一键部署

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

或手动执行：

```bash
# 构建镜像
docker compose -f deploy/docker-compose.yml build --pull

# 启动所有服务（后台运行）
docker compose -f deploy/docker-compose.yml up -d

# 查看运行状态
docker compose -f deploy/docker-compose.yml ps
```

预期输出 4 个服务都是 `Up` + `healthy`：

```
NAME             STATUS
paygo-app        Up (healthy)
paygo-postgres   Up (healthy)
paygo-redis      Up (healthy)
paygo-caddy      Up
```

### 5.4 首次访问

打开浏览器访问 `https://你的域名/dashboard`。

- Caddy 会自动向 Let's Encrypt 申请 SSL 证书（首次可能需要 10-30 秒）
- 登录账号：`admin` / `admin123`
- 数据库表已自动创建，支付汇率数据已种子

---

## 6. 验证部署

### 6.1 HTTP → HTTPS 重定向

```bash
curl -I http://你的域名
# HTTP/1.1 308 Permanent Redirect → https://...
```

### 6.2 API 接口

```bash
# 登录
curl -c /tmp/cookies.txt -X POST \
  -d "username=admin&password=admin123" \
  https://你的域名/login

# 查看客户列表
curl -b /tmp/cookies.txt https://你的域名/api/customers
```

### 6.3 查看日志

```bash
docker compose -f deploy/docker-compose.yml logs -f app
```

---

## 7. 日常运维

### 常用命令

```bash
# 查看所有服务状态
docker compose -f deploy/docker-compose.yml ps

# 查看应用日志（实时）
docker compose -f deploy/docker-compose.yml logs -f app

# 查看 PostgreSQL 日志
docker compose -f deploy/docker-compose.yml logs -f postgres

# 重启单个服务
docker compose -f deploy/docker-compose.yml restart app

# 停止所有服务
docker compose -f deploy/docker-compose.yml down

# 更新代码后重新部署
git pull
docker compose -f deploy/docker-compose.yml build app
docker compose -f deploy/docker-compose.yml up -d app
```

### 更新部署

```bash
cd ~/paygo-platform
git pull
docker compose -f deploy/docker-compose.yml up -d --build app
# 旧镜像清理
docker image prune -f
```

### 查看资源占用

```bash
docker stats
```

---

## 8. 数据库备份

### 8.1 手动备份

```bash
# 导出 SQL
docker exec paygo-postgres pg_dump -U paygo_user paygo_platform > backup_$(date +%Y%m%d).sql

# 压缩
gzip backup_$(date +%Y%m%d).sql
```

### 8.2 恢复

```bash
gunzip backup_20260519.sql.gz
docker exec -i paygo-postgres psql -U paygo_user paygo_platform < backup_20260519.sql
```

### 8.3 自动备份（crontab）

```bash
crontab -e
```

添加（每天凌晨 3 点备份，保留最近 7 天）：

```
0 3 * * * docker exec paygo-postgres pg_dump -U paygo_user paygo_platform | gzip > ~/backups/paygo_$(date +\%Y\%m\%d).sql.gz && find ~/backups -name '*.sql.gz' -mtime +7 -delete
```

创建备份目录：

```bash
mkdir -p ~/backups
```

### 8.4 异地备份（可选）

将备份文件同步到 S3 或其他存储：

```bash
# 使用 rclone 或 scp
scp ~/backups/paygo_*.sql.gz user@backup-server:/backups/
```

---

## 9. 故障排查

### 9.1 服务未启动

```bash
# 查看全部容器状态（包括已停止的）
docker compose -f deploy/docker-compose.yml ps -a

# 查看具体错误
docker compose -f deploy/docker-compose.yml logs postgres
docker compose -f deploy/docker-compose.yml logs app
```

### 9.2 数据库连接失败

```bash
# 检查 postgres 是否健康
docker exec paygo-postgres pg_isready -U paygo_user

# 检查 app 能否连接 postgres
docker exec paygo-app python -c "
import asyncpg, asyncio
asyncio.run(asyncpg.connect('postgresql://paygo_user:你的密码@postgres:5432/paygo_platform'))
"
```

### 9.3 SSL 证书问题

```bash
# 检查 Caddy 日志
docker compose -f deploy/docker-compose.yml logs caddy

# 常见原因：
# - 域名 DNS 未指向 VPS IP
# - 80/443 端口被防火墙拦截
# - Let's Encrypt 频率限制（测试环境可先用 http://）
```

### 9.4 内存不足

```bash
# 限制 PostgreSQL 内存（编辑 docker-compose.yml 的 postgres 服务）
# 添加 command:
#   - "postgres"
#   - "-c"
#   - "shared_buffers=256MB"
#   - "-c"
#   - "effective_cache_size=768MB"
```

### 9.5 完全重置

```bash
# 停止并删除所有容器和卷
docker compose -f deploy/docker-compose.yml down -v

# 重新部署
./deploy/deploy.sh
```

---

## 10. 安全加固

### 10.1 数据库密码

- 不要使用默认密码 `PaygoDB2026!`
- 生成强密码：`openssl rand -base64 32`

### 10.2 系统更新

```bash
# 定期更新
sudo apt update && sudo apt upgrade -y

# 定期更新 Docker 镜像
docker compose -f deploy/docker-compose.yml pull
docker compose -f deploy/docker-compose.yml up -d
```

### 10.3 管理员密码

登录后台后立即修改默认密码 `admin123`（通过 API 或直接在数据库修改）。

### 10.4 Fail2Ban（可选）

```bash
sudo apt install fail2ban -y
# 默认配置已保护 SSH
```

### 10.5 监控建议

- **Uptime 监控**：UptimeRobot（免费，5 分钟间隔）
- **资源监控**：`htop` + `docker stats`
- **日志聚合**：后续可接入 Grafana Loki

---

## 附录：架构总览

```
                         Internet
                            │
                    ┌───────▼───────┐
                    │   Caddy :443   │  ← 自动 Let's Encrypt SSL
                    │  (反向代理)    │
                    └───────┬───────┘
                            │ :8000
                    ┌───────▼───────┐
                    │  FastAPI App   │
                    │  (Uvicorn x2)  │
                    └───┬─────┬─────┘
                        │     │
              ┌─────────▼┐  ┌─▼─────────┐
              │PostgreSQL│  │  Redis 8   │
              │   15     │  │  (session  │
              │ (数据卷)  │  │  + cache)  │
              └──────────┘  └────────────┘
```

| 组件 | 镜像 | 内部端口 | 外部暴露 |
|------|------|----------|----------|
| Caddy | `caddy:2-alpine` | 80, 443 | **是** (80, 443) |
| App | `paygo-app:latest` | 8000 | 否 |
| PostgreSQL | `postgres:15-alpine` | 5432 | 否 |
| Redis | `redis:8-alpine` | 6379 | 否 |

> PostgreSQL 和 Redis 仅在内网 `internal` bridge 网络暴露，外网无法直接访问。
