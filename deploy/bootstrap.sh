#!/bin/bash
# ==========================================================================
# VeroRun / easykai.cn — Bare-metal deploy script (v1.0)
# ==========================================================================
# Target: Ubuntu 22.04 / 24.04 fresh VPS (Google Cloud, Alibaba Cloud, Tencent Cloud, etc.)
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/bootstrap.sh | sudo bash
#
#   Parameters:
#     $1 Domain      (default: easykai.cn)
#     $2 Install path (default: /var/www/verorun)
#     $3 Git repo     (default: https://github.com/fanjumin/VeroRunSystem.git)
#     $4 Git branch   (default: master)
#
#   Examples:
#     sudo bash bootstrap.sh
#     sudo bash bootstrap.sh mysite.com
#     sudo bash bootstrap.sh mysite.com /opt/myapp
# ==========================================================================

set -euo pipefail

# ── Parameters ─────────────────────────────────────────────────────────
DOMAIN="${1:-easykai.cn}"
APP_ROOT="${2:-/var/www/verorun}"
GIT_REPO="${3:-https://github.com/fanjumin/VeroRunSystem.git}"
GIT_BRANCH="${4:-master}"

# ── Colors ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; }
info() { echo -e "${BLUE}[i]${NC} $*"; }

# ── Path constants ─────────────────────────────────────────────────────
SYS_USER="www-data"
VENV_DIR="${APP_ROOT}/venv"

# ==========================================================================
# Phase 0: Pre-checks
# ==========================================================================
banner() {
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║       VeroRun Bare-metal Deploy Script  v1.0           ║"
    echo "  ║       Domain: ${DOMAIN}                                   ║"
    echo "  ║       Path:   ${APP_ROOT}                                  ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo ""
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "Please run with sudo: sudo bash bootstrap.sh"
        exit 1
    fi
    log "Root privileges confirmed"
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        err "Cannot detect OS — requires Ubuntu 22.04+"
        exit 1
    fi
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        warn "Detected $ID, script is designed for Ubuntu — may not be compatible"
        read -p "Continue? (y/N): " yn
        [ "$yn" != "y" ] && exit 1
    fi
    log "OS: $NAME $VERSION_ID"
}

# ==========================================================================
# Phase 1: System environment setup
# ==========================================================================
install_system_deps() {
    log "Updating apt sources..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq

    log "Installing system dependencies (python3, nginx, redis, certbot, git)..."
    apt-get install -y -qq \
        python3 python3-venv python3-pip python3-dev \
        nginx redis-server \
        certbot python3-certbot-nginx \
        git curl wget \
        build-essential libssl-dev \
        > /dev/null 2>&1

    log "System dependencies installed"
}

install_nodejs() {
    if command -v node &>/dev/null; then
        NODE_VER=$(node -v)
        log "Node.js already installed: $NODE_VER"
    else
        log "Installing Node.js 20.x..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
        apt-get install -y -qq nodejs > /dev/null 2>&1
        log "Node.js $(node -v) installed"
    fi
}

install_pm2() {
    if command -v pm2 &>/dev/null; then
        log "PM2 already installed: $(pm2 -v)"
    else
        log "Installing PM2..."
        npm install -g pm2 > /dev/null 2>&1
        log "PM2 $(pm2 -v) installed"
    fi
}

create_system_user() {
    # www-data is Ubuntu's built-in web service user, no need to create
    if id "$SYS_USER" &>/dev/null; then
        log "User $SYS_USER already exists (Ubuntu built-in)"
    else
        log "Creating user $SYS_USER ..."
        useradd -r -s /usr/sbin/nologin "$SYS_USER"
        log "User $SYS_USER created"
    fi

    mkdir -p "$APP_ROOT"
}

# ==========================================================================
# Phase 2: Code deployment
# ==========================================================================
clone_repo() {
    if [ -d "${APP_ROOT}/.git" ]; then
        log "Repository already exists, running git pull..."
        cd "$APP_ROOT"
        git fetch origin "$GIT_BRANCH"
        git reset --hard "origin/$GIT_BRANCH"
        log "Code updated to latest"
    else
        rm -rf "$APP_ROOT"
        log "Cloning repository $GIT_REPO (branch: $GIT_BRANCH)..."
        git clone -b "$GIT_BRANCH" "$GIT_REPO" "$APP_ROOT"
        log "Repository cloned"
    fi
}

