#!/bin/bash
# ==========================================================================
# VeroRun — deploy/lib/common.sh
# 公共函数库：被 deploy/install.sh / install-local.sh / install-dev.sh / install-code.sh
# 通过 `source` 引用。只定义函数与幂等默认值，无任何顶层执行副作用。
# ==========================================================================
# 使用约定（各脚本必须遵守）：
#   1. 在自身 default config（GIT_REPO / GIT_BRANCH / APP_HOME / SPARSE_DIRS 等）
#      定义完成之后、调用任何公共函数之前 source 本文件。
#   2. 本文件的默认值均为 : "${VAR:=...}" 形式——脚本已设置则不覆盖。
#   3. 修改公共函数只需改本文件一处，四个脚本自动生效。
#   4. install.sh（域名版）保留 B 类函数（generate_env / write_nginx_config /
#      print_summary / do_install / do_update / detect_domain / prompt_domain /
#      do_configure_domain）；无域名三脚本保留 generate_env / write_nginx_config /
#      print_summary / do_install / do_update。
# ==========================================================================

# ── 脚本名（sudoers 声明 / 提示文案引用，参数化消除硬编码） ─────────────
: "${INSTALL_SCRIPT:=$(basename "$0")}"

# ── 幂等默认配置（脚本已设置则不覆盖） ─────────────────────────────────
: "${GIT_REPO:=git@github.com:fanjumin/verorun-code.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
: "${APP_HOME:=/home/${APP_USER}/verorun}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${REGION:=global}"                # cn | global
: "${PIP_MIRROR:=}"
: "${PIP_MIRROR_DETECTED:=}"
: "${VR_ADMIN_CREDS_FILE:=/root/.verorun-creds}"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; WARN="${YELLOW}[WARN]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"

# ══════════════════════════════════════════════════════════════════════
# 日志
# ══════════════════════════════════════════════════════════════════════
step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }
fail_step() { echo -e "${FAIL} $1"; }

# ══════════════════════════════════════════════════════════════════════
# CN Network Auto-Adaptation (v1.0)
# 中国网络环境优化：apt 镜像切换 / pip 多源竞速 / git 超时保护
# 完全向后兼容：海外环境（默认源可达）不触发任何切换。
# ══════════════════════════════════════════════════════════════════════

# 1. apt 镜像：检测默认源 3s 内不可达 → 自动切换阿里云（幂等，marker 文件控制）
_ensure_apt_mirror() {
    local _marker="/etc/apt/.verorun_mirror_applied"
    [ -f "${_marker}" ] && return 0
    if command -v curl >/dev/null 2>&1 && curl -s --connect-timeout 3 http://archive.ubuntu.com >/dev/null 2>&1; then
        touch "${_marker}"; return 0
    fi
    echo -e "${WARN} Ubuntu default mirror unreachable → switching to Aliyun"
    cp /etc/apt/sources.list "/etc/apt/sources.list.bak.$(date +%s)"
    sed -i 's|http://[^/]*archive.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list
    sed -i 's|http://[^/]*security.ubuntu.com|http://mirrors.aliyun.com|g' /etc/apt/sources.list
    sed -i 's|http://[^/]*ports.ubuntu.com|http://mirrors.aliyun.com|g'   /etc/apt/sources.list
    touch "${_marker}"
    echo -e "${OK} apt mirror → Aliyun"
}

