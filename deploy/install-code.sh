#!/bin/bash
# ==========================================================================
# VeroRun — Local source code deployment script (no domain required)
# ==========================================================================
# Usage:
#   sudo bash deploy/install-code.sh                    # 本地源码安装
#   sudo bash deploy/install-code.sh --src /path/code   # 指定源码目录
#   sudo bash deploy/install-code.sh --from-tar /path/pkg.tar.gz  # 远程 tar
#   sudo bash deploy/install-code.sh seed               # 种子数据
#   sudo bash deploy/install-code.sh restart            # 重启服务
#   sudo bash deploy/install-code.sh --skip-deps        # 跳过依赖安装
#
# 功能: 从本地源码部署全功能 VeroRun，无域名，localhost/LAN 访问
# 与 install-local.sh 区别: 无 git clone，完整拷贝所有源码和插件
# ==========================================================================
set -euo pipefail

# ── Default config ────────────────────────────────────────────────────
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
: "${APP_HOME:=/home/${APP_USER}/verorun}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${REGION:=global}"                # cn | global
: "${SOURCE_DIR:=}"                  # 源码目录，默认脚本所在目录的上一级
: "${FROM_TAR:=}"                    # 远程 tar.gz 包路径

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; WARN="${YELLOW}[WARN]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"

# ── CN Network Auto-Adaptation (v1.0) ────────────────────────────────
# 中国网络环境优化：apt 镜像切换 / pip 多源竞速
# 完全向后兼容：海外环境（默认源可达）不触发任何切换。
PIP_MIRROR=""
PIP_MIRROR_DETECTED=""

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

# --prefer-binary: prefer wheels, fall back to source build
_pip_install() {
    _detect_pip_mirror
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --timeout 120 --prefer-binary ${PIP_MIRROR} "$@"
}

step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }
fail_step() { echo -e "${FAIL} $1"; }

# ══════════════════════════════════════════════════════════════════════
# 核心差异: 本地源码拷贝 (替代 git clone + sparse-checkout)
# ══════════════════════════════════════════════════════════════════════
copy_source_code() {
    local src_dir="$1"
    local dst_dir="$2"

    if [ ! -d "${src_dir}" ]; then
        echo -e "${FAIL} Source directory not found: ${src_dir}"
        exit 1
    fi

    # 验证是否为 VeroRun 源码目录（检查关键文件）
    if [ ! -f "${src_dir}/requirements.txt" ] || [ ! -d "${src_dir}/auth-center" ]; then
        echo -e "${FAIL} Not a valid VeroRun source directory (missing requirements.txt or auth-center/)"
        exit 1
    fi

    echo -e "${INFO} Copying source code from: ${src_dir}"
    echo -e "${INFO} Target directory: ${dst_dir}"

    # 清理目标目录（如果存在且非空）——仅提示覆盖，不删除
    if [ -d "${dst_dir}" ] && [ "$(ls -A "${dst_dir}" 2>/dev/null)" ]; then
        echo -e "${WARN} Target directory exists and is not empty."
        echo -e "${WARN} Existing files will be overwritten during copy."
    fi
    mkdir -p "${dst_dir}"

    # 使用 rsync（如果可用）或 find+cp -a 进行全量拷贝
    # 排除: .git, __pycache__, *.pyc, *.pyo, node_modules, venv, .env, *.egg-info, .DS_Store
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --delete \
            --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
            --exclude='*.pyo' --exclude='node_modules' --exclude='venv' \
            --exclude='.env' --exclude='*.egg-info' --exclude='.DS_Store' \
            "${src_dir}/" "${dst_dir}/"
    else
        # fallback: cp -a，只处理顶层条目，避免把 src_dir 自身拷进 dst_dir
        find "${src_dir}" -mindepth 1 -maxdepth 1 \
            ! -name '.git' ! -name '__pycache__' ! -name 'node_modules' \
            ! -name 'venv' ! -name '.env' ! -name '.DS_Store' \
            ! -name '*.egg-info' \
            -exec cp -a {} "${dst_dir}/" \; 2>/dev/null || true
        find "${dst_dir}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
        find "${dst_dir}" -name '*.pyc' -delete 2>/dev/null || true
        find "${dst_dir}" -name '*.pyo' -delete 2>/dev/null || true
    fi

    # 确保 deploy 目录存在
    if [ ! -d "${dst_dir}/deploy" ]; then
        echo -e "${FAIL} deploy/ directory not copied correctly"
        exit 1
    fi

    # 拷贝自身到 deploy 目录（确保脚本在目标环境中存在）
    cp "$0" "${dst_dir}/deploy/install-code.sh" 2>/dev/null || true
    chmod +x "${dst_dir}/deploy/install-code.sh" 2>/dev/null || true
    chmod +x "${dst_dir}/deploy/health_check.sh" "${dst_dir}/deploy/seed_data.py" 2>/dev/null || true

    chown -R "${APP_USER}:${APP_USER}" "${dst_dir}" 2>/dev/null || true
    echo -e "${OK} Source code copied ($(du -sh "${dst_dir}" | cut -f1))"
    echo -e "${INFO} Plugins: $(ls -d "${dst_dir}/plugins/"*/ 2>/dev/null | wc -l) directories"
}

