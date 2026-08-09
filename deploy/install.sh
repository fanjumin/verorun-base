#!/bin/bash
# ==========================================================================
# VeroRun — One-command deploy script (v2.1)
# ==========================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo bash   # one-command fresh install (public base)
#   sudo bash deploy/install.sh update           # update code, deps, and restart
#   sudo bash deploy/install.sh restart          # restart services only
#   sudo bash deploy/install.sh health           # health check
#   sudo bash deploy/install.sh rollback         # rollback to previous commit
#   sudo bash deploy/install.sh seed             # seed initial data (admin, plans, products)
#   sudo bash deploy/install.sh configure-domain  # configure domain post-install
#   --approve-migrate: explicitly approve DB migration + seed on install
#   (skipped by default; run e.g. 'sudo bash deploy/install.sh install --approve-migrate')
#   --skip-deps: skip system + Python dependency installation (existing env re-deploy)
#   --region=cn|global: region routing (default global; also supports "--region cn")
# ==========================================================================
set -euo pipefail

# ── Default config ────────────────────────────────────────────────────
: "${DEPLOY_MODE:=update}"              # install | update | restart | health | rollback | seed | configure-domain
: "${GIT_REPO:=https://github.com/fanjumin/verorun-base.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
: "${APP_HOME:=/home/${APP_USER}/verorun}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${DOMAIN:=}"
: "${REGION:=global}"                # cn | global
# 审计 C-1：部署模式由各入口脚本在 source 本文件前定义；统一函数（lib/common.sh）据此区分行为
: "${DEPLOY_TYPE:=production}"       # production | lan | code | dev

# ── 加载公共函数库（lib/common.sh，含日志/CN网络适配/git/systemd/健康检查等） ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -f "${SCRIPT_DIR}/lib/common.sh" ]; then
    # 实体文件执行（git clone 后本地执行）→ 直接加载
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/lib/common.sh"
else
    # 一键部署（curl | sudo bash）：脚本从 stdin 执行，无实体路径
    # → 自动从 verorun-base 拉取公共函数库到临时目录加载
    _COMMON_REMOTE="${COMMON_REMOTE:-https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/lib/common.sh}"
    _COMMON_MIRROR="${COMMON_MIRROR:-https://cdn.jsdelivr.net/gh/fanjumin/verorun-base@master/deploy/lib/common.sh}"
    _tmp_common="$(mktemp)"
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

# ── Mode / Domain detection ──────────────────────────────────────────

detect_domain() {
    local domain_arg="${1:-}"
    # Skip flag-style args (e.g. --approve-migrate) that may land in $2
    if [[ "${domain_arg}" == --* ]]; then
        domain_arg=""
    fi
    if [ -n "$domain_arg" ]; then
        DOMAIN="$domain_arg"
    elif [ -f "${APP_HOME}/.env" ]; then
        DOMAIN=$(grep "^DEPLOY_DOMAIN=" "${APP_HOME}/.env" | cut -d= -f2)
    fi
}

prompt_domain() {
    if [ -n "${DOMAIN}" ]; then
        return
    fi
    echo -e "${INFO} Domain is required to continue."
    read -p "  Enter your domain (e.g., verorun.com) — leave empty to configure later: " DOMAIN </dev/tty
    if [ -z "${DOMAIN}" ]; then
        echo -e "${WARN} Domain skipped. Run after install:"
        echo -e "${INFO}   sudo bash deploy/${INSTALL_SCRIPT} configure-domain <your-domain>"
    else
        echo -e "${OK} Domain set to: ${DOMAIN}"
    fi
}

# ==========================================================================
# Fresh install — 审计 C-1：do_install 已统一至 lib/common.sh（DEPLOY_TYPE=production 驱动）
# ==========================================================================

# ==========================================================================
# Incremental update — 审计 C-1：do_update 已统一至 lib/common.sh（DEPLOY_TYPE=production 驱动）
# ==========================================================================