# 2. pip 镜像：多源竞速（阿里云 → 清华 → 官方）选响应最快，仅检测一次
_detect_pip_mirror() {
    [ -n "${PIP_MIRROR_DETECTED:-}" ] && return 0
    echo -e "${INFO} Detecting fastest pip mirror..."
    local _best="" _best_time=999
    for _t in \
        "aliyun|https://mirrors.aliyun.com/pypi/simple/pip/|-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com" \
        "tsinghua|https://pypi.tuna.tsinghua.edu.cn/simple/pip/|-i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn" \
        "pypi|https://pypi.org/simple/pip/|"; do
        local _name="${_t%%|*}"; local _rest="${_t#*|}"; local _url="${_rest%%|*}"; local _args="${_rest#*|}"
        local _start=$(date +%s%N)
        if command -v curl >/dev/null 2>&1 && curl -s --connect-timeout 3 --max-time 5 "${_url}" -o /dev/null 2>/dev/null; then
            local _elapsed=$(( ($(date +%s%N) - _start) / 1000000 ))
            echo -e "  ${INFO} ${_name}: ${_elapsed}ms"
            if [ "${_elapsed}" -lt "${_best_time}" ]; then
                _best_time="${_elapsed}"; _best="${_args}"
            fi
        else
            echo -e "  ${WARN} ${_name}: unreachable"
        fi
    done
    if [ -n "${_best}" ]; then PIP_MIRROR="${_best}"; fi
    PIP_MIRROR_DETECTED=1
    echo -e "${OK} pip mirror → ${PIP_MIRROR:-default}"
}

# 3. git clone 超时保护（60s）+ 浅克隆加速；失败给出明确指引
# 注意：不执行 fetch --unshallow —— sparse-checkout 不依赖完整历史，
#      补全历史反而在 CN 网络下重新下载全量数据，违背加速目的。
_clone_with_timeout() {
    local _repo=$1 _dest=$2 _branch=$3
    echo -e "${INFO} Cloning ${_repo} (timeout 60s, shallow)..."
    if timeout 60 git clone --depth 1 -b "${_branch}" "${_repo}" "${_dest}" 2>&1; then
        return 0
    fi
    echo -e "${FAIL} git clone failed or timed out (60s)"
    echo -e "${INFO} Possible causes:"
    echo -e "${INFO}   1. GitHub unreachable (DNS pollution / GFW)"
    echo -e "${INFO}   2. SSH key not configured (private repo)"
    echo -e "${INFO}   3. Network too slow"
    echo -e "${INFO} Workarounds:"
    echo -e "${INFO}   • Use a proxy: export https_proxy=... && re-run"
    echo -e "${INFO}   • Pre-clone manually: git clone ${_repo} ${_dest}"
    echo -e "${INFO}   • For public base: use the HTTPS installer from verorun-base"
    exit 1
}

# --prefer-binary: prefer wheels, fall back to source build
_pip_install() {
    _detect_pip_mirror
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --timeout 120 --prefer-binary ${PIP_MIRROR} "$@"
}

# ══════════════════════════════════════════════════════════════════════
# Git SSH auth setup（HTTPS 公开仓库自动跳过）
# ══════════════════════════════════════════════════════════════════════
ensure_git_auth() {
    if echo "${GIT_REPO}" | grep -q '^https://'; then
        return 0
    fi
    local ssh_key="/root/.ssh/id_ed25519"
    if [ ! -f "${ssh_key}" ]; then
        echo -e "${INFO} Generating SSH deploy key for git operations..."
        mkdir -p /root/.ssh
        ssh-keygen -t ed25519 -N "" -f "${ssh_key}" -C "verorun-deploy-$(hostname)" >/dev/null 2>&1
        chmod 600 "${ssh_key}"
        chmod 644 "${ssh_key}.pub"
        echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║  ADD THIS DEPLOY KEY TO GITHUB (one-time setup):           ║${NC}"
        echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
        echo -e "${YELLOW}║  URL: https://github.com/fanjumin/verorun-code/settings/keys/new${NC}"
        echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
        cat "${ssh_key}.pub" | while read -r line; do
            echo -e "${GREEN}║  ${line}${NC}"
        done
        echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo -e "${WARN} After adding the key, re-run this script to continue."
        exit 0
    fi
    if [ ! -f /root/.ssh/known_hosts ] || ! grep -q '^github\.com' /root/.ssh/known_hosts 2>/dev/null; then
        ssh-keyscan github.com >> /root/.ssh/known_hosts 2>/dev/null || true
    fi
    if [ -d "${APP_HOME}/.git" ]; then
        local current_url
        current_url=$(git -C "${APP_HOME}" remote get-url origin 2>/dev/null || echo "")
        if echo "${current_url}" | grep -q '^https://'; then
            git -C "${APP_HOME}" remote set-url origin "${GIT_REPO}"
            done_step "Git remote switched to SSH"
        fi
    fi
}

