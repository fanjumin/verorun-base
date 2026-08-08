#!/bin/bash
# ==========================================================================
# VeroRun — Local / LAN deployment script (no public domain required)
# ==========================================================================
# Usage:
#   sudo bash deploy/install-local.sh
#   sudo bash deploy/install-local.sh --skip-deps     # skip dependency install
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
: "${GIT_REPO:=git@github.com:fanjumin/verorun-code.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
: "${APP_HOME:=/home/${APP_USER}/verorun}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${REGION:=global}"                # cn | global
: "${SPARSE_DIRS:=admin auth-center main_site health_service veroguard plugin_manager plugins agent_matrix orchestrator i18n captcha-service shared providers themes static deploy}"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; WARN="${YELLOW}[WARN]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"

# ── Pip mirror: auto-detect PyPI connectivity ──
PIP_MIRROR=""
if command -v curl >/dev/null 2>&1 && curl -s --connect-timeout 3 https://pypi.org >/dev/null 2>&1; then
    : # pypi.org reachable
else
    PIP_MIRROR="-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
fi
_pip_install() {
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --timeout 120 --prefer-binary ${PIP_MIRROR} "$@"
}

step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }

# ── Git SSH auth setup (skip for HTTPS public repo) ───────────────────
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

# ── .env generation — no-domain mode ──────────────────────────────────
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

    cat > "${env_file}" << ENVEOF
# VeroRun config — auto-generated by install-local.sh (no-domain / LAN mode)
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

# v2.1.0 — mini_app_builder 插件独立数据库
MINI_APP_PG_DB=verorun_miniapp

# v2.1.0 — site_builder 插件独立数据库
SITE_BUILDER_PG_DB=verorun_sitebuilder

# Local/LAN mode: DEBUG enabled for development convenience
APP_DEBUG=true
FLASK_DEBUG=1

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
}

# ── systemd services — identical to install.sh ────────────────────────
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
    write_one_service "verorun-admin" 8084 "admin.app" "--timeout 120 --max-requests=1000 --graceful-timeout=30 --log-level warning --config admin/gunicorn_config.py" "admin/run_gunicorn.py" "verorun"
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
# VeroGuard Guardian environment config — generated by install-local.sh
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

# ── sudoers — one-click update permissions (declarative, idempotent) ──
write_sudoers() {
    local sudoers_file="/etc/sudoers.d/verorun"
    cat > "${sudoers_file}" << SUEOF
# Managed by VeroRun install-local.sh — regenerated on every install/update
# Grants ${APP_USER} passwordless one-click update for VeroRun services
${APP_USER} ALL=(root) NOPASSWD: /bin/bash ${APP_HOME}/deploy/install.sh update
${APP_USER} ALL=(root) NOPASSWD: /bin/bash ${APP_HOME}/deploy/install.sh restart
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
# VeroRun Nginx — no-domain mode (auto-generated by install-local.sh)

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
        echo -e "${INFO} Run 'install-local.sh' first"
        exit 1
    fi
    local _seed_args=""
    if [ -n "${VR_ADMIN_USERNAME:-}" ]; then
        _seed_args="--admin-user ${VR_ADMIN_USERNAME} --admin-pass ${VR_ADMIN_PASSWORD}"
    fi
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" "${APP_HOME}/deploy/seed_data.py" ${_seed_args}
    echo -e "${OK} Seed data injected"
}

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

