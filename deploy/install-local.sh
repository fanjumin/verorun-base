#!/bin/bash
# ==========================================================================
# VeroRun — Local / LAN deployment script (no public domain required)
# ==========================================================================
# 一键部署:
#   curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install-local.sh | sudo bash
#
# 手动部署:
#   sudo bash deploy/install-local.sh                     # fresh install
#   sudo bash deploy/install-local.sh update              # update code, deps, and restart
#   sudo bash deploy/install-local.sh restart             # restart services only
#   sudo bash deploy/install-local.sh health              # health check
#   sudo bash deploy/install-local.sh rollback            # rollback to previous commit
#   sudo bash deploy/install-local.sh seed                # seed initial data
#   sudo bash deploy/install-local.sh --skip-deps          # skip dependency install
#   --approve-migrate: explicitly approve DB migration + seed on install
#
# Deploys VeroRun WITHOUT a public domain, accessible via:
#   http://localhost/          → main site
#   http://localhost/admin/    → admin panel
#   http://localhost/auth/     → user console
#   http://192.168.x.x/        → LAN access (same paths)
#
# Differences vs deploy/install.sh:
#   - No domain required: DEPLOY_DOMAIN left empty
#   - DEPLOY_PROTOCOL=http (no SSL)
#   - Nginx path routing only (listen 80 default_server, no subdomains)
#   - Does NOT modify deploy/install.sh
#
# Limitations (expected, architecture-bound):
#   - Online payment / OAuth / SMS unavailable (require public callback URLs)
#   - Multi-tenant subdomains and SSL unavailable
# ==========================================================================
set -euo pipefail

# ── Default config ────────────────────────────────────────────────────
: "${GIT_REPO:=https://github.com/fanjumin/verorun-base.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
: "${APP_HOME:=/home/${APP_USER}/verorun}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${REGION:=global}"                # cn | global

# 审计 C-1：部署模式（lan）——统一函数（lib/common.sh）据此区分行为，必须在 source 前定义
DEPLOY_TYPE="lan"

# ── 加载公共函数库（lib/common.sh，含日志/CN网络适配/git/systemd/健康检查等） ──
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
fi
if [ -n "${SCRIPT_DIR}" ] && [ -f "${SCRIPT_DIR}/lib/common.sh" ]; then
    # 实体文件执行（git clone 后本地执行）→ 直接加载
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/lib/common.sh"
else
    # 一键部署（curl | sudo bash）：脚本从 stdin 执行，无实体路径
    # → 自动从 verorun-base 拉取公共函数库到临时目录加载
    _COMMON_REMOTE="${COMMON_REMOTE:-https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/lib/common.sh}"
    _COMMON_MIRROR="${COMMON_MIRROR:-https://cdn.jsdelivr.net/gh/fanjumin/verorun-base@master/deploy/lib/common.sh}"
    _tmp_common="$(mktemp)"
    # 审计 P3-2：Ctrl+C 中断时清理临时文件
    trap 'rm -f "${_tmp_common}"' EXIT
    _ok=0
    if command -v curl >/dev/null 2>&1; then
        # 审计 M-1：统一 --max-time 防握手卡死 + --retry 抗瞬时抖动
        if curl -sSL --connect-timeout 15 --max-time 25 --retry 3 --retry-delay 2 "${_COMMON_REMOTE}" -o "${_tmp_common}"; then _ok=1; fi
        # 官方源失败（如 GFW 封锁）→ 降级到 jsdelivr CDN 镜像
        if [ "${_ok}" != "1" ] && curl -sSL --connect-timeout 10 --max-time 25 --retry 3 --retry-delay 2 "${_COMMON_MIRROR}" -o "${_tmp_common}"; then _ok=1; fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --timeout=25 --tries=4 -O "${_tmp_common}" "${_COMMON_REMOTE}"; then _ok=1; fi
        if [ "${_ok}" != "1" ] && wget -q --timeout=25 --tries=4 -O "${_tmp_common}" "${_COMMON_MIRROR}"; then _ok=1; fi
    fi
    if [ "${_ok}" != "1" ]; then
        echo "FATAL: 无法获取 deploy/lib/common.sh（检查网络，或改用 git clone 方式）" >&2
        rm -f "${_tmp_common}"
        exit 1
    fi
    # shellcheck disable=SC1090
    source "${_tmp_common}"
    rm -f "${_tmp_common}"
fi

# ── .env generation — 审计 C-1：generate_env 已统一至 lib/common.sh（DEPLOY_TYPE=lan 驱动） ──

# ── Nginx — 审计 C-1：write_nginx_config 已统一至 lib/common.sh（DEPLOY_TYPE=lan 驱动，无域名 default_server 模板） ──

# ── Fresh install — 审计 C-1：do_install 已统一至 lib/common.sh（DEPLOY_TYPE=lan 驱动） ──

# ── Summary — 审计 C-1：print_summary 已统一至 lib/common.sh（DEPLOY_TYPE=lan 驱动） ──

# ── Incremental update — 审计 C-1：do_update 已统一至 lib/common.sh（DEPLOY_TYPE=lan 驱动） ──

# ── Main entry ──────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash deploy/install-local.sh [install|update|restart|health|rollback|seed]"
    exit 1
fi

detect_mode "${1:-}"

# 一键安装：install 模式默认批准 DB 迁移与播种，装完即完全可用
if [ "${DEPLOY_MODE}" = "install" ]; then
    APPROVE_MIGRATE=1
fi

# Parse flags (while+shift pattern supports both --region=cn and --region cn)
# 审计 NEW-C3：统一为与 install.sh/install-code.sh/install-dev.sh 一致的外层 shift 模式
while [ $# -gt 0 ]; do
    case "${1}" in
        --region=*) REGION="${1#*=}" ;;
        --region) shift; [ $# -gt 0 ] && REGION="${1}" || { echo -e "${FAIL} --region requires a value"; exit 1; } ;;
        --skip-deps) SKIP_DEPS=1 ;;
        --approve-migrate) APPROVE_MIGRATE=1 ;;
        --force) FORCE_UPDATE=1 ;;   # 审计 C-3：update 时允许覆盖本地修改（先备份 diff）
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
        echo "Usage: sudo bash deploy/install-local.sh [install|update|restart|health|rollback|seed] [--region cn|global] [--skip-deps] [--approve-migrate]"
        exit 1
        ;;
esac