# ══════════════════════════════════════════════════════════════════════
# 目录冲突处理（文档 verorun-deploy-guide.html §6.3：备份/删除/中止）
# ══════════════════════════════════════════════════════════════════════
resolve_directory_conflict() {
    local target_dir="$1"

    # 目录不存在 → 正常流程
    if [ ! -d "${target_dir}" ]; then
        return 0
    fi

    # 已是 git 仓库 → 可以安全更新
    if [ -d "${target_dir}/.git" ]; then
        echo -e "${OK} Existing VeroRun installation detected at ${target_dir}"
        return 0
    fi

    # 目录存在但不是 git 仓库 → 交互式选择
    echo ""
    echo -e "${WARN} ═══════════════════════════════════════════════════════"
    echo -e "${WARN}  Directory conflict detected:"
    echo -e "${WARN}    ${target_dir}"
    echo -e "${WARN}"
    echo -e "${WARN}  This directory exists but is NOT a VeroRun installation."
    echo -e "${WARN}  What would you like to do?"
    echo -e "${WARN}"
    echo -e "${INFO}  [1] Backup and reinstall"
    echo -e "${INFO}      → Move to ${target_dir}.bak.$(date +%Y%m%d%H%M%S) and proceed"
    echo -e "${INFO}  [2] Delete and reinstall"
    echo -e "${INFO}      → Remove ${target_dir} completely and proceed"
    echo -e "${INFO}  [3] Abort installation"
    echo -e "${INFO}      → Exit now. You can manually resolve and re-run."
    echo -e "${WARN} ═══════════════════════════════════════════════════════"

    while true; do
        read -r -p "  Your choice [1/2/3]: " _choice </dev/tty

        case "${_choice}" in
            1)
                local _bak="${target_dir}.bak.$(date +%Y%m%d%H%M%S)"
                echo -e "${INFO} Backing up to ${_bak} ..."
                mv "${target_dir}" "${_bak}"
                echo -e "${OK} Backup complete. Proceeding with installation."
                return 0
                ;;
            2)
                # 安全防护：拒绝删除危险路径
                if [ -z "${target_dir}" ] || [ "${target_dir}" = "/" ] || [ "${target_dir}" = "${HOME}" ]; then
                    echo -e "${FAIL} Refusing to remove dangerous path: ${target_dir}"
                    exit 1
                fi
                echo -e "${INFO} Removing ${target_dir} ..."
                rm -rf "${target_dir}"
                echo -e "${OK} Removed. Proceeding with installation."
                return 0
                ;;
            3)
                echo -e "${INFO} Installation aborted by user."
                exit 0
                ;;
            *)
                echo -e "${WARN} Please enter 1, 2, or 3"
                ;;
        esac
    done
}

# ══════════════════════════════════════════════════════════════════════
# DEBUG 强制禁用（生产门禁：install/update 前必须 APP_DEBUG=false 且 FLASK_DEBUG=0）
# ══════════════════════════════════════════════════════════════════════
assert_debug_disabled() {
    local _dbg
    # Check APP_DEBUG
    _dbg=$(grep -E '^APP_DEBUG=' "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2)
    case "${_dbg}" in
        1|true|TRUE|True|on|yes)
            echo -e "${FAIL} Production install aborted: APP_DEBUG is enabled in .env"
            echo -e "${INFO} Set APP_DEBUG=false in ${APP_HOME}/.env and re-run"
            exit 1 ;;
    esac
    # Check FLASK_DEBUG
    _dbg=$(grep -E '^FLASK_DEBUG=' "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2)
    case "${_dbg}" in
        1|true|TRUE|True|on|yes)
            echo -e "${FAIL} Production install aborted: FLASK_DEBUG is enabled in .env"
            echo -e "${INFO} Set FLASK_DEBUG=0 in ${APP_HOME}/.env and re-run"
            exit 1 ;;
    esac
}

