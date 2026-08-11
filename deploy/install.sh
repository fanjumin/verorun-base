#!/bin/bash
# ==========================================================================
# VeroRun — One-command unified deploy script (v3.0)
# ==========================================================================
# Usage:
#   # Interactive (recommended)
#   sudo bash deploy/install.sh install
#
#   # CI / automation (environment variable)
#   sudo env INSTALL_TYPE=professional bash deploy/install.sh install
#
#   # curl|bash one-command
#   curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo env INSTALL_TYPE=professional bash
#
#   sudo bash deploy/install.sh update           # update code, deps, and restart
#   sudo bash deploy/install.sh restart          # restart services only
#   sudo bash deploy/install.sh health           # health check
#   sudo bash deploy/install.sh rollback         # rollback to previous commit
#   sudo bash deploy/install.sh seed             # seed initial data (admin, plans, products)
#   sudo bash deploy/install.sh configure-domain  # configure domain post-install
#   --approve-migrate: explicitly approve DB migration + seed on install
#   --skip-deps: skip system + Python dependency installation (existing env re-deploy)
#   --region=cn|global: region routing (default global)
#
# Supported INSTALL_TYPE values: website | professional | development | educational
#   website      → DEPLOY_TYPE=production (domain + HTTPS)
#   professional → DEPLOY_TYPE=lan         (no domain, LAN access)
#   development  → DEPLOY_TYPE=code        (verorun-code SSH, full plugins)
#   educational  → DEPLOY_TYPE=edu         (no domain, edu license)
#
# install-code.sh is preserved as an independent shortcut (logic merged into Development option here).
# install-local.sh and install-dev.sh have been removed (logic merged into Professional / Development).
# ==========================================================================
set -euo pipefail

# ── Default config ────────────────────────────────────────────────────
: "${GIT_REPO:=https://github.com/fanjumin/verorun-base.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
# APP_USER=root 时 home 为 /root（非 /home/root），与 install-code.sh / install-dev.sh 一致
if [ "${APP_USER}" = "root" ]; then
    : "${APP_HOME:=/root/verorun}"
else
    : "${APP_HOME:=/home/${APP_USER}/verorun}"
fi
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${DOMAIN:=}"
: "${REGION:=global}"                # cn | global
: "${DEPLOY_TYPE:=production}"       # production | lan | code | edu — 默认值，select_deploy_type 会覆盖
: "${VR_ADMIN_USERNAME:=}"
: "${VR_ADMIN_PASSWORD:=}"
: "${SSL_EMAIL:=}"

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
    # → 自动从 verorun-code 拉取公共函数库到临时目录加载
    # 审计 D10：默认源固定为 verorun-code（与一键安装链接一致）；
    # 拉取后做 SHA-256 白名单校验，防 CDN/仓库投毒。
    _COMMON_REMOTE="${COMMON_REMOTE:-https://raw.githubusercontent.com/fanjumin/verorun-code/master/deploy/lib/common.sh}"
    _COMMON_MIRROR="${COMMON_MIRROR:-https://cdn.jsdelivr.net/gh/fanjumin/verorun-code@master/deploy/lib/common.sh}"
    # 发布时由 deploy/scripts/sign_release.py 计算并回填（LF 归一化哈希）
    _COMMON_SHA256="${COMMON_SHA256:-40bdfad1f696b5378b3307ae66afc23079ea29e20189448646f76043b66cd2b0}"
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
    # 审计 D10：SHA-256 白名单校验——不匹配即拒绝加载（防投毒）
    _actual_sha=""
    if command -v sha256sum >/dev/null 2>&1; then
        _actual_sha="$(sha256sum "${_tmp_common}" | awk '{print $1}')"
    elif command -v python3 >/dev/null 2>&1; then
        _actual_sha="$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "${_tmp_common}")"
    fi
    if [ -z "${_actual_sha}" ] || [ "${_actual_sha}" != "${_COMMON_SHA256}" ]; then
        echo "FATAL: common.sh checksum mismatch (got '${_actual_sha}', expected '${_COMMON_SHA256}')" >&2
        echo "       refusing to load to prevent supply-chain tampering. Update install.sh or pin COMMON_SHA256." >&2
        rm -f "${_tmp_common}"
        exit 1
    fi
    # shellcheck disable=SC1090
    source "${_tmp_common}"
    rm -f "${_tmp_common}"
fi

