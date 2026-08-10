#!/bin/bash
# ==========================================================================
# VeroRun — Uninstall script
# ==========================================================================
# Usage: sudo bash deploy/uninstall.sh
# Mirrors every resource created by install.sh install, reverses them.
# Does NOT remove system packages (python3/nginx/postgresql/git).
# ==========================================================================
set -euo pipefail

APP_USER="${SUDO_USER:-$(whoami)}"
APP_HOME="${VR_APP_HOME:-}"
LOG_DIR="/var/log/verorun"
SERVICE_DIR="/etc/systemd/system"

# 审计 H-3 修复：安装支持通过环境变量自定义 APP_HOME，卸载不得硬编码默认路径。
# 优先从 systemd 服务文件解析实际 WorkingDirectory，解析失败才回退默认路径。
if [ -z "${APP_HOME}" ] && [ -f "${SERVICE_DIR}/verorun-main.service" ]; then
    APP_HOME=$(grep '^WorkingDirectory=' "${SERVICE_DIR}/verorun-main.service" 2>/dev/null | head -1 | cut -d= -f2)
fi
APP_HOME="${APP_HOME:-/home/${APP_USER}/verorun}"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"
step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash deploy/uninstall.sh"
    exit 1
fi

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  WARNING: This will remove ALL VeroRun data & services.  ║${NC}"
echo -e "${RED}║  This action is IRREVERSIBLE. Databases will be DROPPED. ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
# 审计 M8 修复：非交互一键卸载（curl | sudo bash）必须支持 VR_UNINSTALL_YES=1 跳过确认；
# 无 TTY 且未显式授权时明确报错退出（禁止 read </dev/tty 在管道下静默卡死）。
if [ "${VR_UNINSTALL_YES:-0}" = "1" ]; then
    echo -e "${INFO} VR_UNINSTALL_YES=1 — skipping confirmation"
elif [ -t 0 ]; then
    read -r -p "  Type 'yes' to confirm: " CONFIRM || CONFIRM=""
    if [ "${CONFIRM:-}" != "yes" ]; then
        echo -e "${INFO} Aborted."
        exit 0
    fi
else
    echo -e "${FAIL} Non-interactive uninstall requires VR_UNINSTALL_YES=1"
    exit 1
fi

# 1. systemd services (reverse of write_systemd_services + restart_services)
step "systemd services"
for svc in verorun-admin verorun-auth verorun-main verorun-health verorun-guardian; do
    systemctl stop "${svc}" 2>/dev/null || true
    systemctl disable "${svc}" 2>/dev/null || true
    echo "  stop/disable: ${svc}"
done
rm -f "${SERVICE_DIR}"/verorun-*.service
systemctl daemon-reload
done_step "systemd services removed"

# 2. Nginx config (reverse of write_nginx_config)
step "Nginx config"
rm -f /etc/nginx/sites-available/verorun.conf
rm -f /etc/nginx/sites-enabled/verorun.conf
if systemctl is-active --quiet nginx 2>/dev/null; then
    systemctl reload nginx 2>/dev/null || true
    echo "  nginx reloaded"
fi
done_step "Nginx config removed"

# 3. Directories (reverse of mkdir; do NOT touch the login user)
step "User & files"
# 审计 M8 修复：APP_USER 即 SSH 登录用户（如 ***REMOVED***），安装脚本从不创建系统用户，
# 原 userdel 会误删登录账号导致服务器无法再 SSH 登录。卸载只清理安装脚本创建的目录。
rm -rf "${LOG_DIR}" 2>/dev/null || true
rm -rf "${APP_HOME}" 2>/dev/null || true
done_step "User & directories cleaned"

# 4. PostgreSQL (reverse of CREATE ROLE + CREATE DATABASE)
step "PostgreSQL"
# 审计 M8 修复：先断开 appdb 上的残留连接（服务进程/守护进程占用时 DROP DATABASE 会失败），
# DROP 结果显式判断并输出可执行的手工修复命令，不再静默吞错。
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='appdb' AND pid <> pg_backend_pid()" >/dev/null 2>&1 || true
if sudo -u postgres psql -c "DROP DATABASE IF EXISTS appdb" 2>&1; then
    done_step "Database appdb dropped"
else
    echo -e "${FAIL} DROP DATABASE appdb failed — check lingering connections:"
    echo -e "${INFO}   sudo -u postgres psql -c \"SELECT pid, query FROM pg_stat_activity WHERE datname='appdb'\""
    echo -e "${INFO}   sudo -u postgres psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='appdb'\""
    echo -e "${INFO}   sudo -u postgres psql -c \"DROP DATABASE appdb\""
fi
if sudo -u postgres psql -c "DROP ROLE IF EXISTS app" 2>&1; then
    done_step "Role app dropped"
else
    echo -e "${FAIL} DROP ROLE app failed — manual command:"
    echo -e "${INFO}   sudo -u postgres psql -c \"DROP ROLE app\""
fi

# 5. Residual config files (sudoers + guardian env)
step "Config files"
rm -f /etc/default/verorun-guardian /etc/sudoers.d/verorun
done_step "Config files removed"

step "Done"
echo -e "${OK} VeroRun fully uninstalled."
echo ""
echo -e "${INFO} System packages (python3, nginx, postgresql, git) are NOT removed."
echo -e "${INFO} Server is clean. Ready for fresh install:"
echo -e "${INFO}   git clone https://github.com/fanjumin/verorun-base.git"
echo -e "${INFO}   cd verorun-base"
echo -e "${INFO}   sudo bash deploy/install.sh install your-domain.com"