# ══════════════════════════════════════════════════════════════════════
# .env 补齐缺失密钥（幂等）
# ══════════════════════════════════════════════════════════════════════
update_env() {
    local env_file="${APP_HOME}/.env"
    if [ ! -f "${env_file}" ]; then
        generate_env
        return
    fi

    local missing=()
    for key in PLUGIN_LICENSE_SECRET CAPTCHA_SECRET_KEY DEV_ACCOUNTS_ENCRYPTION_KEY LICENSE_SERVER_SECRET PROBE_SECRET INTERNAL_SERVICE_TOKEN; do
        if ! grep -q "^${key}=" "${env_file}" 2>/dev/null; then
            local val
            val=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            echo "${key}=${val}" >> "${env_file}"
            missing+=("${key}")
        fi
    done

    for key in APP_DEBUG:false FLASK_DEBUG:0; do
        local k="${key%%:*}" v="${key##*:}"
        if ! grep -q "^${k}=" "${env_file}" 2>/dev/null; then
            echo "${k}=${v}" >> "${env_file}"
            missing+=("${k}")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${OK} Filled missing keys: ${missing[*]}"
        chmod 600 "${env_file}"
    else
        echo -e "${OK} All keys are present in .env"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# systemd 服务（四服务 + guardian 守护进程）
# ══════════════════════════════════════════════════════════════════════
write_systemd_services() {
    local env_file="${APP_HOME}/.env"
    write_one_service() {
        local name=$1 port=$2 module=$3 extra_args="${4:-}" runner="${5:-}" runtime_dir="${6:-}"
        local file="${SERVICE_DIR}/${name}.service"
        if [ -n "${runner}" ]; then
            local exec_cmd="${VENV_DIR}/bin/python ${APP_HOME}/${runner} -w 2 -b 127.0.0.1:${port} ${extra_args} ${module}:app"
        else
            local exec_cmd="${VENV_DIR}/bin/gunicorn -w 2 -b 127.0.0.1:${port} ${extra_args} ${module}:app"
        fi
        local rt_block=""
        if [ -n "${runtime_dir}" ]; then
            rt_block="RuntimeDirectory=${runtime_dir}
RuntimeDirectoryMode=0755"
        fi
        cat > "${file}" << SVCEOF
[Unit]
Description=VeroRun ${name}
After=network.target postgresql.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_HOME}
EnvironmentFile=${env_file}
ExecStart=${exec_cmd}
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=30
TimeoutStartSec=300
# Startup health check: /health must return 200, otherwise systemd marks startup failed
ExecStartPost=${APP_HOME}/deploy/health_check.sh ${port}
StandardOutput=append:${LOG_DIR}/${name}.log
StandardError=append:${LOG_DIR}/${name}.log
${rt_block}

[Install]
WantedBy=multi-user.target
SVCEOF
        systemctl daemon-reload
        systemctl enable "${name}"
    }
    # 8081 — Main site (homepage public_home.html)
    write_one_service "verorun-main" 8081 "auth_server" "--timeout 120 --log-level warning"
    # 8083 — Platform / User Console
    write_one_service "verorun-auth" 8083 "main_site" "--timeout 120 --log-level warning"
    # 8084 — Admin (uses run_gunicorn.py to avoid platform/ shadowing stdlib)
    # RuntimeDirectory=verorun → systemd creates /run/verorun/ owned by APP_USER on service start.
    write_one_service "verorun-admin" 8084 "admin.app" "--timeout 300 --max-requests=1000 --graceful-timeout=30 --log-level warning --config admin/gunicorn_config.py" "admin/run_gunicorn.py" "verorun"
    # 8085 — Health Check
    write_one_service "verorun-health" 8085 "health_service.app" "--timeout 30 --graceful-timeout=30 --log-level warning"
    # ── verorun-guardian (standalone daemon, no HTTP port) ──
    write_guardian_service
    write_guardian_env
}

