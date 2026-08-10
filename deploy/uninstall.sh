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
read -p "  Type 'yes' to confirm: " CONFIRM </dev/tty
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${INFO} Aborted."
    exit 0
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

# 3. User & directories (reverse of useradd + mkdir)
step "User & files"
if id "${APP_USER}" &>/dev/null; then
    # 审计 M6 修复：不再用 -r 级联删除 home（改为下方显式 rm -rf 可控目录）
    if userdel "${APP_USER}" 2>/dev/null; then
        echo "  user ${APP_USER} removed"
    else
        # 审计 L-2：userdel 失败（如存在运行中进程）时明确警告，不再静默继续
        echo -e "${WARN} userdel ${APP_USER} failed (user may have running processes). Home dir will still be removed."
    fi
else
    echo "  user ${APP_USER} not found"
fi
rm -rf "${LOG_DIR}" 2>/dev/null || true
# ── Note: home dir removed below via rm -rf (userdel without -r) ──
rm -rf "${APP_HOME}" 2>/dev/null || true
done_step "User & directories cleaned"

# 4. PostgreSQL (reverse of CREATE ROLE + CREATE DATABASE)
step "PostgreSQL"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS appdb" 2>/dev/null || true
sudo -u postgres psql -c "DROP ROLE IF EXISTS app" 2>/dev/null || true
done_step "PostgreSQL database & role dropped"

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
