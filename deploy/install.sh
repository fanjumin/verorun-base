#!/bin/bash
# ==========================================================================
# VeroRun — One-command deploy script (v2.1)
# ==========================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/install.sh | sudo bash   # fresh install
#   sudo bash deploy/install.sh update           # update code, deps, and restart
#   sudo bash deploy/install.sh restart          # restart services only
#   sudo bash deploy/install.sh health           # health check
#   sudo bash deploy/install.sh rollback         # rollback to previous commit
#   sudo bash deploy/install.sh seed             # seed initial data (admin, plans, products)
#   sudo bash deploy/install.sh configure-domain  # configure domain post-install
# ==========================================================================
set -euo pipefail

# ── Default config ────────────────────────────────────────────────────
: "${DEPLOY_MODE:=update}"              # install | update | restart | health | rollback | seed | configure-domain
: "${GIT_REPO:=https://github.com/fanjumin/VeroRunSystem.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=${SUDO_USER:-$(whoami)}}"
: "${APP_HOME:=/home/${APP_USER}/verorun}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/verorun}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${DOMAIN:=}"

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; WARN="${YELLOW}[WARN]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"

step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }
fail_step() { echo -e "${FAIL} $1"; }

# ── Mode / Domain detection ──────────────────────────────────────────

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

detect_domain() {
    local domain_arg="${1:-}"
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
        echo -e "${INFO}   sudo bash deploy/install.sh configure-domain <your-domain>"
    else
        echo -e "${OK} Domain set to: ${DOMAIN}"
    fi
}