write_guardian_service() {
    local file="${SERVICE_DIR}/verorun-guardian.service"
    cat > "${file}" << 'GDEVEOF'
[Unit]
Description=VeroGuard — Unified Guardian Daemon (Health + Integrity + Heartbeat)
After=network.target postgresql.service
Wants=verorun-health.service verorun-main.service verorun-admin.service verorun-auth.service

[Service]
Type=simple
# Guardian runs as root to access system integrity checks (file hashes,
# process monitoring, and systemd journal) that require elevated privileges.
User=root
WorkingDirectory=GDEVDIR
EnvironmentFile=-/etc/default/verorun-guardian
ExecStart=GDEVDIR/venv/bin/python GDEVDIR/veroguard/guardian.py
Restart=always
RestartSec=5
RuntimeDirectory=verorun-guardian
RuntimeDirectoryMode=0755
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
GDEVEOF
    sed -i "s|GDEVDIR|${APP_HOME}|g" "${file}"
    systemctl daemon-reload
    systemctl enable verorun-guardian
}

write_guardian_env() {
    local env_file="/etc/default/verorun-guardian"
    local probe_secret=""
    if [ -f "${APP_HOME}/.env" ]; then
        probe_secret=$(grep "^PROBE_SECRET=" "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2) || true
        [ -n "${probe_secret}" ] && probe_secret="PROBE_SECRET=${probe_secret}"
    fi
    cat > "${env_file}" << GENVEOF
# VeroGuard Guardian environment config — generated by ${INSTALL_SCRIPT}
GUARDIAN_PROJECT_DIR=${APP_HOME}
GUARDIAN_LOG_FILE=${LOG_DIR}/verorun-guardian.log
GUARDIAN_CHECK_INTERVAL=30
GUARDIAN_MAX_FAILURES=3
GUARDIAN_COOLDOWN=300
GUARDIAN_INTEGRITY_INTERVAL=300
GUARDIAN_HEARTBEAT_INTERVAL=300
GUARDIAN_WEBHOOK_URL=
GUARDIAN_REMOTE_URL=https://api.verorun.com
${probe_secret}
DEPLOYMENT_CODE=
GENVEOF
    chmod 600 "${env_file}"
}

# ══════════════════════════════════════════════════════════════════════
# sudoers — 一键更新权限（声明式、幂等）
# ══════════════════════════════════════════════════════════════════════
write_sudoers() {
    local sudoers_file="/etc/sudoers.d/verorun"
    cat > "${sudoers_file}" << SUEOF
# Managed by VeroRun ${INSTALL_SCRIPT} — regenerated on every install/update
# Grants ${APP_USER} passwordless one-click update for VeroRun services
${APP_USER} ALL=(root) NOPASSWD: /bin/bash ${APP_HOME}/deploy/${INSTALL_SCRIPT} update
${APP_USER} ALL=(root) NOPASSWD: /bin/bash ${APP_HOME}/deploy/${INSTALL_SCRIPT} restart
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-main
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-auth
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-admin
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-health
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart verorun-guardian
${APP_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl restart nginx
SUEOF
    chmod 440 "${sudoers_file}"
    visudo -c -f "${sudoers_file}" || {
        echo -e "${FAIL} Invalid sudoers file — restoring previous state"
        rm -f "${sudoers_file}"
        exit 1
    }
}

# ══════════════════════════════════════════════════════════════════════
# 服务重启（含启动等待轮询 + nginx）
# ══════════════════════════════════════════════════════════════════════
restart_services() {
    local services=("verorun-admin" "verorun-auth" "verorun-main" "verorun-health" "verorun-guardian")
    for svc in "${services[@]}"; do
        if systemctl is-enabled --quiet "${svc}" 2>/dev/null; then
            systemctl restart "${svc}"
            local _waited=0
            while [ $_waited -lt 60 ]; do
                if systemctl is-active --quiet "${svc}" 2>/dev/null; then
                    echo -e "${OK} ${svc} is running"
                    break
                fi
                sleep 2
                _waited=$((_waited + 2))
            done
            if [ $_waited -ge 60 ]; then
                echo -e "${FAIL} ${svc} failed to start — check: journalctl -u ${svc} -n 20"
            fi
        else
            echo -e "${WARN} ${svc} not configured, skipping"
        fi
    done
    if systemctl is-enabled --quiet nginx 2>/dev/null; then
        systemctl restart nginx
        echo -e "${OK} nginx restarted"
    fi
}

# ══════════════════════════════════════════════════════════════════════
# 依赖扫描
# ══════════════════════════════════════════════════════════════════════
check_system_deps() {
    local pkg
    for pkg in python3 python3-venv python3-pip python3-dev nginx git curl wget \
        build-essential libpq-dev libssl-dev postgresql postgresql-client; do
        if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
            return 1
        fi
    done
    return 0
}

check_python_deps() {
    [ -x "${VENV_DIR}/bin/python" ] || return 1
    [ -f "${APP_HOME}/requirements.txt" ] || return 1
    local freeze line pkg
    freeze=$("${VENV_DIR}/bin/pip" list --format=freeze 2>/dev/null) || return 1
    while read -r line; do
        [ -z "${line}" ] && continue
        case "${line}" in \#*) continue ;; esac
        pkg="${line%%[<>=!~;]*}"
        pkg=$(printf '%s' "${pkg}" | tr 'A-Z' 'a-z' | tr '_' '-')
        printf '%s\n' "${freeze}" | grep -qi "^${pkg}==" || return 1
    done < "${APP_HOME}/requirements.txt"
    return 0
}

# ══════════════════════════════════════════════════════════════════════
# 模式检测
# ══════════════════════════════════════════════════════════════════════
detect_mode() {
    local mode="${1:-}"
    if [ -n "$mode" ]; then
        DEPLOY_MODE="$mode"
    elif [ -f "${APP_HOME}/.env" ]; then
        DEPLOY_MODE="update"
    else
        DEPLOY_MODE="install"
    fi
    echo -e "${INFO} Deploy mode: ${DEPLOY_MODE}"
}

# ══════════════════════════════════════════════════════════════════════
# 管理员凭据交互创建（install 模式、TTY 存活时调用）
# ══════════════════════════════════════════════════════════════════════
prompt_admin_creds() {
    case "${DEPLOY_MODE}" in install) ;; *) return 0 ;; esac
    [ -f "${VR_ADMIN_CREDS_FILE}" ] && return 0

    echo "" > /dev/tty
    echo -e "${INFO} Create the administrator account for VeroRun" > /dev/tty

    local _user="" _pass="" _pass2=""
    read -r -p "  Admin username: " _user < /dev/tty
    while [ -z "${_user}" ]; do
        echo -e "${WARN} Username cannot be empty" > /dev/tty
        read -r -p "  Admin username: " _user < /dev/tty
    done

    read -r -s -p "  Admin password: " _pass < /dev/tty
    echo "" > /dev/tty
    while [ -z "${_pass}" ]; do
        echo -e "${WARN} Password cannot be empty" > /dev/tty
        read -r -s -p "  Admin password: " _pass < /dev/tty
        echo "" > /dev/tty
    done

    read -r -s -p "  Confirm password: " _pass2 < /dev/tty
    echo "" > /dev/tty
    while [ "${_pass}" != "${_pass2}" ]; do
        echo -e "${WARN} Passwords do not match, try again" > /dev/tty
        read -r -s -p "  Admin password: " _pass < /dev/tty
        echo "" > /dev/tty
        read -r -s -p "  Confirm password: " _pass2 < /dev/tty
        echo "" > /dev/tty
    done

    printf 'VR_ADMIN_USERNAME="%s"\nVR_ADMIN_PASSWORD="%s"\n' "${_user}" "${_pass}" > "${VR_ADMIN_CREDS_FILE}"
    chmod 600 "${VR_ADMIN_CREDS_FILE}"
    # 审计 C2 加固：脚本异常退出时清理凭据文件（prompt 仅在 install 模式调用，无 EXIT trap 冲突）
    trap 'rm -f "${VR_ADMIN_CREDS_FILE}"' EXIT
    echo -e "${OK} Admin credentials saved"
}