# ==========================================================================
# Configure domain post-install
# ==========================================================================
do_configure_domain() {
    local domain="$1"
    if [ -z "$domain" ]; then
        echo -e "${FAIL} Usage: sudo bash deploy/install.sh configure-domain <your-domain>"
        exit 1
    fi

    step "Configure domain: ${domain}"

    local env_file="${APP_HOME}/.env"
    if [ ! -f "${env_file}" ]; then
        echo -e "${FAIL} .env not found. Run '${INSTALL_SCRIPT} install' first."
        exit 1
    fi

    # Update DEPLOY_DOMAIN in .env
    if grep -q "^DEPLOY_DOMAIN=" "${env_file}"; then
        sed -i "s/^DEPLOY_DOMAIN=.*/DEPLOY_DOMAIN=${domain}/" "${env_file}"
    else
        echo "DEPLOY_DOMAIN=${domain}" >> "${env_file}"
    fi
    DOMAIN="$domain"
    done_step "Updated DEPLOY_DOMAIN in .env"

    step "systemd services"
    chmod +x "${APP_HOME}/deploy/health_check.sh" 2>/dev/null || true
    write_systemd_services
    done_step "systemd services configured"

    step "Nginx"
    write_nginx_config
    nginx -t && systemctl restart nginx
    done_step "Nginx configured"

    step "Start services"
    restart_services
    done_step "Services started"

    print_summary
}

# ==========================================================================
# .env management — 审计 C-1：generate_env 已统一至 lib/common.sh（DEPLOY_TYPE=production 驱动）
# ==========================================================================

# ==========================================================================
# Nginx — 审计 C-1：write_nginx_config 已统一至 lib/common.sh（DEPLOY_TYPE=production 驱动）
# ==========================================================================

# ==========================================================================
# Summary — 审计 C-1：print_summary 已统一至 lib/common.sh（DEPLOY_TYPE=production 驱动）
# ==========================================================================

# ── Main entry ──────────────────────────────────────────────────────────

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash ${INSTALL_SCRIPT} [install|update|restart|health|rollback|seed|configure-domain] [--region cn|global] [--skip-deps] [--approve-migrate]"
    exit 1
fi

detect_mode "${1:-}"
detect_domain "${2:-}"

# 审计 A-1：install 模式默认批准 DB 迁移与播种，装完即用（与 install-local.sh 一致）
if [ "${DEPLOY_MODE}" = "install" ]; then
    APPROVE_MIGRATE=1
fi

# Parse flags: --region cn / --region=cn / --skip-deps / --approve-migrate
# 审计 H4 修复：原 --region) 分支为空操作，--region cn 空格分隔形式的值被丢弃
while [ $# -gt 0 ]; do
    case "${1}" in
        --region=*) REGION="${1#*=}" ;;
        --region) shift; [ $# -gt 0 ] && REGION="${1}" || { echo -e "${FAIL} --region requires a value"; exit 1; } ;;
        --skip-deps) SKIP_DEPS=1 ;;
        --approve-migrate) APPROVE_MIGRATE=1 ;;
        --force) FORCE_UPDATE=1 ;;   # 审计 C-3：update 时允许覆盖本地修改（先备份 diff）
        *)
            # 审计 H-1 修复：detect_domain("${2:-}") 只读 $2，当用户以
            # `install --region cn your-domain.com` 空格形式传参时，域名落在 $4，
            # 此前会被 while 循环静默丢弃。此处将"非 flag、非 DEPLOY_MODE、
            # 且 DOMAIN 尚未确定"的剩余参数捕获为域名。
            if [ -z "${DOMAIN}" ] && [[ "${1}" != --* ]] && [ "${1}" != "${DEPLOY_MODE}" ]; then
                DOMAIN="${1}"
                echo -e "${INFO} Domain detected: ${DOMAIN}"
            fi
            ;;
    esac
    shift
done
# Validate region
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
    configure-domain)
        # 审计 R1 修复：while 循环已 shift 清空 $2，改用 detect_domain 写入的全局 DOMAIN
        do_configure_domain "${DOMAIN}"
        ;;
    *)
        echo "Usage: sudo bash install.sh [install|update|restart|health|rollback|seed|configure-domain <domain>]"
        exit 1
        ;;
esac
