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
# ── Sparse-checkout 白名单：仅这些目录在服务器检出（cone 模式） ──
: "${SPARSE_DIRS:=admin auth-center main_site health_service veroguard plugin_manager agent_matrix orchestrator i18n captcha-service shared providers themes static deploy}"

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
    _tmp_common="$(mktemp)"
    _ok=0
    if command -v curl >/dev/null 2>&1; then
        if curl -sSL --connect-timeout 15 "${_COMMON_REMOTE}" -o "${_tmp_common}"; then _ok=1; fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --timeout=15 -O "${_tmp_common}" "${_COMMON_REMOTE}"; then _ok=1; fi
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
    if [ "${SKIP_DEPS:-0}" = "1" ]; then
        echo -e "${WARN} --skip-deps: skipping system dependency installation"
    else
        _ensure_apt_mirror
        apt-get update
        apt-get install -y python3 python3-venv python3-pip python3-dev \
            nginx git curl wget build-essential libpq-dev libssl-dev
    fi
    done_step "System dependencies installed"

    # Generate PG password early so PostgreSQL role and .env match
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

    # Ensure role exists and password matches .env
    # 审计 C1 加固：密码经临时 SQL 文件（600 权限）传入 psql -f，避免出现在进程命令行
    _sql_tmp=$(mktemp)
    chmod 600 "${_sql_tmp}"
    if sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='verorun'" 2>/dev/null | grep -qE '^\s*1\s*$'; then
        printf "ALTER ROLE verorun WITH LOGIN PASSWORD '%s';\n" "${PG_PASSWORD}" > "${_sql_tmp}"
    else
        printf "CREATE ROLE verorun WITH LOGIN PASSWORD '%s';\n" "${PG_PASSWORD}" > "${_sql_tmp}"
    fi
    sudo -u postgres psql -q -f "${_sql_tmp}" 2>/dev/null || true
    rm -f "${_sql_tmp}"
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='verorun'" | grep -qE '^\s*1\s*$' 2>/dev/null || \
        sudo -u postgres psql -c "CREATE DATABASE verorun OWNER verorun" 2>/dev/null
    # 铁律：安装脚本只允许创建系统库，插件数据库一律不建
    done_step "PostgreSQL is running"

    step "Create directories"
    mkdir -p "${APP_HOME}" "${APP_HOME}/data" "${LOG_DIR}"
    mkdir -p "${APP_HOME}/.cache/llm" \
             "${APP_HOME}/.cache/sessions" \
             "${APP_HOME}/.cache/agents"
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${LOG_DIR}" 2>/dev/null || true
    done_step "Directories ready"

    ensure_git_auth

    step "Pull code"
    # 审计 H3 修复：目录冲突时交互式三选一（备份/删除/中止），不再直接 rm -rf
    resolve_directory_conflict "${APP_HOME}"
    if [ -d "${APP_HOME}/.git" ]; then
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        # 审计 F-2：抑制 git 交互式凭据提示 + 超时保护，避免 origin 指向镜像时无限卡死
        export GIT_TERMINAL_PROMPT=0
        if ! timeout 60 git fetch origin "${GIT_BRANCH}" 2>&1; then
            echo -e "${FAIL} Git fetch failed or timed out (60s) — aborting"
            echo -e "${INFO} Check origin remote: git -C ${APP_HOME} remote -v"
            echo -e "${INFO} If it points to a mirror (ghfast.top/ghproxy), reset it:"
            echo -e "${INFO}   git -C ${APP_HOME} remote set-url origin ${GIT_REPO}"
            exit 1
        fi
        git reset --hard "origin/${GIT_BRANCH}"
    else
        _clone_with_timeout "${GIT_REPO}" "${APP_HOME}" "${GIT_BRANCH}"
    fi
    # 应用 sparse-checkout 白名单（幂等；拉取后立即收窄工作区，仅保留运行时目录）
    if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
        git -C "${APP_HOME}" sparse-checkout init --cone 2>/dev/null || true
        git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS}
    fi
    # 本地/无域名部署脚本不进生产工作区：install.sh 不部署也不更新 install-local.sh
    rm -f "${APP_HOME}/deploy/install-local.sh"
    # Clean stale __pycache__ before chown (avoids race-condition failures)
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

    prompt_domain

    step "Generate .env"
    generate_env force
    done_step ".env generated"

    # Production gate: refuse to continue if DEBUG got enabled in .env
    assert_debug_disabled

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
    if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
        sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; cd ${APP_HOME} && PYTHONPATH=${APP_HOME}/auth-center ${VENV_DIR}/bin/python -c 'from models.database import init_db; init_db()'"
        done_step "Database migrated"
    else
        echo -e "${WARN} Skipped database migration (pass --approve-migrate to apply schema changes)"
        echo -e "${INFO} Services may fail to start if code references columns not yet in the DB"
    fi

    step "Seed data"
    do_seed
    done_step "Seed data injected"

    print_summary
}