# ══════════════════════════════════════════════════════════════════════
# 部署类型解析（统一入口 v3.0）
# DEPLOY_TYPE: production | lan | code | edu
# ══════════════════════════════════════════════════════════════════════
select_deploy_type() {
    # ================================================================
    # install 模式：每次安装都强制走菜单/环境变量，不受 .env 是否存在影响
    # 即使上次安装失败残留 .env，也会重新弹出选择菜单
    # ================================================================
    if [ "${DEPLOY_MODE}" = "install" ]; then
        # 1) 环境变量优先（CI / curl|bash 管道）
        if [ -n "${INSTALL_TYPE:-}" ]; then
            case "${INSTALL_TYPE}" in
                website)      DEPLOY_TYPE="production" ;;
                professional) DEPLOY_TYPE="lan" ;;
                development)  DEPLOY_TYPE="code" ;;
                educational)  DEPLOY_TYPE="edu" ;;
                *) echo -e "${FAIL} Unknown INSTALL_TYPE: ${INSTALL_TYPE}"; exit 1 ;;
            esac
            echo -e "${INFO} Deploy type from INSTALL_TYPE: ${DEPLOY_TYPE}"
            return
        fi
        # 2) 无 TTY 兜底：必须显式指定 INSTALL_TYPE，否则报错退出（失败即退）
        if [ ! -t 0 ]; then
            echo -e "${FAIL} Non-interactive shell: must specify INSTALL_TYPE"
            echo -e "${INFO}   curl ... | sudo env INSTALL_TYPE=professional bash"
            exit 1
        fi
        # 3) 交互式菜单 — 每次 install 无条件显示
        echo ""
        echo "  VeroRun 安装向导 - 请选择部署类型"
        echo "  ----------------------------------------------"
        echo "  [1] Website        生产部署（需域名 + HTTPS）"
        echo "  [2] Professional   专业版（无域名，LAN 访问）"
        echo "  [3] Development    开发版（verorun-code 全插件，需 SSH key）"
        echo "  [4] Educational    教育版（无域名，需教育认证码）"
        echo -n "  请输入 [1-4]: " > /dev/tty
        read -r _choice < /dev/tty
        case "${_choice}" in
            1) DEPLOY_TYPE="production" ;;
            2) DEPLOY_TYPE="lan" ;;
            3) DEPLOY_TYPE="code" ;;
            4) DEPLOY_TYPE="edu" ;;
            *) echo -e "${FAIL} 无效选择，请重试"; exit 1 ;;
        esac
        echo -e "${INFO} Deploy type selected: ${DEPLOY_TYPE}"
        return
    fi

    # ================================================================
    # 非 install 模式（update / restart / health / rollback / seed 等）：
    # 从 .env 读取，无交互
    # ================================================================

    # 已安装环境：从 .env 读取 DEPLOY_TYPE（幂等）
    if [ -f "${APP_HOME}/.env" ] && grep -q "^DEPLOY_TYPE=" "${APP_HOME}/.env"; then
        DEPLOY_TYPE=$(grep "^DEPLOY_TYPE=" "${APP_HOME}/.env" | tail -1 | cut -d= -f2)
        echo -e "${INFO} Deploy type from .env: ${DEPLOY_TYPE}"
        return
    fi

    # 旧版 .env 兼容：无 DEPLOY_TYPE 时按 DEPLOY_DOMAIN 推断
    # （有域名 -> production；无域名 -> lan。此逻辑仅对存量环境生效）
    if [ -f "${APP_HOME}/.env" ]; then
        local _old_dom
        _old_dom=$(grep "^DEPLOY_DOMAIN=" "${APP_HOME}/.env" 2>/dev/null | tail -1 | cut -d= -f2)
        if [ -n "${_old_dom}" ]; then
            DEPLOY_TYPE="production"
        else
            DEPLOY_TYPE="lan"
        fi
        echo -e "${INFO} Inferred DEPLOY_TYPE=${DEPLOY_TYPE} (pre-DEPLOY_TYPE .env)"
        return
    fi

    # 兜底：如果没有任何 .env（极端情况，非 install 模式下几乎不会到达）
    echo -e "${WARN} No .env found — defaulting DEPLOY_TYPE=${DEPLOY_TYPE}"
}

# ══════════════════════════════════════════════════════════════════════
# 部署类型应用：根据 DEPLOY_TYPE 调整 GIT_REPO / SPARSE_DIRS 等
# ══════════════════════════════════════════════════════════════════════
apply_deploy_type() {
    case "${DEPLOY_TYPE}" in
        code)
            # 复用 install-code.sh 逻辑：verorun-code SSH + 全插件
            GIT_REPO="git@github.com:fanjumin/verorun-code.git"
            SPARSE_DIRS="${SPARSE_DIRS:-} plugins"
            ;;
        edu)
            # 与 lan 一致：verorun-base HTTPS 无域名
            GIT_REPO="https://github.com/fanjumin/verorun-base.git"
            ;;
    esac
}