# ── Fresh install (no-domain) ─────────────────────────────────────────
do_install() {
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

    step "System dependencies"
    export DEBIAN_FRONTEND=noninteractive
    if [ "${SKIP_DEPS:-0}" != "1" ]; then
        apt-get update
        apt-get install -y python3 python3-venv python3-pip python3-dev \
            nginx git curl wget build-essential libpq-dev libssl-dev
    else
        echo -e "${WARN} Skipped (deps already present or --skip-deps)"
    fi
    done_step "System dependencies installed"

    PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")

    step "PostgreSQL"
    if ! systemctl is-active --quiet postgresql 2>/dev/null; then
        if [ "${SKIP_DEPS:-0}" = "1" ]; then
            echo -e "${FAIL} postgresql not running, but dependency installation was skipped"
            exit 1
        fi
        apt-get install -y postgresql postgresql-client
        systemctl enable --now postgresql
    fi
    if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='verorun'" 2>/dev/null | grep -q 1; then
        sudo -u postgres psql -c "ALTER ROLE verorun WITH LOGIN PASSWORD '${PG_PASSWORD}'" 2>/dev/null || true
    else
        sudo -u postgres psql -c "CREATE ROLE verorun WITH LOGIN PASSWORD '${PG_PASSWORD}'" 2>/dev/null || true
    fi
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='verorun'" | grep -q 1 2>/dev/null || \
        sudo -u postgres psql -c "CREATE DATABASE verorun OWNER verorun" 2>/dev/null || true
    # v2.1.0：mini_app_builder 插件独立数据库（同实例新库，数据库级物理隔离）
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='verorun_miniapp'" | grep -q 1 2>/dev/null || \
        sudo -u postgres psql -c "CREATE DATABASE verorun_miniapp OWNER verorun" 2>/dev/null || true
    # v2.1.0：site_builder 插件独立数据库（同实例新库，数据库级物理隔离）
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='verorun_sitebuilder'" | grep -q 1 2>/dev/null || \
        sudo -u postgres psql -c "CREATE DATABASE verorun_sitebuilder OWNER verorun" 2>/dev/null || true
    done_step "PostgreSQL is running"

    step "Create directories"
    mkdir -p "${APP_HOME}" "${APP_HOME}/data" "${LOG_DIR}"
    mkdir -p "${APP_HOME}/.cache/llm" "${APP_HOME}/.cache/sessions" "${APP_HOME}/.cache/agents"
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${LOG_DIR}" 2>/dev/null || true
    done_step "Directories ready"

    ensure_git_auth

    step "Pull code"
    if [ -d "${APP_HOME}/.git" ]; then
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        git fetch origin "${GIT_BRANCH}"
        git reset --hard "origin/${GIT_BRANCH}"
    else
        if [ -n "${APP_HOME}" ] && [ "${APP_HOME}" != "/" ] && [ "${APP_HOME}" != "${HOME}" ]; then
            rm -rf "${APP_HOME}"
        else
            echo -e "${FAIL} Refusing to remove APP_HOME='${APP_HOME}'"
            exit 1
        fi
        git clone -b "${GIT_BRANCH}" "${GIT_REPO}" "${APP_HOME}"
    fi
    if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
        git -C "${APP_HOME}" sparse-checkout init --cone 2>/dev/null || true
        git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS}
    fi
    find "${APP_HOME}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    done_step "Code pulled ($(git -C "${APP_HOME}" log --oneline -1))"

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

    step "Generate .env (no-domain mode)"
    generate_env force
    done_step ".env generated (DEPLOY_DOMAIN empty, DEPLOY_PROTOCOL=http)"

    step "systemd services"
    write_systemd_services
    done_step "systemd services configured"

    step "Nginx (path routing)"
    write_nginx_config
    nginx -t && systemctl restart nginx
    done_step "Nginx configured"

    step "Start services"
    restart_services
    done_step "Services started"

    step "Configure sudoers (one-click update permissions)"
    write_sudoers
    done_step "Sudoers configured"

    step "Database migration"
    sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; cd ${APP_HOME} && PYTHONPATH=${APP_HOME}/auth-center ${VENV_DIR}/bin/python -c 'from models.database import init_db; init_db()'"
    done_step "Database migrated"

    step "Seed data"
    do_seed
    done_step "Seed data injected"

    print_summary
}

# ── Summary ───────────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║         No-domain / LAN Deployment Complete!                  ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Main site:   http://localhost/                               ║"
    echo "  ║  Admin:       http://localhost/admin/                         ║"
    echo "  ║  Console:     http://localhost/auth/                          ║"
    local PUBLIC_IP
    PUBLIC_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -n "${PUBLIC_IP}" ]; then
    echo "  ║  LAN access:  http://${PUBLIC_IP}/  (same paths)              ║"
    fi
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Useful commands:                                            ║"
    echo "  ║    systemctl status verorun-{main,auth,admin,guardian}       ║"
    echo "  ║    bash deploy/install.sh update                              ║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ── Main entry ──────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash deploy/install-local.sh"
    exit 1
fi

# Parse --region flag
for arg in "$@"; do
    case "${arg}" in
        --region=*) REGION="${arg#*=}" ;;
        --skip-deps) SKIP_DEPS=1 ;;
    esac
done
if [ "${REGION}" != "cn" ] && [ "${REGION}" != "global" ]; then
    echo -e "${FAIL} --region must be 'cn' or 'global' (got: ${REGION})"
    exit 1
fi
echo -e "${INFO} Region: ${REGION}"

do_install
