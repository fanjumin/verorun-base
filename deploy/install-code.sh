#!/bin/bash
# ==========================================================================
# VeroRun — Team intranet deployment script (no domain, full plugins)
# ==========================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-pro/master/deploy/install-code.sh | sudo bash   # one-command install (pulls verorun-code, needs deploy key)
#   sudo bash deploy/install-code.sh install                     # fresh install (when .env absent)
#   sudo bash deploy/install-code.sh install --approve-migrate   # install + DB migration + seed
#   sudo bash deploy/install-code.sh update                      # update code, deps, and restart
#   sudo bash deploy/install-code.sh restart                     # restart services only
#   sudo bash deploy/install-code.sh health                      # health check
#   sudo bash deploy/install-code.sh rollback                    # rollback to previous commit
#   sudo bash deploy/install-code.sh seed                        # seed initial data
#   --skip-deps: skip system + Python dependency installation
#   --region=cn|global: region routing (default global; also supports "--region cn")
#   --approve-migrate: explicitly approve DB migration + seed on install
#
# Deploys VeroRun on a team intranet server WITHOUT a public domain:
#   http://localhost/          → main site
#   http://localhost/admin/    → admin panel
#   http://localhost/auth/     → user console
#   http://192.168.x.x/        → LAN access (same paths)
#
# Key differences vs deploy/install-dev.sh:
#   - Sparse-checkout INCLUDES plugins/ → full source with all plugins
#   - Targeted at team intranet deployment (not developer workstations)
#   - All security audit fixes are built in from the start
#
# Key differences vs deploy/install-local.sh:
#   - Pulls from verorun-code (SSH, private repo) with full plugins
#   - install-local.sh pulls from verorun-pro (HTTPS, public repo) without plugins
#
# This script does NOT modify deploy/install.sh or deploy/install-local.sh.
#
# Logic has been merged into the Development option of deploy/install.sh (build-2026.08.11+); this script is kept as a standalone shortcut entry.
#
# Limitations (expected, architecture-bound):
#   - Online payment / OAuth / SMS unavailable (require public callback URLs)
#   - Multi-tenant subdomains and SSL unavailable
# ==========================================================================
set -euo pipefail

# ── Default config ────────────────────────────────────────────────────
: "${GIT_REPO:=git@github.com:fanjumin/verorun-code.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
# Audit P1-8: home is /root when APP_USER=root (not /home/root)
if [ "${APP_USER}" = "root" ]; then
    : "${APP_HOME:=/root/verorun}"
else
    : "${APP_HOME:=/home/${APP_USER}/verorun}"
fi
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${REGION:=global}"                # cn | global

# Audit C-1: deploy mode (code) — unified functions (lib/common.sh) branch on this; must be defined before source
DEPLOY_TYPE="code"

# ── Load shared function library (lib/common.sh: logging / CN network adaptation / git / systemd / health check, etc.) ──
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
fi
if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/lib/common.sh" ]; then
    # Executed from a real file (e.g., after git clone) → load directly
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/lib/common.sh"
else
    # One-command install (curl | sudo bash): script runs from stdin, no real path
    # → fetch the shared library from verorun-pro into a temp file and load it
    _COMMON_REMOTE="${COMMON_REMOTE:-https://raw.githubusercontent.com/fanjumin/verorun-pro/master/deploy/lib/common.sh}"
    _COMMON_MIRROR="${COMMON_MIRROR:-https://cdn.jsdelivr.net/gh/fanjumin/verorun-pro@master/deploy/lib/common.sh}"
    _tmp_common="$(mktemp)"
    _ok=0
    if command -v curl >/dev/null 2>&1; then
        # Audit M-1: unified --max-time to prevent handshake hangs + --retry against transient flakiness
        if curl -sSL --connect-timeout 15 --max-time 25 --retry 3 --retry-delay 2 "${_COMMON_REMOTE}" -o "${_tmp_common}"; then _ok=1; fi
        # Official source failed (e.g., blocked by GFW) → fall back to jsdelivr CDN mirror
        if [ "${_ok}" != "1" ] && curl -sSL --connect-timeout 10 --max-time 25 --retry 3 --retry-delay 2 "${_COMMON_MIRROR}" -o "${_tmp_common}"; then _ok=1; fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --timeout=25 --tries=4 -O "${_tmp_common}" "${_COMMON_REMOTE}"; then _ok=1; fi
        if [ "${_ok}" != "1" ] && wget -q --timeout=25 --tries=4 -O "${_tmp_common}" "${_COMMON_MIRROR}"; then _ok=1; fi
    fi
    if [ "${_ok}" != "1" ]; then
        echo "FATAL: cannot fetch deploy/lib/common.sh (check network, or use the git clone method)" >&2
        rm -f "${_tmp_common}"
        exit 1
    fi
    # shellcheck disable=SC1090
    source "${_tmp_common}"
    rm -f "${_tmp_common}"
