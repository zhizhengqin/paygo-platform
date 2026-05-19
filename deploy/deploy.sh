#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────
# PAYGO Solar Platform — 一键部署脚本
# 适用：Debian 12 / Ubuntu 24.04
# ──────────────────────────────────────────

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}┌──────────────────────────────────────┐${NC}"
echo -e "${GREEN}│  PAYGO Platform — Deploy Script      │${NC}"
echo -e "${GREEN}└──────────────────────────────────────┘${NC}"

# ── 1. 检查 .env 文件 ──
if [ ! -f deploy/.env ]; then
    echo -e "${YELLOW}[!] deploy/.env 不存在，正在从 .env.example 创建...${NC}"
    cp deploy/.env.example deploy/.env
    echo -e "${YELLOW}[!] 请编辑 deploy/.env，填入你的 DOMAIN 和 DB_PASSWORD 后重新运行本脚本${NC}"
    exit 1
fi

# ── 2. 安装 Docker（如未安装） ──
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}[1/4] 安装 Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo -e "${YELLOW}[!] 已将当前用户加入 docker 组，如提示权限不足请重新登录或运行: newgrp docker${NC}"
fi

# ── 3. 构建并启动 ──
echo -e "${GREEN}[2/4] 构建镜像...${NC}"
docker compose -f deploy/docker-compose.yml build --pull

echo -e "${GREEN}[3/4] 启动服务...${NC}"
docker compose -f deploy/docker-compose.yml up -d

# ── 4. 等待健康检查通过 ──
echo -e "${GREEN}[4/4] 等待服务就绪...${NC}"
sleep 3
docker compose -f deploy/docker-compose.yml ps

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}  访问: https://\$(grep DOMAIN deploy/.env | cut -d= -f2)${NC}"
echo -e "${GREEN}  登录: admin / admin123${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "常用命令:"
echo "  查看日志:   docker compose -f deploy/docker-compose.yml logs -f app"
echo "  重启服务:   docker compose -f deploy/docker-compose.yml restart app"
echo "  停止全部:   docker compose -f deploy/docker-compose.yml down"
echo "  备份数据库: docker exec paygo-postgres pg_dump -U paygo_user paygo_platform > backup.sql"
