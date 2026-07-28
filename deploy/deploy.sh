#!/bin/bash
# ==========================================================================
# VeroRun — One-command deploy script (v2.1)
# ==========================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/deploy.sh | sudo bash   # fresh install
#   sudo bash deploy/deploy.sh update           # update code, deps, and restart
#   sudo bash deploy/deploy.sh restart          # restart services only
#   sudo bash deploy/deploy.sh health           # health check
#   sudo bash deploy/deploy.sh rollback         # rollback to previous commit
# ==========================================================================
set -euo pipefail

# ── Default config ────────────────────────────────────────────────────
: "${DEPLOY_MODE:=update}"              # install | update | restart | health | rollback
: "${GIT_REPO:=https://github.com/fanjumin/VeroRunSystem.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=verorun}"
: "${APP_HOME:=/home/${APP_USER}/verorun-workspace}"
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
    while [ -z "${DOMAIN}" ]; do
        read -p "  Enter your domain (e.g., verorun.com): " DOMAIN
        if [ -z "${DOMAIN}" ]; then
            echo -e "${FAIL} Domain cannot be empty. Please enter a valid domain."
        fi
    done
    echo -e "${OK} Domain set to: ${DOMAIN}"
}

# ==========================================================================
# Fresh install
# ==========================================================================
do_install() {
    prompt_domain

    step "System dependencies"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip python3-dev \
        nginx git curl wget build-essential libpq-dev libssl-dev
    done_step "System dependencies installed"

    step "PostgreSQL"
    if ! systemctl is-active --quiet postgresql 2>/dev/null; then
        apt-get install -y -qq postgresql postgresql-client
        systemctl enable --now postgresql
    fi
    done_step "PostgreSQL is running"

    step "Create user & directories"
    if ! id "${APP_USER}" &>/dev/null; then
        useradd -m -s /bin/bash "${APP_USER}"
    fi
    mkdir -p "${APP_HOME}" "${LOG_DIR}"
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" "${LOG_DIR}"
    done_step "User ${APP_USER} ready"

    step "Pull code"
    if [ -d "${APP_HOME}/.git" ]; then
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        git fetch origin "${GIT_BRANCH}"
        git reset --hard "origin/${GIT_BRANCH}"
    else
        rm -rf "${APP_HOME}"
        git clone -b "${GIT_BRANCH}" "${GIT_REPO}" "${APP_HOME}"
    fi
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}"
    done_step "Code pulled ($(git -C "${APP_HOME}" log --oneline -1))"

    step "Python virtual environment"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
    fi
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip -q
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -r "${APP_HOME}/requirements.txt" -q
    done_step "Python dependencies installed"

    step "Generate .env"
    generate_env
    done_step ".env generated"

    step "systemd services"
    write_systemd_services
    done_step "systemd services configured"

    step "Nginx"
    write_nginx_config
    nginx -t && systemctl reload nginx
    done_step "Nginx configured"

    step "Start services"
    restart_services
    done_step "Services started"

    print_summary
}