# ══════════════════════════════════════════════════════════════════════
# 健康检查
# ══════════════════════════════════════════════════════════════════════
health_check() {
    echo ""
    local all_ok=true

    check_port() {
        local port=$1 name=$2
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://127.0.0.1:${port}/" 2>/dev/null || echo "000")
        if [ "$code" != "000" ]; then
            echo -e "  ${OK} ${name} (:${port}) -> HTTP ${code}"
        else
            echo -e "  ${FAIL} ${name} (:${port}) -> no response"
            all_ok=false
        fi
    }

    check_port 8081 "verorun-main"
    check_port 8083 "verorun-auth"
    check_port 8084 "verorun-admin"
    check_port 8085 "verorun-health"

    if systemctl is-active --quiet verorun-guardian 2>/dev/null; then
        echo -e "  ${OK} verorun-guardian (systemd)"
    else
        echo -e "  ${FAIL} verorun-guardian (inactive)"
        all_ok=false
    fi

    echo ""
    echo -e "${INFO} Migration log check:"
    for svc in verorun-admin verorun-auth verorun-main; do
        journalctl -u "${svc}" --since "1 min ago" 2>/dev/null | grep -i "\[Migration\]" | tail -2 || true
    done

    if $all_ok; then
        echo -e "\n${OK} All services healthy"
    else
        echo -e "\n${FAIL} Some services are unhealthy — check logs"
        UPDATE_FAILED=1
    fi
}

