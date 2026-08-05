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
APP_HOME="/home/${APP_USER}/verorun"
LOG_DIR="/var/log/verorun"
SERVICE_DIR="/etc/systemd/system"

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
    userdel -r "${APP_USER}" 2>/dev/null || true
    echo "  user ${APP_USER} removed (home + files)"
else
    echo "  user ${APP_USER} not found"
fi
rm -rf "${APP_HOME}" "${LOG_DIR}" 2>/dev/null || true
done_step "User & directories cleaned"

# 4. PostgreSQL (reverse of CREATE ROLE + CREATE DATABASE)
step "PostgreSQL"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS verorun" 2>/dev/null || true
sudo -u postgres psql -c "DROP ROLE IF EXISTS verorun" 2>/dev/null || true
done_step "PostgreSQL database & role dropped"

step "Done"
echo -e "${OK} VeroRun fully uninstalled."
echo ""
echo -e "${INFO} System packages (python3, nginx, postgresql, git) are NOT removed."
echo -e "${INFO} Server is clean. Ready for fresh install:"
echo -e "${INFO}   git clone https://github.com/fanjumin/verorun-base.git"
echo -e "${INFO}   cd verorun-base"
echo -e "${INFO}   sudo bash deploy/install.sh install your-domain.com"