# ==========================================================================
# Fresh install
# ==========================================================================
do_install() {
    step "System dependencies"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y python3 python3-venv python3-pip python3-dev \
        nginx git curl wget build-essential libpq-dev libssl-dev
    done_step "System dependencies installed"

    # Generate PG password early so PostgreSQL role and .env match
    PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")

    step "PostgreSQL"
    if ! systemctl is-active --quiet postgresql 2>/dev/null; then
        apt-get install -y postgresql postgresql-client
        systemctl enable --now postgresql
    fi

    # Ensure role exists and password matches .env
    if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='verorun'" 2>/dev/null | grep -q 1; then
        sudo -u postgres psql -c "ALTER ROLE verorun WITH LOGIN PASSWORD '${PG_PASSWORD}'" 2>/dev/null || true
    else
        sudo -u postgres psql -c "CREATE ROLE verorun WITH LOGIN PASSWORD '${PG_PASSWORD}'" 2>/dev/null || true
    fi
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='verorun'" | grep -q 1 2>/dev/null || \
        sudo -u postgres psql -c "CREATE DATABASE verorun OWNER verorun" 2>/dev/null || true
    done_step "PostgreSQL is running"

    step "Create directories"
    mkdir -p "${APP_HOME}" "${APP_HOME}/data" "${LOG_DIR}"
    mkdir -p "${APP_HOME}/.cache/llm" \
             "${APP_HOME}/.cache/sessions" \
             "${APP_HOME}/.cache/agents"
    # Clean stale __pycache__ before chown (avoids race-condition failures)
    find "${APP_HOME}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${LOG_DIR}" 2>/dev/null || true
    done_step "Directories ready"

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
    # Clean stale __pycache__ before chown (avoids race-condition failures)
    find "${APP_HOME}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    done_step "Code pulled ($(git -C "${APP_HOME}" log --oneline -1))"

    step "Python virtual environment"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
    fi
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip
    # --only-binary: fail fast if no pre-built wheel instead of compiling for hours
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --only-binary=:all: -r "${APP_HOME}/requirements.txt"
    done_step "Python dependencies installed"

    prompt_domain

    step "Generate .env"
    generate_env force
    done_step ".env generated"

    if [ -z "${DOMAIN}" ]; then
        echo -e "${WARN} Domain not configured. System and nginx not started."
        echo -e "${INFO} After install, run:"
        echo -e "${INFO}   sudo bash deploy/install.sh configure-domain <your-domain>"
    else
        step "systemd services"
        write_systemd_services
        done_step "systemd services configured"

        step "Nginx"
        write_nginx_config
        nginx -t && systemctl restart nginx
        done_step "Nginx configured"

        step "Start services"
        restart_services
        done_step "Services started"
    fi

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

# ==========================================================================
# Incremental update
# ==========================================================================
do_update() {
    # Self-update tracking: md5 of currently-running install.sh
    UPDATE_MD5=$(md5sum "${APP_HOME}/deploy/install.sh" 2>/dev/null | awk '{print $1}') || UPDATE_MD5=""

    # Read domain from existing .env
    DOMAIN=$(grep "^DEPLOY_DOMAIN=" "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2) || true

    local before_commit
    before_commit=$(git -C "${APP_HOME}" log --oneline -1 2>/dev/null || echo "unknown")

    step "Backup current version"
    # Ensure .cache/ dirs exist (fresh install or upgrade from pre-cache version)
    mkdir -p "${APP_HOME}/.cache/llm" \
             "${APP_HOME}/.cache/sessions" \
             "${APP_HOME}/.cache/agents"
    mkdir -p "${APP_HOME}/.rollback"
    cp "${APP_HOME}/.env" "${APP_HOME}/.rollback/.env.bak" 2>/dev/null || true
    done_step "Environment backed up"

    step "Pull latest code"
    if [ ! -d "${APP_HOME}/.git" ]; then
        echo -e "${WARN} .git missing — re-cloning repository"
        if [ -n "${APP_HOME}" ] && [ "${APP_HOME}" != "/" ] && [ "${APP_HOME}" != "${HOME}" ]; then
            rm -rf "${APP_HOME}"
        else
            echo -e "${FAIL} Refusing to remove APP_HOME='${APP_HOME}'"
            exit 1
        fi
        git clone -b "${GIT_BRANCH}" "${GIT_REPO}" "${APP_HOME}"
    else
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        git fetch origin "${GIT_BRANCH}"
        git merge "origin/${GIT_BRANCH}" --ff-only 2>/dev/null || {
            echo -e "${WARN} Fast-forward merge failed, falling back to reset"
            git reset --hard "origin/${GIT_BRANCH}"
        }
    fi
    local after_commit
    after_commit=$(git log --oneline -1)
    done_step "Code updated: ${before_commit:0:7} -> ${after_commit:0:7}"

    # Self-update: if install.sh itself changed, re-run update with new version
    local script_md5
    script_md5=$(md5sum "${APP_HOME}/deploy/install.sh" | awk '{print $1}')
    if [ "${UPDATE_MD5}" != "${script_md5}" ]; then
        echo -e "${INFO} install.sh updated, re-running with new version..."
        exec sudo APP_HOME="${APP_HOME}" bash "${APP_HOME}/deploy/install.sh" update
        exit
    fi

    step "Update .env (fill missing keys)"
    update_env
    done_step ".env synced"

    step "Update Python dependencies"
    req_hash=$(md5sum "${APP_HOME}/requirements.txt" | awk '{print $1}')
    cached_hash=$(cat "${APP_HOME}/.requirements_hash" 2>/dev/null || echo "")
    if [ "${req_hash}" != "${cached_hash}" ]; then
        sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --only-binary=:all: -r "${APP_HOME}/requirements.txt"
        echo "${req_hash}" > "${APP_HOME}/.requirements_hash"
    else
        echo -e "${INFO} requirements.txt unchanged, skipping pip install"
    fi
    done_step "Dependencies updated"

    step "Update systemd services"
    write_systemd_services
    done_step "Systemd services updated"

    step "Update sudoers (one-click update permissions)"
    write_sudoers
    done_step "Sudoers updated"

    step "Update Nginx config"
    write_nginx_config
    nginx -t && systemctl restart nginx
    done_step "Nginx config updated"

    step "Pre-flight check"
    # 验证数据库可连接
    if ! sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; ${VENV_DIR}/bin/python -c \"
from plugins._base.db import get_raw_connection
c = get_raw_connection()
c.close()
print('DB OK')
\""; then
        echo -e "${FAIL} Database not accessible — aborting update"
        exit 1
    fi
    # 验证 Python 语法无致命错误
    if ! sudo -u "${APP_USER}" bash -c "${VENV_DIR}/bin/python -m py_compile ${APP_HOME}/admin/app.py"; then
        echo -e "${FAIL} Syntax error in new code — aborting update"
        exit 1
    fi
    done_step "Pre-flight passed"

    step "Restart services"
    restart_services
    done_step "Services restarted"

    step "Health check"
    health_check
}

# ==========================================================================
# Seed initial data
# ==========================================================================
# ── Admin credentials temp file ──────────────────────────────────────
VR_ADMIN_CREDS_FILE="/tmp/verorun-admin-creds"

do_seed() {
    step "Seed initial data"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        echo -e "${FAIL} Python venv not found at ${VENV_DIR}"
        echo -e "${INFO} Run 'install.sh install' first"
        exit 1
    fi

    # Read credentials from temp file (set by prompt_admin_creds before detach)
    VR_ADMIN_USERNAME=""
    VR_ADMIN_PASSWORD=""
    if [ -f "${VR_ADMIN_CREDS_FILE}" ]; then
        # shellcheck disable=SC1090
        source "${VR_ADMIN_CREDS_FILE}"
        rm -f "${VR_ADMIN_CREDS_FILE}"
    fi

    if [ -z "${VR_ADMIN_USERNAME}" ]; then
        echo -e "${INFO} No admin credentials provided — username will be auto-generated"
    fi

    local _seed_args=""
    if [ -n "${VR_ADMIN_USERNAME}" ]; then
        _seed_args="--admin-user ${VR_ADMIN_USERNAME} --admin-pass ${VR_ADMIN_PASSWORD}"
    fi
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" "${APP_HOME}/deploy/seed_data.py" ${_seed_args}
    echo -e "${OK} Seed data injected"
}

# Prompt for admin credentials BEFORE detach (while TTY is still alive).
# Saves to a temp file that survives setsid+nohup.
prompt_admin_creds() {
    case "${DEPLOY_MODE}" in install) ;; *) return 0 ;; esac

    # If already set (e.g. re-run after detach), skip
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

    cat > "${VR_ADMIN_CREDS_FILE}" << CREDS_EOF
VR_ADMIN_USERNAME="${_user}"
VR_ADMIN_PASSWORD="${_pass}"
CREDS_EOF
    echo -e "${OK} Admin credentials saved"
}

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
        echo -e "${FAIL} .env not found. Run 'install.sh install' first."
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
# Rollback
# ==========================================================================
do_rollback() {
    step "Rollback to previous version"
    cd "${APP_HOME}"
    git reflog --oneline -5 | head -5
    if git reset --hard HEAD~1; then
        systemctl restart verorun-admin verorun-auth verorun-main verorun-health verorun-guardian
        echo -e "${OK} Rolled back to $(git log --oneline -1)"
    else
        echo -e "${FAIL} Rollback failed"
    fi
}