# ==========================================================================
# Incremental update
# ==========================================================================
do_update() {
    # ── Trap: write failure status on any early exit ──
    # /run/verorun/ is tmpfs managed by systemd RuntimeDirectory (verorun-admin.service).
    # Owned by APP_USER, no root-permission conflicts. Cleared on reboot (intended).
    local _status_file="/run/verorun/update_status.json"
    mkdir -p /run/verorun 2>/dev/null || true
    chown "${APP_USER}:${APP_USER}" /run/verorun 2>/dev/null || true
    trap 'echo "{\"status\":\"failed\",\"progress\":100,\"message\":\"Update failed\",\"error\":\"Script exited unexpectedly\"}" > '"${_status_file}" EXIT

    # Self-update tracking: md5 of currently-running install.sh
    UPDATE_MD5=$(md5sum "${APP_HOME}/deploy/install.sh" 2>/dev/null | awk '{print $1}') || UPDATE_MD5=""

    # Read domain from existing .env
    DOMAIN=$(grep "^DEPLOY_DOMAIN=" "${APP_HOME}/.env" 2>/dev/null | cut -d= -f2) || true

    local before_commit
    before_commit=$(git -C "${APP_HOME}" log --oneline -1 2>/dev/null || echo "unknown")

    step "Backup current version"
    mkdir -p "${APP_HOME}/.rollback"
    cp "${APP_HOME}/.env" "${APP_HOME}/.rollback/.env.bak" 2>/dev/null || true
    echo "${before_commit}" > "${APP_HOME}/.rollback/before_commit"
    done_step "Environment backed up"

    step "Restore locally modified files"
    # 生产环境严禁手动修改 tracked 文件，自动恢复 working directory 的本地修改
    if [ -d "${APP_HOME}/.git" ]; then
        if ! git -C "${APP_HOME}" diff --quiet; then
            echo -e "${WARN} Local modifications detected, restoring to git version..."
            git -C "${APP_HOME}" diff --name-only -z | xargs -0 git -C "${APP_HOME}" checkout --
            done_step "Locally modified files restored"
        else
            done_step "No local modifications"
        fi
    else
        done_step "Skipped (no .git directory)"
    fi

    ensure_git_auth

    step "Pull latest code"
    if [ ! -d "${APP_HOME}/.git" ]; then
        echo -e "${WARN} .git missing — re-cloning repository"
        # 审计 H3 修复：复用交互式冲突处理，禁止直接 rm -rf
        resolve_directory_conflict "${APP_HOME}"
        _clone_with_timeout "${GIT_REPO}" "${APP_HOME}" "${GIT_BRANCH}"
    else
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        if ! git fetch origin "${GIT_BRANCH}" 2>&1; then
            echo -e "${FAIL} Git fetch failed. Check network connectivity to GitHub."
            echo -e "${FAIL} Update aborted."
            exit 1
        fi
        git merge "origin/${GIT_BRANCH}" --ff-only 2>/dev/null || {
            echo -e "${WARN} Fast-forward merge failed, falling back to reset"
            git reset --hard "origin/${GIT_BRANCH}" || {
                echo -e "${FAIL} Git reset failed."
                exit 1
            }
        }
    fi
    # 应用 sparse-checkout 白名单：老仓库立即移除 .github/CHANGELOG/docs 等非运行时文件
    if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
        git -C "${APP_HOME}" sparse-checkout init --cone 2>/dev/null || true
        git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS}
    fi
    # 本地/无域名部署脚本不进生产工作区：install.sh 不部署也不更新 install-local.sh
    rm -f "${APP_HOME}/deploy/install-local.sh"
    local after_commit
    after_commit=$(git log --oneline -1)
    done_step "Code updated: ${before_commit:0:7} -> ${after_commit:0:7}"

    # Self-update: if install.sh itself changed, re-run update with new version
    local script_md5
    script_md5=$(md5sum "${APP_HOME}/deploy/install.sh" | awk '{print $1}')
    if [ "${UPDATE_MD5}" != "${script_md5}" ]; then
        echo -e "${INFO} install.sh updated, re-running with new version..."
        exec sudo APP_USER="${APP_USER}" APP_HOME="${APP_HOME}" VENV_DIR="${VENV_DIR}" REGION="${REGION}" bash "${APP_HOME}/deploy/install.sh" update
        exit
    fi

    step "Update .env (fill missing keys)"
    update_env
    done_step ".env synced"

    # Production gate: refuse to continue if DEBUG got enabled in .env
    assert_debug_disabled

    step "Update Python dependencies"
    req_hash=$(md5sum "${APP_HOME}/requirements.txt" | awk '{print $1}')
    cached_hash=$(cat "${APP_HOME}/.requirements_hash" 2>/dev/null || echo "")
    if [ "${req_hash}" != "${cached_hash}" ]; then
        _pip_install -r "${APP_HOME}/requirements.txt"
        echo "${req_hash}" > "${APP_HOME}/.requirements_hash"
    else
        echo -e "${INFO} requirements.txt unchanged, skipping pip install"
    fi
    done_step "Dependencies updated"

    step "Update systemd services"
    chmod +x "${APP_HOME}/deploy/health_check.sh" 2>/dev/null || true
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
    # 验证数据库可连接（直接 psycopg2 连接，不依赖 plugins 包）
    if ! sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; ${VENV_DIR}/bin/python -c \"