# ── Mode / Domain detection ──────────────────────────────────────────

detect_domain() {
    # 审计 P0-1：移除 flag 前缀判断。函数仅在 while 参数解析完成后调用，
    # 位置参数中的域名已由 while 循环的 *) catchall 写入 DOMAIN。
    if [ -n "${1:-}" ]; then
        DOMAIN="$1"
    elif [ -z "${DOMAIN:-}" ] && [ -f "${APP_HOME}/.env" ]; then
        DOMAIN=$(grep "^DEPLOY_DOMAIN=" "${APP_HOME}/.env" 2>/dev/null | tail -1 | cut -d= -f2)
    fi
}

# 审计 M18：域名 FQDN 格式校验（拒绝 scheme/路径/端口/空格/连续点/边界连字符）
_is_valid_fqdn() {
    local d="$1"
    case "${d}" in
        *://*|*/*|*:*|*" "*|*..*|.*|*.-*|*-.*) return 1 ;;
    esac
    echo "${d}" | grep -qE '^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
}

prompt_domain() {
    if [ -n "${DOMAIN}" ]; then
        return
    fi
    echo -e "${INFO} Domain is required to continue."
    # 提示符改用 echo -n > /dev/tty 输出——read -p 提示走 stderr，
    # 在 2>&1 | tail 管道下会被缓冲吞掉导致"看似卡死"。
    echo -n "  Enter your domain (e.g., verorun.com) — leave empty to configure later: " > /dev/tty
    read -r DOMAIN < /dev/tty
    DOMAIN="$(echo "${DOMAIN}" | tr -d '[:space:]')"
    if [ -z "${DOMAIN}" ]; then
        echo -e "${WARN} Domain skipped. Run after install:"
        echo -e "${INFO}   sudo bash deploy/${INSTALL_SCRIPT} configure-domain <your-domain>"
    elif _is_valid_fqdn "${DOMAIN}"; then
        echo -e "${OK} Domain set to: ${DOMAIN}"
    else
        echo -e "${WARN} 域名格式非法（${DOMAIN}），已跳过。请使用合法 FQDN，如 verorun.com"
        DOMAIN=""
    fi
}

# ==========================================================================
# Fresh install — 审计 C-1：do_install 已统一至 lib/common.sh（DEPLOY_TYPE 驱动）
# ==========================================================================

# ==========================================================================
# Incremental update — 审计 C-1：do_update 已统一至 lib/common.sh（DEPLOY_TYPE 驱动）
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
    # 审计 M18：configure-domain 参数域名 FQDN 格式校验，非法直接拒绝
    if ! _is_valid_fqdn "${domain}"; then
        echo -e "${FAIL} 非法域名：${domain}（应为合法 FQDN，如 verorun.com）"
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
        local _esc=$(printf '%s' "${domain}" | sed 's/[\/&\\]/\\&/g')
        sed -i "s/^DEPLOY_DOMAIN=.*/DEPLOY_DOMAIN=${_esc}/" "${env_file}"
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

    # 审计 D3：configure-domain 后 TLS 存活校验（证书存在→探测 443；缺失→提示签发命令）
    step "TLS check"
    local _cert_dir="/etc/letsencrypt/live/${domain}"
    if [ -f "${_cert_dir}/fullchain.pem" ] && [ -f "${_cert_dir}/privkey.pem" ]; then
        if command -v curl >/dev/null 2>&1; then
            local _tls_code
            _tls_code=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "https://${domain}/" 2>/dev/null || echo "000")
            if [ "${_tls_code}" = "000" ]; then
                echo -e "${WARN} HTTPS 探测失败（HTTP ${_tls_code}），请检查 443 端口放行与证书有效性"
            else
                done_step "TLS OK (https://${domain} → HTTP ${_tls_code})"
            fi
        else
            done_step "证书存在（未安装 curl，跳过在线探测）"
        fi
    else
        echo -e "${WARN} 证书不存在：当前为纯 HTTP。如需启用 HTTPS，请运行："
        echo "  sudo certbot --nginx -d ${domain} -d www.${domain} -d platform.${domain} -d agent.${domain}"
    fi

    step "Start services"
    restart_services
    done_step "Services started"

    print_summary
}