# ══════════════════════════════════════════════════════════════════════
# 从 tar.gz 解压源码（用于远程部署）
# ══════════════════════════════════════════════════════════════════════
extract_from_tar() {
    local tar_path="$1"
    local dst_dir="$2"

    if [ ! -f "${tar_path}" ]; then
        echo -e "${FAIL} Tar file not found: ${tar_path}"
        exit 1
    fi

    # 危险路径保护：禁止删除空串、根目录或用户家目录
    if [ -z "${dst_dir}" ] || [ "${dst_dir}" = "/" ] || [ "${dst_dir}" = "${HOME}" ]; then
        echo -e "${FAIL} Refusing to remove dangerous path: ${dst_dir}"
        exit 1
    fi

    echo -e "${INFO} Extracting from tar: ${tar_path}"

    # 清理目标目录
    if [ -d "${dst_dir}" ]; then
        rm -rf "${dst_dir}"
    fi
    mkdir -p "${dst_dir}"

    # 解压（优先 strip-components=1 处理带顶层目录的包）
    if ! tar -xzf "${tar_path}" -C "${dst_dir}" --strip-components=1 2>/dev/null; then
        if ! tar -xzf "${tar_path}" -C "${dst_dir}" 2>/dev/null; then
            echo -e "${FAIL} Failed to extract tar file"
            exit 1
        fi
    fi

    # 验证
    if [ ! -f "${dst_dir}/requirements.txt" ]; then
        echo -e "${FAIL} Extracted source is not a valid VeroRun codebase"
        exit 1
    fi

    chmod +x "${dst_dir}/deploy/health_check.sh" "${dst_dir}/deploy/seed_data.py" 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${dst_dir}" 2>/dev/null || true
    echo -e "${OK} Source extracted from tar ($(du -sh "${dst_dir}" | cut -f1))"
}