fi

# Audit H-5: base SPARSE_DIRS is defined in common.sh; this script (team intranet / full source with plugins) appends plugins
SPARSE_DIRS="${SPARSE_DIRS} plugins"

# ── .env generation — Audit C-1: generate_env unified into lib/common.sh (driven by DEPLOY_TYPE=code, full-plugin LAN mode) ──

# ── Nginx — Audit C-1: write_nginx_config unified into lib/common.sh (driven by DEPLOY_TYPE=code, domain-less default_server template) ──

# ── Fresh install — Audit C-1: do_install unified into lib/common.sh (driven by DEPLOY_TYPE=code, full plugins) ──

# ── Summary — Audit C-1: print_summary unified into lib/common.sh (driven by DEPLOY_TYPE=code, shows plugin/code sizes) ──

# ── Incremental update — Audit C-1: do_update unified into lib/common.sh (driven by DEPLOY_TYPE=code) ──

# ── Main entry ──────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash deploy/install-code.sh [install|update|restart|health|rollback|seed]"
    exit 1
fi

detect_mode "${1:-}"

# Audit A-1: install mode approves DB migration and seed by default, ready to use after install (same as install-local.sh)
if [ "${DEPLOY_MODE}" = "install" ]; then
    APPROVE_MIGRATE=1
fi

# Parse flags (while+shift pattern supports both --region=cn and --region cn)
while [ $# -gt 0 ]; do
    case "${1}" in
        --region=*) REGION="${1#*=}" ;;
        --region) shift; [ $# -gt 0 ] && REGION="${1}" || { echo -e "${FAIL} --region requires a value (cn|global)"; exit 1; } ;;
        --skip-deps) SKIP_DEPS=1 ;;
        --approve-migrate) APPROVE_MIGRATE=1 ;;
        --force) FORCE_UPDATE=1 ;;   # Audit C-3: allow overwriting local changes on update (back up the diff first)
        --admin-user=*) VR_ADMIN_USERNAME="${1#*=}" ;;
        --admin-user) shift; [ $# -gt 0 ] && VR_ADMIN_USERNAME="${1}" || { echo -e "${FAIL} --admin-user requires a value"; exit 1; } ;;
        --admin-pass=*) VR_ADMIN_PASSWORD="${1#*=}" ;;
        --admin-pass) shift; [ $# -gt 0 ] && VR_ADMIN_PASSWORD="${1}" || { echo -e "${FAIL} --admin-pass requires a value"; exit 1; } ;;
        *)
            echo -e "${WARN} Unknown argument ignored: ${1}"
            ;;
    esac
    shift
done
if [ "${REGION}" != "cn" ] && [ "${REGION}" != "global" ]; then
    echo -e "${FAIL} --region must be 'cn' or 'global' (got: ${REGION})"
    exit 1
fi
echo -e "${INFO} Region: ${REGION}"

# Ask for admin credentials (TTY is still alive)
prompt_admin_creds

case "${DEPLOY_MODE}" in
    install)
        do_install
        ;;
    update)
        do_update
        ;;
    restart)
        restart_services
        ;;
    health)
        health_check
        ;;
    rollback)
        do_rollback
        ;;
    seed)
        do_seed
        ;;
    *)
        echo "Usage: sudo bash deploy/install-code.sh [install|update|restart|health|rollback|seed] [--region cn|global] [--skip-deps] [--approve-migrate]"
        exit 1
        ;;
esac