# ==========================================================================
# .env management
# ==========================================================================
generate_env() {
    local env_file="${APP_HOME}/.env"
    local force="${1:-}"

    if [ -f "${env_file}" ] && [ "${force}" != "force" ]; then
        echo -e "${WARN} .env already exists, skipping"
        return
    fi

    # Backup existing .env on force overwrite
    if [ -f "${env_file}" ] && [ "${force}" = "force" ]; then
        cp "${env_file}" "${env_file}.bak.$(date +%s)" 2>/dev/null || true
        echo -e "${INFO} Existing .env backed up"
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
# VeroRun production config — auto-generated by install.sh
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=${DOMAIN}
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

# Phase 1 — Security hardening keys (2026-07-28)
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}

# VeroGuard — 守护进程加密通信密钥（官方端与客户端需一致）
PROBE_SECRET=${PROBE_SECRET}

# API Keys (replace with real values)
DASHSCOPE_TEXT_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here
ENVEOF

    chown "${APP_USER}:${APP_USER}" "${env_file}"
    chmod 600 "${env_file}"
}

update_env() {
    local env_file="${APP_HOME}/.env"
    if [ ! -f "${env_file}" ]; then
        generate_env
        return
    fi

    # Fill missing Phase 1 keys
    local missing=()
    for key in PLUGIN_LICENSE_SECRET CAPTCHA_SECRET_KEY DEV_ACCOUNTS_ENCRYPTION_KEY LICENSE_SERVER_SECRET PROBE_SECRET; do
        if ! grep -q "^${key}=" "${env_file}" 2>/dev/null; then
            local val
            val=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            echo "${key}=${val}" >> "${env_file}"
            missing+=("${key}")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${OK} Filled missing keys: ${missing[*]}"
        chmod 600 "${env_file}"
    else
        echo -e "${OK} All keys are present in .env"
    fi
}