import os, psycopg2
conn = psycopg2.connect(
    host=os.getenv('PG_HOST', 'localhost'),
    port=os.getenv('PG_PORT', '5432'),
    dbname=os.getenv('PG_DB', 'verorun'),
    user=os.getenv('PG_USER', 'verorun'),
    password=os.getenv('PG_PASSWORD', ''),
)
conn.close()
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

    # ── Write final update status for admin UI polling ──
    trap - EXIT  # Clear the failure trap before writing success
    local _status_file="/run/verorun/update_status.json"
    mkdir -p /run/verorun 2>/dev/null || true
    chown "${APP_USER}:${APP_USER}" /run/verorun 2>/dev/null || true
    if [ "${UPDATE_FAILED:-0}" -eq 0 ]; then
        echo '{"status":"success","progress":100,"message":"Update completed successfully","error":null}' > "${_status_file}"
    else
        echo '{"status":"failed","progress":100,"message":"Update completed with errors","error":"Some services are unhealthy"}' > "${_status_file}"
    fi
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
    INTERNAL_SERVICE_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > "${env_file}" << ENVEOF
# VeroRun production config — auto-generated by install.sh
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=${DOMAIN}
DEPLOY_PROTOCOL=https
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

# Production defaults: DEBUG must stay disabled (assert_debug_disabled enforces on install/update)
APP_DEBUG=false
FLASK_DEBUG=0

# v2.1.0 — 内部服务令牌
INTERNAL_SERVICE_TOKEN=${INTERNAL_SERVICE_TOKEN}

# Phase 1 — Security hardening keys (2026-07-28)
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}

# 部署默认不自动安装/启用插件（需在后台手动安装启用）
PLUGIN_AUTO_INSTALL=0

# VeroGuard — 守护进程加密通信密钥（官方端与客户端需一致）
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
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

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
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

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
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

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
# Summary
# ==========================================================================
print_summary() {
    local PUBLIC_IP
    PUBLIC_IP=$(curl -s --connect-timeout 5 --max-time 10 ifconfig.me 2>/dev/null || echo "unknown")

    echo ""
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║              Deployment Complete!                             ║"
    if [ -n "${DOMAIN}" ]; then
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Main site:  https://${DOMAIN}                                 ║"
    echo "  ║  Platform:   https://platform.${DOMAIN}                        ║"
    echo "  ║  Admin:      https://agent.${DOMAIN}/admin/                    ║"
    fi
    if [ "${APPROVE_MIGRATE:-0}" != "1" ]; then
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  WARNING: Admin account NOT created — admin panel inaccessible"
    echo "  ║  To fix: sudo bash deploy/install.sh seed                      ║"
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

# ── Main entry ──────────────────────────────────────────────────────────

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} Please run with sudo: sudo bash install.sh [install|update|restart|health|rollback|seed|configure-domain] [--region cn|global] [--skip-deps] [--approve-migrate]"
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