# ==========================================================================
# Incremental update
# ==========================================================================
do_update() {
    # Read domain from existing .env
    DOMAIN=$(grep "^DEPLOY_DOMAIN=" "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2) || true

    local before_commit
    before_commit=$(git -C "${APP_HOME}" log --oneline -1 2>/dev/null || echo "unknown")

    step "Backup current version"
    mkdir -p "${APP_HOME}/.rollback"
    cp "${APP_HOME}/.env" "${APP_HOME}/.rollback/.env.bak" 2>/dev/null || true
    done_step "Environment backed up"

    step "Pull latest code"
    git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
    cd "${APP_HOME}"
    git fetch origin "${GIT_BRANCH}"
    git merge "origin/${GIT_BRANCH}" --ff-only 2>/dev/null || {
        echo -e "${WARN} Fast-forward merge failed, falling back to reset"
        git reset --hard "origin/${GIT_BRANCH}"
    }
    local after_commit
    after_commit=$(git log --oneline -1)
    done_step "Code updated: ${before_commit:0:7} → ${after_commit:0:7}"

    step "Update .env (fill missing keys)"
    update_env
    done_step ".env synced"

    step "Update Python dependencies"
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -r "${APP_HOME}/requirements.txt" -q
    done_step "Dependencies updated"

    step "Restart services"
    restart_services
    done_step "Services restarted"

    step "Health check"
    health_check
}

# ==========================================================================
# Rollback
# ==========================================================================
do_rollback() {
    step "Rollback to previous version"
    cd "${APP_HOME}"
    git reflog --oneline -5 | head -5
    if git reset --hard HEAD~1; then
        systemctl restart verorun-admin verorun-auth verorun-main
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
    if [ -f "${env_file}" ]; then
        echo -e "${WARN} .env already exists, skipping"
        return
    fi

    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    PLUGIN_LICENSE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    CAPTCHA_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    DEV_ACCOUNTS_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    LICENSE_SERVER_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > "${env_file}" << ENVEOF
# VeroRun production config — auto-generated by deploy.sh
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=${DOMAIN}
DB_PATH=${APP_HOME}/data/verorun.db
PG_HOST=localhost
PG_PORT=5432
PG_DB=verorun
PG_USER=verorun
PG_PASSWORD=change-me-in-production
JWT_SECRET=${JWT_SECRET}
FLASK_SECRET_KEY=${FLASK_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
EASYKAI_MODE=main

# Phase 1 — Security hardening keys (2026-07-28)
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}

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
    for key in PLUGIN_LICENSE_SECRET CAPTCHA_SECRET_KEY DEV_ACCOUNTS_ENCRYPTION_KEY LICENSE_SERVER_SECRET; do
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
        local name=$1 port=$2 module=$3 extra_args="${4:-}"
        local file="${SERVICE_DIR}/${name}.service"

        cat > "${file}" << SVCEOF
[Unit]
Description=VeroRun ${name}
After=network.target postgresql.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_HOME}
EnvironmentFile=${env_file}
ExecStart=${VENV_DIR}/bin/gunicorn -w 2 -b 127.0.0.1:${port} ${extra_args} ${module}:app
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/${name}.log
StandardError=append:${LOG_DIR}/${name}.log

[Install]
WantedBy=multi-user.target
SVCEOF
        systemctl daemon-reload
        systemctl enable "${name}"
    }

    # 8081 — Main site
    write_one_service "verorun-main" 8081 "main" "--timeout 120 --log-level warning"

    # 8083 — Platform / Auth
    write_one_service "verorun-auth" 8083 "auth_center" "--timeout 120 --log-level warning"

    # 8084 — Admin
    write_one_service "verorun-admin" 8084 "admin" "--timeout 120 --max-requests=1000 --graceful-timeout=30 --log-level warning"
}

restart_services() {
    local services=("verorun-admin" "verorun-auth" "verorun-main")
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
}

# ==========================================================================
# Nginx
# ==========================================================================
write_nginx_config() {
    local nginx_conf="/etc/nginx/sites-available/verorun.conf"
    local nginx_enabled="/etc/nginx/sites-enabled/verorun.conf"

    if [ -f "${nginx_enabled}" ]; then
        echo -e "${WARN} Nginx config already exists, skipping"
        return
    fi

    cat > "${nginx_conf}" << NGXEOF
# VeroRun Nginx — auto-generated by deploy.sh

server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN} platform.${DOMAIN} agent.${DOMAIN};

    # ── Main site ───────────────────────────────
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    # ── Admin ─────────────────────────────────
    location /admin/ {
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }

    # ── Auth / Platform ───────────────────────
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

    # ── Platform subdomain ─────────────────────
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

    # ── Agent subdomain ──────────────────────────
    server {
        listen 80;
        server_name agent.${DOMAIN};

        location / {
            proxy_pass http://127.0.0.1:8084;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
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
            echo -e "  ${OK} ${name} (:${port}) → HTTP ${code}"
        else
            echo -e "  ${FAIL} ${name} (:${port}) → no response"
            all_ok=false
        fi
    }

    check_port 8081 "verorun-main"
    check_port 8083 "verorun-auth"
    check_port 8084 "verorun-admin"

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
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Main site:  https://${DOMAIN}                                 ║"
    echo "  ║  Platform:   https://platform.${DOMAIN}                        ║"
    echo "  ║  Admin:      https://agent.${DOMAIN}/admin/                    ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Useful commands:                                            ║"
    echo "  ║    systemctl status verorun-{main,auth,admin}                ║"
    echo "  ║    journalctl -u verorun-admin -f                            ║"
    echo "  ║    bash deploy/deploy.sh update                              ║"
    echo "  ║    bash deploy/deploy.sh rollback                            ║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ==========================================================================
# Main entry
# ==========================================================================

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash deploy.sh [update|restart|health|rollback]"
    exit 1
fi

detect_mode "${1:-}"
detect_domain "${2:-}"

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
    *)
        echo "Usage: sudo bash deploy.sh [install|update|restart|health|rollback]"
        exit 1
        ;;
esac