# ==========================================================================
# .env management — 审计 C-1：generate_env 已统一至 lib/common.sh（DEPLOY_TYPE 驱动）
# ==========================================================================

# ==========================================================================
# Nginx — 审计 C-1：write_nginx_config 已统一至 lib/common.sh（DEPLOY_TYPE 驱动）
# ==========================================================================

# ==========================================================================
# Summary — 审计 C-1：print_summary 已统一至 lib/common.sh（DEPLOY_TYPE 驱动）
# ==========================================================================

# ── Educational 认证占位（拉口固定）────────────────────────────────
# 后续邮箱验证/国内插件认证在此接入；部署层只做 ED-码 + check 校验
_edu_license_check() {
    if [ "${DEPLOY_TYPE}" != "edu" ] || [ "${DEPLOY_MODE}" != "install" ]; then
        return 0
    fi

    echo -e "${INFO} 教育版认证 - 请输入教育版部署码 (ED-XXXX)"
    echo -n "  部署码: " > /dev/tty
    read -r EDU_CODE < /dev/tty
    EDU_CODE="${EDU_CODE// /}"
    if [ -z "${EDU_CODE}" ]; then
        echo -e "${FAIL} 教育部署码不能为空"; exit 1
    fi
    # 区域感知校验接口（沿用 license_service 的区域路由约定）
    local _edu_url
    case "${REGION}" in
        cn)     _edu_url="https://api.verorun.cn" ;;
        *)      _edu_url="https://api.verorun.com" ;;
    esac
    local _edu_check
    _edu_check=$(curl -fsSL --connect-timeout 10 --max-time 20 \
        "${_edu_url}/api/subscription/check?code=${EDU_CODE}" 2>/dev/null \
        || echo '{"success":false}')
    if ! echo "${_edu_check}" | grep -q '"is_valid":true'; then
        echo -e "${FAIL} 教育部署码校验失败，请检查后重试"; exit 1
    fi
    export EDU_CODE
    echo -e "${OK} 教育部署码验证通过"
}

# ── Main entry ──────────────────────────────────────────────────────────

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash ${INSTALL_SCRIPT} [install|update|restart|health|rollback|seed|configure-domain] [--region cn|global] [--skip-deps] [--approve-migrate]"
    exit 1
fi

detect_mode "${1:-}"

# ── 统一入口：解析部署类型（.env 优先；全新 install 才交互）—— 所有模式执行 ──
select_deploy_type
apply_deploy_type

# ── Educational 认证校验（仅 edu + install 模式） ──
_edu_license_check

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
        --admin-user=*) VR_ADMIN_USERNAME="${1#*=}" ;;
        --admin-user) shift; [ $# -gt 0 ] && VR_ADMIN_USERNAME="${1}" || { echo -e "${FAIL} --admin-user requires a value"; exit 1; } ;;
        --admin-pass=*) VR_ADMIN_PASSWORD="${1#*=}" ;;
        --admin-pass) shift; [ $# -gt 0 ] && VR_ADMIN_PASSWORD="${1}" || { echo -e "${FAIL} --admin-pass requires a value"; exit 1; } ;;
        --ssl-email=*) SSL_EMAIL="${1#*=}" ;;
        --ssl-email) shift; [ $# -gt 0 ] && SSL_EMAIL="${1}" || { echo -e "${FAIL} --ssl-email requires a value"; exit 1; } ;;
        *)
            # 审计 H-1 修复：detect_domain("${2:-}") 只读 $2，当用户以
            # `install --region cn your-domain.com` 空格形式传参时，域名落在 $4，
            # 此前会被 while 循环静默丢弃。此处将"非 flag、非 DEPLOY_MODE、
            # 且 DOMAIN 尚未确定"的剩余参数捕获为域名。
            if [ -z "${DOMAIN}" ] && [[ "${1}" != --* ]] && [ "${1}" != "${DEPLOY_MODE}" ]; then
                DOMAIN="${1}"
                echo -e "${INFO} Domain detected: ${DOMAIN}"
            elif [ -n "${DOMAIN}" ] && [[ "${1}" != --* ]] && [ "${1}" != "${DEPLOY_MODE}" ] && [ "${1}" != "${DOMAIN}" ]; then
                echo -e "${WARN} Domain overridden: ${DOMAIN} → ${1}"
                DOMAIN="${1}"
            fi
            ;;
    esac
    shift
done
# 审计 P0-1：while 参数解析完成后统一解析域名（.env 仅作兜底；命令行域名优先，不被覆盖）
detect_domain ""
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
