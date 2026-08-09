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
    INTERNAL_SERVICE_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")

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

# v2.1.0 — 内部服务令牌
INTERNAL_SERVICE_TOKEN=${INTERNAL_SERVICE_TOKEN}

# Production defaults: DEBUG must stay disabled (assert_debug_disabled enforces on install/update)
APP_DEBUG=false
FLASK_DEBUG=0

# Phase 1 — Security hardening keys (2026-07-28)
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}

# Deployments do not auto-install/enable plugins by default (install manually in admin)
PLUGIN_AUTO_INSTALL=0

# VeroGuard — daemon encrypted communication key (official side and client must match)
PROBE_SECRET=${PROBE_SECRET}

# API Keys (intentionally empty — set real values before enabling AI features)
DASHSCOPE_TEXT_KEY=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=

# Region routing (VeroRun 0.43.0+)
VERORUN_REGION=${REGION}
ENVEOF

    chown "${APP_USER}:${APP_USER}" "${env_file}"
    chmod 600 "${env_file}"
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
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ── Admin panel ─────────────────────────
    location /admin/ {
        client_max_body_size 100M;
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
        _ensure_apt_mirror
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
    # 审计 H-3：显式验证角色与数据库是否创建成功，失败立即中止（不再被静默吞掉）
    if ! sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='verorun'" 2>/dev/null | grep -qE '^\s*1\s*$'; then
        echo -e "${FAIL} FATAL: PostgreSQL role 'verorun' not created. Check pg_hba.conf auth method (md5/scram requires password auth)."
        exit 1
    fi
    if ! sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='verorun'" 2>/dev/null | grep -qE '^\s*1\s*$'; then
        echo -e "${FAIL} FATAL: PostgreSQL database 'verorun' not created."
        exit 1
    fi
    # 铁律：安装脚本只允许创建系统库，插件数据库一律不建
    done_step "PostgreSQL is running"

    step "Create directories"
    mkdir -p "${APP_HOME}" "${APP_HOME}/data" "${LOG_DIR}"
    mkdir -p "${APP_HOME}/.cache/llm" "${APP_HOME}/.cache/sessions" "${APP_HOME}/.cache/agents"
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" 2>/dev/null || true
    chown -R "${APP_USER}:${APP_USER}" "${LOG_DIR}" 2>/dev/null || true
    done_step "Directories ready"

    ensure_git_auth

    step "Pull code"
    # 交互式解决目录冲突：备份/删除/中止 三选一
    resolve_directory_conflict "${APP_HOME}"
    if [ -d "${APP_HOME}/.git" ]; then
        # 已有 git 仓库 → 拉取最新代码
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        # 审计 F-2：修复残留镜像 remote → 重置为 GIT_REPO 后再 fetch
        git remote set-url origin "${GIT_REPO}"
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
        # 目录不存在或已被清理/备份 → 全新 clone
        _clone_with_timeout "${GIT_REPO}" "${APP_HOME}" "${GIT_BRANCH}"
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

    # 审计 NEW-H1：VeroGuard 完整性清单构建统一走 common.sh 函数
    build_veroguard_manifest

    # Production gate: refuse to continue if DEBUG got enabled in .env
    assert_debug_disabled

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
    if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
        sudo -u "${APP_USER}" bash -c "set -a; source ${APP_HOME}/.env; cd ${APP_HOME} && PYTHONPATH=${APP_HOME}/auth-center ${VENV_DIR}/bin/python -c 'from models.database import init_db; init_db()'"
        done_step "Database migrated"
    else
        echo -e "${WARN} Skipped database migration (pass --approve-migrate to apply schema changes)"
        echo -e "${INFO} Services may fail to start if code references columns not yet in the DB"
    fi

    step "Seed data"
    # 审计 NEW-M1：凭据由 common.sh do_seed 统一生成并回显（此处不再用全局变量传递）
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
    echo "  ║    bash deploy/install-local.sh update                        ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  AI API keys are empty by default — set real values in:      ║"
    echo "  ║    ${APP_HOME}/.env  (DASHSCOPE_TEXT_KEY / OPENAI_API_KEY /   ║"
    echo "  ║    DEEPSEEK_API_KEY) before enabling AI features             ║"
    if [ "${APPROVE_MIGRATE:-0}" = "1" ]; then
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  Admin login: ${VR_ADMIN_USERNAME:-administrator} / ${VR_ADMIN_PASSWORD}"
    fi
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ── Incremental update ───────────────────────────────────────────────
do_update() {
    local _status_file="/run/verorun/update_status.json"
    mkdir -p /run/verorun 2>/dev/null || true
    chown "${APP_USER}:${APP_USER}" /run/verorun 2>/dev/null || true
    trap 'echo "{\"status\":\"failed\",\"progress\":100,\"message\":\"Update failed\",\"error\":\"Script exited unexpectedly\"}" > '"${_status_file}" EXIT

    UPDATE_MD5=$(md5sum "${APP_HOME}/deploy/install-local.sh" 2>/dev/null | awk '{print $1}') || UPDATE_MD5=""

    local before_commit
    before_commit=$(git -C "${APP_HOME}" log --oneline -1 2>/dev/null || echo "unknown")

    step "Backup current version"
    mkdir -p "${APP_HOME}/.rollback"
    cp "${APP_HOME}/.env" "${APP_HOME}/.rollback/.env.bak" 2>/dev/null || true
    echo "${before_commit}" > "${APP_HOME}/.rollback/before_commit"
    done_step "Environment backed up"

    step "Restore locally modified files"
    # 审计 C-3：默认拒绝覆盖本地修改（防止销毁用户定制/热修复）；--force 时先备份 diff 再恢复
    if [ -d "${APP_HOME}/.git" ]; then
        if ! git -C "${APP_HOME}" diff --quiet; then
            if [ "${FORCE_UPDATE:-0}" != "1" ]; then
                echo -e "${FAIL} Local modifications detected — refusing to overwrite them."
                echo -e "${INFO} To review:  git -C ${APP_HOME} diff"
                echo -e "${INFO} To backup:  git -C ${APP_HOME} diff > ${APP_HOME}/.rollback/local-patch-$(date +%s).diff"
                echo -e "${INFO} Re-run with '--force' to auto-restore (a backup diff is saved first)."
                exit 1
            fi
            mkdir -p "${APP_HOME}/.rollback"
            git -C "${APP_HOME}" diff > "${APP_HOME}/.rollback/local-patch-$(date +%s).diff"
            echo -e "${WARN} Local modifications detected (backed up to .rollback/local-patch-*.diff), restoring to git version..."
            git -C "${APP_HOME}" diff --name-only -z | xargs -0 git -C "${APP_HOME}" checkout --
            done_step "Locally modified files restored (diff saved)"
        else
            done_step "No local modifications"
        fi
    else
        done_step "Skipped (no .git directory)"
    fi

    ensure_git_auth

    step "Pull latest code"
    if [ ! -d "${APP_HOME}/.git" ]; then
        echo -e "${FAIL} .git missing — cannot update. Re-install with install-local.sh."
        exit 1
    else
        git config --global --add safe.directory "${APP_HOME}" 2>/dev/null || true
        cd "${APP_HOME}"
        git remote set-url origin "${GIT_REPO}"
        if ! git fetch origin "${GIT_BRANCH}" 2>&1; then
            echo -e "${FAIL} Git fetch failed. Check network connectivity."
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
    if ! git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS} 2>/dev/null; then
        git -C "${APP_HOME}" sparse-checkout init --cone 2>/dev/null || true
        git -C "${APP_HOME}" sparse-checkout set ${SPARSE_DIRS}
    fi
    local after_commit
    after_commit=$(git log --oneline -1)
    done_step "Code updated: ${before_commit:0:7} -> ${after_commit:0:7}"

    local script_md5
    script_md5=$(md5sum "${APP_HOME}/deploy/install-local.sh" | awk '{print $1}')
    if [ "${UPDATE_MD5}" != "${script_md5}" ]; then
        echo -e "${INFO} install-local.sh updated, re-running with new version..."
        exec sudo APP_USER="${APP_USER}" APP_HOME="${APP_HOME}" VENV_DIR="${VENV_DIR}" REGION="${REGION}" FORCE_UPDATE="${FORCE_UPDATE:-0}" bash "${APP_HOME}/deploy/install-local.sh" update
        exit
    fi

    step "Update .env (fill missing keys)"
    update_env
    done_step ".env synced"

    # 审计 R3-M2：代码更新后重建 VeroGuard 完整性清单，避免基准过时触发误报
    build_veroguard_manifest

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

    step "Update sudoers"
    write_sudoers
    done_step "Sudoers updated"

    step "Update Nginx config"
    write_nginx_config
    nginx -t && systemctl restart nginx
    done_step "Nginx config updated"

    step "Pre-flight check"
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

    trap - EXIT
    local _status_file="/run/verorun/update_status.json"
    mkdir -p /run/verorun 2>/dev/null || true
    chown "${APP_USER}:${APP_USER}" /run/verorun 2>/dev/null || true
    if [ "${UPDATE_FAILED:-0}" -eq 0 ]; then
        echo '{"status":"success","progress":100,"message":"Update completed successfully","error":null}' > "${_status_file}"
    else
        echo '{"status":"failed","progress":100,"message":"Update completed with errors","error":"Some services are unhealthy"}' > "${_status_file}"
    fi
}

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