# ══════════════════════════════════════════════════════════════════════
# .env 生成（无域名模式，修复 install-local.sh 遗漏的变量）
# ══════════════════════════════════════════════════════════════════════
generate_env() {
    local env_file="${APP_HOME}/.env"
    local force="${1:-}"

    if [ -f "${env_file}" ] && [ "${force}" != "force" ]; then
        echo -e "${WARN} .env already exists, skipping"
        return
    fi

    if [ -f "${env_file}" ] && [ "${force}" = "force" ]; then
        cp "${env_file}" "${env_file}.bak.$(date +%s)" 2>/dev/null || true
    fi

    if [ -z "${PG_PASSWORD:-}" ]; then
        PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    fi

    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    PLUGIN_LICENSE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    CAPTCHA_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    DEV_ACCOUNTS_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    LICENSE_SERVER_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    PROBE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    # 修复 install-local.sh 遗漏: INTERNAL_SERVICE_TOKEN
    INTERNAL_SERVICE_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > "${env_file}" << ENVEOF
# VeroRun config — auto-generated by install-code.sh (local-source / LAN mode)
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=
DEPLOY_PROTOCOL=http
DB_PATH=${APP_HOME}/data/verorun.db
PG_HOST=localhost
PG_PORT=5432
PG_DB=verorun
PG_USER=verorun
PG_PASSWORD=${PG_PASSWORD}
JWT_SECRET=${JWT_SECRET}
FLASK_SECRET_KEY=${FLASK_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
APP_MODE=main

# Production-safe default: DEBUG disabled (审计 H2 修复，防止本地脚本误开启调试)
APP_DEBUG=false
FLASK_DEBUG=0

# v2.1.0 — 内部服务令牌（修复 install-local.sh 遗漏）
INTERNAL_SERVICE_TOKEN=${INTERNAL_SERVICE_TOKEN}

# Phase 1 — Security hardening keys (2026-07-28)
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}

# Deployments do not auto-install/enable plugins by default (install manually in admin)
PLUGIN_AUTO_INSTALL=0

# VeroGuard — daemon encrypted communication key (official side and client must match)
PROBE_SECRET=${PROBE_SECRET}

# API Keys (replace with real values)
DASHSCOPE_TEXT_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here

# Region routing (VeroRun 0.43.0+)
VERORUN_REGION=${REGION}
ENVEOF

    chown "${APP_USER}:${APP_USER}" "${env_file}"
    chmod 600 "${env_file}"
    echo -e "${OK} .env generated (no-domain mode, all secrets initialized)"
}

# ══════════════════════════════════════════════════════════════════════
# systemd 服务（与 install-local.sh 完全一致）
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
# VeroGuard Guardian environment config — generated by install-code.sh
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