setup_python_venv() {
    log "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"

    log "Installing Python dependencies (may take a few minutes)..."
    "${VENV_DIR}/bin/pip" install --upgrade pip > /dev/null 2>&1
    "${VENV_DIR}/bin/pip" install -r "${APP_ROOT}/requirements.txt" > /dev/null 2>&1
    log "Python dependencies installed"
}

generate_env() {
    if [ -f "${APP_ROOT}/.env" ]; then
        log ".env already exists, keeping existing config"
        return
    fi

    log "Generating .env config..."
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    PLUGIN_LICENSE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    CAPTCHA_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    DEV_ACCOUNTS_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    LICENSE_SERVER_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > "${APP_ROOT}/.env" << EOF
# VeroRun production config — auto-generated by bootstrap.sh
# Replace API keys with real values after deployment
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=${DOMAIN}
DB_PATH=data/easykai.db
JWT_SECRET=${JWT_SECRET}
FLASK_SECRET_KEY=${FLASK_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
EASYKAI_MODE=main
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DB=verorun
PG_USER=easykai
PG_PASSWORD=
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}
DASHSCOPE_TEXT_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here
EOF
    log ".env generated (JWT/Flask keys randomized, API keys need to be configured)"
}

create_data_dir() {
    log "Creating data directories..."
    mkdir -p "${APP_ROOT}/data/logs"
    # Create empty SQLite database directory, app creates tables on startup
    touch "${APP_ROOT}/data/.gitkeep"
}

setup_permissions() {
    log "Setting file permissions..."
    chown -R "${SYS_USER}:${SYS_USER}" "$APP_ROOT"
    chmod 755 "$APP_ROOT"
    chmod 600 "${APP_ROOT}/.env"
}