# ==========================================================================
# systemd services
# ==========================================================================
write_systemd_services() {
    local env_file="${APP_HOME}/.env"

    write_one_service() {
        local name=$1 port=$2 module=$3 extra_args="${4:-}" runner="${5:-}"
        local file="${SERVICE_DIR}/${name}.service"

        if [ -n "${runner}" ]; then
            local exec_cmd="${VENV_DIR}/bin/python ${APP_HOME}/${runner} -w 2 -b 127.0.0.1:${port} ${extra_args} ${module}:app"
        else
            local exec_cmd="${VENV_DIR}/bin/gunicorn -w 2 -b 127.0.0.1:${port} ${extra_args} ${module}:app"
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
# 启动健康检查：30 秒内 /health 不返回 200 → systemd 认为启动失败
ExecStartPost=/bin/bash -c 'for i in $(seq 1 30); do curl -sf http://127.0.0.1:${port}/health && exit 0; sleep 1; done; exit 1'
StandardOutput=append:${LOG_DIR}/${name}.log
StandardError=append:${LOG_DIR}/${name}.log

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
    write_one_service "verorun-admin" 8084 "admin.app" "--timeout 120 --max-requests=1000 --graceful-timeout=30 --log-level warning --config admin/gunicorn_config.py" "admin/run_gunicorn.py"

    # 8085 — Health Check
    write_one_service "verorun-health" 8085 "health_service.app" "--timeout 30 --graceful-timeout=30 --log-level warning"

    # ── verorun-guardian (独立守护进程，不占用端口) ──
    write_guardian_service
    write_guardian_env
}

# ==========================================================================
# Guardian service + env
# ==========================================================================
write_guardian_service() {
    local file="${SERVICE_DIR}/verorun-guardian.service"
    cat > "${file}" << 'GDEVEOF'
[Unit]
Description=VeroGuard — Unified Guardian Daemon (Health + Integrity + Heartbeat)
After=network.target postgresql.service
Wants=verorun-health.service verorun-main.service verorun-admin.service verorun-auth.service

[Service]
Type=simple
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
    # Replace placeholder with actual path
    sed -i "s|GDEVDIR|${APP_HOME}|g" "${file}"
    systemctl daemon-reload
    systemctl enable verorun-guardian
}

write_guardian_env() {
    local env_file="/etc/default/verorun-guardian"
    # Read PROBE_SECRET from .env
    local probe_secret=""
    if [ -f "${APP_HOME}/.env" ]; then
        probe_secret=$(grep "^PROBE_SECRET=" "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2) || true
        [ -n "${probe_secret}" ] && probe_secret="PROBE_SECRET=${probe_secret}"
    fi
    cat > "${env_file}" << GENVEOF
# VeroGuard Guardian 环境配置 — 由 install.sh 生成
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

# ==========================================================================
# sudoers — one-click update permissions (declarative, idempotent)
# Grants APP_USER passwordless access to run install.sh and restart the
# VeroRun systemd services. Scoped to the minimum command set.
# ==========================================================================
write_sudoers() {
    local sudoers_file="/etc/sudoers.d/verorun"
    cat > "${sudoers_file}" << SUEOF
# Managed by VeroRun install.sh — regenerated on every install/update
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
            sleep 2
            if systemctl is-active --quiet "${svc}"; then
                echo -e "${OK} ${svc} is running"
            else
                echo -e "${FAIL} ${svc} failed to start — check: journalctl -u ${svc} -n 20"
            fi
        else
            echo -e "${WARN} ${svc} not configured, skipping"
        fi
    done

    # Also ensure nginx is running after service restart
    if systemctl is-enabled --quiet nginx 2>/dev/null; then
        systemctl restart nginx
        echo -e "${OK} nginx restarted"
    fi
}

# ==========================================================================
# Nginx
# ==========================================================================
write_nginx_config() {
    local nginx_conf="/etc/nginx/sites-available/verorun.conf"
    local nginx_enabled="/etc/nginx/sites-enabled/verorun.conf"

    cat > "${nginx_conf}" << NGXEOF
# VeroRun Nginx — auto-generated by install.sh

# ── Main domain ────────────────────────────────
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    # ── Admin ─────────────────────────────────
    location /admin/ {
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    # ── Auth / subscribe ─────────────────────
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

    # ── Main site ───────────────────────────────
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}

# ── Platform subdomain ─────────────────────────
server {
    listen 80;
    server_name platform.${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# ── Agent subdomain ────────────────────────────
server {
    listen 80;
    server_name agent.${DOMAIN};
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGXEOF

    rm -f /etc/nginx/sites-enabled/default
    ln -sf "${nginx_conf}" "${nginx_enabled}"
}

# ==========================================================================
# Health check
# ==========================================================================
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

    # Guardian: 无 HTTP 端口，通过 systemctl 检查
    if systemctl is-active --quiet verorun-guardian 2>/dev/null; then
        echo -e "  ${OK} verorun-guardian (systemd)"
    else
        echo -e "  ${FAIL} verorun-guardian (inactive)"
        all_ok=false
    fi

    # Check DDL migration logs
    echo ""
    echo -e "${INFO} Migration log check:"
    for svc in verorun-admin verorun-auth verorun-main; do
        journalctl -u "${svc}" --since "1 min ago" 2>/dev/null | grep -i "\[Migration\]" | tail -2 || true
    done

    if $all_ok; then
        echo -e "\n${OK} All services healthy"
    else
        echo -e "\n${FAIL} Some services are unhealthy — check logs"
    fi
}

# ==========================================================================
# Summary
# ==========================================================================
print_summary() {
    local PUBLIC_IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "unknown")

    echo ""
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║              Deployment Complete!                             ║"
    if [ -n "${DOMAIN}" ]; then
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Main site:  https://${DOMAIN}                                 ║"
    echo "  ║  Platform:   https://platform.${DOMAIN}                        ║"
    echo "  ║  Admin:      https://agent.${DOMAIN}/admin/                    ║"
    fi
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Useful commands:                                            ║"
    echo "  ║    systemctl status verorun-{main,auth,admin,guardian}       ║"
    echo "  ║    journalctl -u verorun-guardian -f                         ║"
    echo "  ║    bash deploy/install.sh update                              ║"
    echo "  ║    bash deploy/install.sh rollback                            ║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ==========================================================================
# Main entry
# ==========================================================================

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash install.sh [install|update|restart|health|rollback|seed|configure-domain]"
    exit 1
fi

detect_mode "${1:-}"
detect_domain "${2:-}"

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
        do_configure_domain "${2:-}"
        ;;
    *)
        echo "Usage: sudo bash install.sh [install|update|restart|health|rollback|seed|configure-domain <domain>]"
        exit 1
        ;;
esac