# ══════════════════════════════════════════════════════════════════════
# 种子数据
# ══════════════════════════════════════════════════════════════════════
do_seed() {
    step "Seed initial data"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        echo -e "${FAIL} Python venv not found at ${VENV_DIR}"
        echo -e "${INFO} Run '${INSTALL_SCRIPT}' first"
        exit 1
    fi

    # Seed is grouped under the same manual gate as DB migration
    if [ "${APPROVE_MIGRATE:-0}" != "1" ]; then
        echo -e "${WARN} Skipped seed data (pass --approve-migrate to inject admin/plans/products)"
        return 0
    fi

    # Read credentials from temp file (set by prompt_admin_creds)
    VR_ADMIN_USERNAME=""
    VR_ADMIN_PASSWORD=""
    if [ -f "${VR_ADMIN_CREDS_FILE}" ]; then
        # shellcheck disable=SC1090
        source "${VR_ADMIN_CREDS_FILE}"
        rm -f "${VR_ADMIN_CREDS_FILE}"
    fi

    if [ -z "${VR_ADMIN_USERNAME}" ]; then
        echo -e "${INFO} No admin credentials provided — username defaults to 'administrator'"
    fi

    # 审计 C1：管理员凭据经环境变量传入 seed_data.py，避免出现在进程命令行
    if [ -n "${VR_ADMIN_USERNAME}" ]; then
        sudo -u "${APP_USER}" env VR_ADMIN_USERNAME="${VR_ADMIN_USERNAME}" VR_ADMIN_PASSWORD="${VR_ADMIN_PASSWORD}" \
            "${VENV_DIR}/bin/python" "${APP_HOME}/deploy/seed_data.py"
    else
        sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" "${APP_HOME}/deploy/seed_data.py"
    fi
    echo -e "${OK} Seed data injected"
}

# ══════════════════════════════════════════════════════════════════════
# 回滚（统一使用 before_commit 保存点，缺失时 fallback HEAD~1）
# ══════════════════════════════════════════════════════════════════════
do_rollback() {
    step "Rollback to previous version"
    cd "${APP_HOME}"
    git reflog --oneline -5 | head -5
    local target_commit
    if [ -f "${APP_HOME}/.rollback/before_commit" ]; then
        target_commit=$(head -1 "${APP_HOME}/.rollback/before_commit" | awk '{print $1}')
        echo -e "${INFO} Rolling back to saved commit: ${target_commit}"
    else
        target_commit="HEAD~1"
        echo -e "${WARN} No saved commit found, falling back to HEAD~1"
    fi
    if git reset --hard "${target_commit}"; then
        systemctl restart verorun-admin verorun-auth verorun-main verorun-health verorun-guardian
        echo -e "${OK} Rolled back to $(git log --oneline -1)"
    else
        echo -e "${FAIL} Rollback failed"
    fi
}