# ==========================================================================
# Phase 3: Nginx configuration
# ==========================================================================
write_nginx_config() {
    log "Writing Nginx configuration..."

    cat > /etc/nginx/sites-available/nginx_configure.conf << 'NGINX_EOF'
# ========================================================
# VeroRun — Unified Nginx Configuration
# Auto-generated by bootstrap.sh
# ========================================================
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# ── www / root domain ────────────────────────────────────
server {
    listen 80;
    server_name __DOMAIN__ www.__DOMAIN__;

    location ^~ /.well-known/acme-challenge/ {
        root __APP_ROOT__;
        try_files $uri =404;
    }

    location /subscribe {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location ^~ /auth/oauth/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location ^~ /auth/ {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location ^~ /user/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location ^~ /admin/static/ {
        root __APP_ROOT__;
        expires 30d;
        add_header Cache-Control "public, immutable, no-transform";
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 30s;
        proxy_send_timeout 300s;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable, no-transform";
        access_log off;
    }
}

# ── platform subdomain ──────────────────────────────────
server {
    listen 80;
    server_name platform.__DOMAIN__;

    location / {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }
}

# ── agent subdomain ─────────────────────────────────────
server {
    listen 80;
    server_name agent.__DOMAIN__;
    client_max_body_size 50M;

    location = / { return 302 /admin/login; }

    location ^~ /admin/static/ {
        root __APP_ROOT__;
        expires 30d;
        add_header Cache-Control "public, immutable, no-transform";
        access_log off;
    }

    location ^~ /api/v1/knowledge/ {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
    }

    location /admin/automation/ {
        proxy_pass http://127.0.0.1:8084;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
    }

    location / {
        proxy_pass http://127.0.0.1:8084;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }
}
NGINX_EOF

    # Replace placeholders
    sed -i "s|__DOMAIN__|${DOMAIN}|g" /etc/nginx/sites-available/nginx_configure.conf
    sed -i "s|__APP_ROOT__|${APP_ROOT}|g" /etc/nginx/sites-available/nginx_configure.conf

    # Enable site
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/nginx_configure.conf /etc/nginx/sites-enabled/nginx_configure.conf

    log "Nginx configuration written and enabled"
}

test_nginx() {
    log "Validating Nginx configuration..."
    if nginx -t 2>&1; then
        log "Nginx configuration syntax is correct"
    else
        err "Nginx configuration has errors — check /etc/nginx/sites-available/nginx_configure.conf"
        exit 1
    fi
}

setup_ssl() {
    log "Attempting SSL certificate issuance..."
    info "Ensure domain ${DOMAIN} *.${DOMAIN} resolves to this server's public IP"

    # Ensure nginx is running (HTTP mode required by certbot)
    systemctl restart nginx

    # Issue certificate (non-interactive mode)
    if certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" -d "platform.${DOMAIN}" -d "agent.${DOMAIN}" \
        --non-interactive --agree-tos --email "admin@${DOMAIN}" --redirect 2>&1; then
        log "SSL certificate issued successfully"
        # certbot automatically updates nginx config with SSL
    else
        warn "SSL certificate issuance failed (domain may not resolve or port 80 is unreachable)"
        warn "Currently running in HTTP mode only — run manually later: certbot --nginx"
    fi

    systemctl restart nginx
}

# ==========================================================================
# Phase 4: PM2 process management
# ==========================================================================
write_pm2_config() {
    log "Writing PM2 configuration..."

    cat > "${APP_ROOT}/ecosystem.config.js" << PM2_EOF
// VeroRun PM2 process config — auto-generated by bootstrap.sh
module.exports = {
  apps: [
    // ─── Main site 8081 (auth-center) ───
    {
      name: 'easykai-main',
      script: '${VENV_DIR}/bin/python3',
      args: '-B run_auth_wsgi.py -w 2 -b 0.0.0.0:8081 --log-level warning',
      cwd: '${APP_ROOT}',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      env: { PYTHONUNBUFFERED: '1' }
    },
    // ─── Platform 8083 ───
    {
      name: 'easykai-platform',
      script: '${VENV_DIR}/bin/python3',
      args: '-B run_gunicorn.py -w 2 -b 127.0.0.1:8083 --timeout 120 --access-logfile /tmp/gunicorn_8083_access.log --error-logfile /tmp/gunicorn_8083_error.log app:app',
      cwd: '${APP_ROOT}',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      env: { PYTHONUNBUFFERED: '1' }
    },
    // ─── Admin 8084 ───
    {
      name: 'easykai-admin',
      script: '${VENV_DIR}/bin/python3',
      args: 'admin/run_gunicorn.py -w 2 --max-requests=1000 -b 0.0.0.0:8084 app:app --timeout 120 --graceful-timeout 30 --log-level warning --access-logfile - --error-logfile -',
      cwd: '${APP_ROOT}',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      env: { PYTHONUNBUFFERED: '1' }
    },
    // ─── Health Guardian (watchdog) ───
    {
      name: 'easykai-health',
      script: '${VENV_DIR}/bin/python3',
      args: 'health_guardian.py',
      cwd: '${APP_ROOT}',
      autorestart: true,
      max_restarts: 5,
      restart_delay: 5000,
      env: { PYTHONUNBUFFERED: '1' }
    }
  ]
};
PM2_EOF

    log "PM2 configuration written to ${APP_ROOT}/ecosystem.config.js"
}

setup_pm2_systemd() {
    log "Configuring PM2 systemd auto-start..."

    # PM2_HOME goes under the system user's home directory
    PM2_HOME="/home/${SYS_USER}/.pm2"

    # Create systemd service
    cat > /etc/systemd/system/pm2-easykai.service << SYSTEMD_EOF
[Unit]
Description=PM2 process manager (easykai)
Documentation=https://pm2.keymetrics.io/
After=network.target

[Service]
Type=forking
User=${SYS_USER}
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PM2_HOME=${PM2_HOME}
PIDFile=${PM2_HOME}/pm2.pid
Restart=on-failure
RestartSec=5

ExecStart=/usr/bin/pm2 resurrect
ExecReload=/usr/bin/pm2 reload all
ExecStop=/usr/bin/pm2 kill

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

    systemctl daemon-reload
    systemctl enable pm2-easykai
    log "PM2 systemd service configured"
}

start_services() {
    log "Starting all services..."

    # Kill any lingering processes
    pkill -f "run_auth_wsgi.py" 2>/dev/null || true
    pkill -f "run_gunicorn.py" 2>/dev/null || true
    pkill -f "health_guardian.py" 2>/dev/null || true
    sleep 2

    # Ensure PM2_HOME directory exists with correct permissions
    PM2_HOME="/home/${SYS_USER}/.pm2"
    mkdir -p "$PM2_HOME"
    chown -R "${SYS_USER}:${SYS_USER}" "$PM2_HOME"

    # Start PM2 as system user
    sudo -u "$SYS_USER" env PM2_HOME="$PM2_HOME" pm2 start "${APP_ROOT}/ecosystem.config.js"

    # Save PM2 process list (for resurrect)
    sudo -u "$SYS_USER" env PM2_HOME="$PM2_HOME" pm2 save

    log "All services started via PM2"
}

# ==========================================================================
# Phase 5: Verification
# ==========================================================================
verify_services() {
    log "Waiting for services to be ready..."
    sleep 5

    local failed=0

    check_port() {
        local port=$1 name=$2
        if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://127.0.0.1:${port}/" 2>/dev/null | grep -qE '^(2|3)'; then
            log "  ${name} (:${port}) — OK"
        else
            err "  ${name} (:${port}) — no response"
            failed=1
        fi
    }

    echo ""
    info "Smoke test..."
    check_port 8081 "easykai-main"
    check_port 8083 "easykai-platform"
    check_port 8084 "easykai-admin"

    if [ "$failed" -eq 0 ]; then
        echo ""
        log "All services started successfully!"
    else
        echo ""
        warn "Some services are not ready — run pm2 logs to check"
    fi
}

# ==========================================================================
# Deployment summary
# ==========================================================================
print_summary() {
    local PUBLIC_IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "unknown")

    echo ""
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║              Deployment Complete!                             ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Domain:    ${DOMAIN}                                          $(printf '%*s' $((48 - ${#DOMAIN})) '')║"
    echo "  ║  IP:        ${PUBLIC_IP}                                       $(printf '%*s' $((48 - ${#PUBLIC_IP})) '')║"
    echo "  ║                                                              ║"
    echo "  ║  Service ports:                                              ║"
    echo "  ║    Main (8081):    https://${DOMAIN}                          $(printf '%*s' $((35 - ${#DOMAIN})) '')║"
    echo "  ║    Platform (8083): https://platform.${DOMAIN}                $(printf '%*s' $((28 - ${#DOMAIN})) '')║"
    echo "  ║    Admin (8084):    https://agent.${DOMAIN}                   $(printf '%*s' $((28 - ${#DOMAIN})) '')║"
    echo "  ║                                                              ║"
    echo "  ║  Useful commands:                                            ║"
    echo "  ║    pm2 status          — check process status                ║"
    echo "  ║    pm2 logs            — view logs                           ║"
    echo "  ║    pm2 restart all     — restart all services                ║"
    echo "  ║                                                              ║"
    echo "  ║  Next steps:                                                 ║"
    echo "  ║    1. Edit ${APP_ROOT}/.env to set real API keys              ║"
    echo "  ║    2. If SSL failed, run manually: certbot --nginx           ║"
    echo "  ║    3. Visit https://agent.${DOMAIN}/admin/ for admin panel   $(printf '%*s' $((28 - ${#DOMAIN})) '')║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ==========================================================================
# Main flow
# ==========================================================================
main() {
    banner
    check_root
    check_os

    echo ""
    info "Deploying to: ${APP_ROOT}"
    info "Git repo:    ${GIT_REPO}"
    info "Branch:      ${GIT_BRANCH}"
    echo ""

    # Phase 1
    echo "━━━ Phase 1/5: System environment ━━━"
    install_system_deps
    install_nodejs
    install_pm2
    create_system_user

    # Phase 2
    echo "━━━ Phase 2/5: Code deployment ━━━"
    clone_repo
    setup_python_venv
    generate_env
    create_data_dir
    setup_permissions

    # Phase 3
    echo "━━━ Phase 3/5: Nginx configuration ━━━"
    write_nginx_config
    test_nginx
    setup_ssl

    # Phase 4
    echo "━━━ Phase 4/5: PM2 process management ━━━"
    write_pm2_config
    setup_pm2_systemd
    start_services

    # Phase 5
    echo "━━━ Phase 5/5: Verification ━━━"
    verify_services

    print_summary
}

main "$@"