# ── sudoers — one-click restart permissions (declarative, idempotent) ──
write_sudoers() {
    local sudoers_file="/etc/sudoers.d/verorun"
    cat > "${sudoers_file}" << SUEOF
# Managed by VeroRun install-code.sh — regenerated on every install
# Grants ${APP_USER} passwordless restart for VeroRun services only
# 审计 H5 修复：不再授予"运行整个安装脚本"的无密码权限，仅保留受控的 systemctl restart
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

# ── Nginx — no-domain path routing only ───────────────────────────────
write_nginx_config() {
    local nginx_conf="/etc/nginx/sites-available/verorun.conf"
    local nginx_enabled="/etc/nginx/sites-enabled/verorun.conf"

    cat > "${nginx_conf}" << NGXEOF
# VeroRun Nginx — no-domain mode (auto-generated by install-code.sh)

server {
    listen 80 default_server;
    # No server_name: match every Host (localhost / LAN IP)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # ── Admin panel ─────────────────────────
    location /admin/ {
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    # ── User console / auth ─────────────────
    location /auth/ {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /subscribe {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # ── Main site (default route) ───────────
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGXEOF

    rm -f /etc/nginx/sites-enabled/default
    ln -sf "${nginx_conf}" "${nginx_enabled}"
}

# ── Seed initial data ─────────────────────────────────────────────────
do_seed() {
    step "Seed initial data"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        echo -e "${FAIL} Python venv not found at ${VENV_DIR}"
        echo -e "${INFO} Run 'install-code.sh' first"
        exit 1
    fi
    # 审计 C1：管理员凭据经环境变量传入 seed_data.py，避免出现在进程命令行
    if [ -n "${VR_ADMIN_USERNAME:-}" ]; then
        sudo -u "${APP_USER}" env VR_ADMIN_USERNAME="${VR_ADMIN_USERNAME}" VR_ADMIN_PASSWORD="${VR_ADMIN_PASSWORD}" \
            "${VENV_DIR}/bin/python" "${APP_HOME}/deploy/seed_data.py"
    else
        sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" "${APP_HOME}/deploy/seed_data.py"
    fi
    echo -e "${OK} Seed data injected"
}

# ══════════════════════════════════════════════════════════════════════
# do_install — 主安装流程（唯一差异: 步骤 4 用本地拷贝替代 git clone）
# ══════════════════════════════════════════════════════════════════════
# ── Dependency scan helpers ──────────────────────────────────────────
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

do_install() {
    # 步骤 0: 依赖检查（扫描已装依赖，缺失时询问是否安装）
    step "Dependency check"
    if [ "${SKIP_DEPS:-0}" = "1" ]; then
        echo -e "${WARN} --skip-deps: skipping dependency installation"
    elif check_system_deps && check_python_deps; then
        echo -e "${OK} All dependencies already installed — skipping"
        SKIP_DEPS=1
    else
        echo -e "${WARN} Some dependencies are missing (system or Python packages)"
        read -r -p "Install dependencies now? [Y/n] " _ans || _ans=""
        case "${_ans}" in
            n|N) echo -e "${WARN} Skipping dependency installation"; SKIP_DEPS=1 ;;
            *)   echo -e "${OK} Will install missing dependencies" ;;
        esac
    fi
    done_step "Dependency check complete"

    # 步骤 1: 系统依赖
    step "System dependencies"
    export DEBIAN_FRONTEND=noninteractive
    if [ "${SKIP_DEPS:-0}" != "1" ]; then
        _ensure_apt_mirror
        apt-get update
        apt-get install -y python3 python3-venv python3-pip python3-dev \
            nginx git curl wget build-essential libpq-dev libssl-dev
    else
        echo -e "${WARN} Skipped (deps already present or --skip-deps)"
    fi
    done_step "System dependencies installed"

    PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")

    # 步骤 2: PostgreSQL
    step "PostgreSQL"
    if ! systemctl is-active --quiet postgresql 2>/dev/null; then
        if [ "${SKIP_DEPS:-0}" = "1" ]; then
            echo -e "${FAIL} postgresql not running, but dependency installation was skipped"
            exit 1
        fi
        apt-get install -y postgresql postgresql-client
        systemctl enable --now postgresql
    fi
    # 审计 C1 加固：密码经临时 SQL 文件（600 权限）传入 psql -f，避免出现在进程命令行
    _sql_tmp=$(mktemp)
    chmod 600 "${_sql_tmp}"
    if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='verorun'" 2>/dev/null | grep -q 1; then
        printf "ALTER ROLE verorun WITH LOGIN PASSWORD '%s';\n" "${PG_PASSWORD}" > "${_sql_tmp}"
    else
        printf "CREATE ROLE verorun WITH LOGIN PASSWORD '%s';\n" "${PG_PASSWORD}" > "${_sql_tmp}"
    fi
    sudo -u postgres psql -q -f "${_sql_tmp}" 2>/dev/null || true
    rm -f "${_sql_tmp}"
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='verorun'" | grep -q 1 2>/dev/null || \
        sudo -u postgres psql -c "CREATE DATABASE verorun OWNER verorun" 2>/dev/null || true
    # 铁律：install-code.sh 只允许创建系统库，插件数据库一律不建
    done_step "PostgreSQL is running"

    # 步骤 3: 创建目录
    step "Create directories"
    mkdir -p "${APP_HOME}" "${APP_HOME}/data" "${LOG_DIR}"
    mkdir -p "${APP_HOME}/.cache/llm" "${APP_HOME}/.cache/sessions" "${APP_HOME}/.cache/agents"
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${LOG_DIR}" 2>/dev/null || true
    done_step "Directories ready"

    # 步骤 4: 拷贝源码 [核心差异点]
    step "Copy source code"
    if [ -n "${FROM_TAR:-}" ]; then
        echo -e "${INFO} Source already extracted from tar, skipping copy"
    else
        local src_dir="${SOURCE_DIR}"
        if [ -z "${src_dir}" ]; then
            # 默认: 脚本所在目录的上一级
            src_dir="$(cd "$(dirname "$0")/.." && pwd)"
        fi
        copy_source_code "${src_dir}" "${APP_HOME}"
    fi
    done_step "Source code in place (full, all plugins)"

    # 步骤 5: Python 虚拟环境
    step "Python virtual environment"
    if [ "${SKIP_DEPS:-0}" != "1" ]; then
        if [ ! -f "${VENV_DIR}/bin/python" ]; then
            sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
        fi
        _pip_install --upgrade pip
        _pip_install -r "${APP_HOME}/requirements.txt"
    else
        echo -e "${WARN} Skipped (deps already present or --skip-deps)"
    fi
    done_step "Python dependencies installed"

    # 步骤 6: 生成 .env
    step "Generate .env (no-domain mode)"
    generate_env force
    done_step ".env generated (DEPLOY_DOMAIN empty, DEPLOY_PROTOCOL=http)"

    # 步骤 7: systemd 服务
    step "systemd services"
    write_systemd_services
    done_step "systemd services configured"

    # 步骤 8: Nginx
    step "Nginx (path routing)"
    write_nginx_config
    nginx -t && systemctl restart nginx
    done_step "Nginx configured"

    # 步骤 9: 启动服务
    step "Start services"
    restart_services
    done_step "Services started"

    # 步骤 10: sudoers
    step "Configure sudoers (one-click restart permissions)"
    write_sudoers
    done_step "Sudoers configured"

    # 步骤 11: 数据库迁移
    step "Database migration"
    sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; cd ${APP_HOME} && PYTHONPATH=${APP_HOME}/auth-center ${VENV_DIR}/bin/python -c 'from models.database import init_db; init_db()'"
    done_step "Database migrated"

    # 步骤 12: 种子数据
    step "Seed data"
    do_seed
    done_step "Seed data injected"

    print_summary
}

# ── Summary ───────────────────────────────────────────────────────────
print_summary() {
    local PUBLIC_IP
    PUBLIC_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo ""
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║         Local Source Deployment Complete!                    ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Main site:   http://localhost/                               ║"
    echo "  ║  Admin:       http://localhost/admin/                         ║"
    echo "  ║  Console:     http://localhost/auth/                          ║"
    if [ -n "${PUBLIC_IP}" ]; then
    echo "  ║  LAN access:  http://${PUBLIC_IP}/  (same paths)              ║"
    fi
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Plugins:     $(ls -d ${APP_HOME}/plugins/*/ 2>/dev/null | wc -l) installed                      ║"
    echo "  ║  Code size:   $(du -sh ${APP_HOME} 2>/dev/null | cut -f1)                         ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Useful commands:                                            ║"
    echo "  ║    systemctl status verorun-{main,auth,admin,guardian}       ║"
    echo "  ║    bash deploy/install-code.sh restart                        ║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ══════════════════════════════════════════════════════════════════════
# Main entry
# ══════════════════════════════════════════════════════════════════════
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash deploy/install-code.sh"
    exit 1
fi

# 解析参数
MODE="install"
for arg in "$@"; do
    case "${arg}" in
        --src=*) SOURCE_DIR="${arg#*=}" ;;
        --from-tar=*) FROM_TAR="${arg#*=}" ;;
        --region=*) REGION="${arg#*=}" ;;
        --skip-deps) SKIP_DEPS=1 ;;
        seed) MODE="seed" ;;
        restart) MODE="restart" ;;
    esac
done

if [ "${REGION}" != "cn" ] && [ "${REGION}" != "global" ]; then
    echo -e "${FAIL} --region must be 'cn' or 'global' (got: ${REGION})"
    exit 1
fi
echo -e "${INFO} Region: ${REGION}"

case "${MODE}" in
    install)
        # 如果指定了 --from-tar，先解压到 APP_HOME 再走安装流程
        if [ -n "${FROM_TAR}" ]; then
            extract_from_tar "${FROM_TAR}" "${APP_HOME}"
        fi
        do_install
        ;;
    seed)
        do_seed
        ;;
    restart)
        restart_services
        ;;
esac
