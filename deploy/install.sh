#!/bin/bash
# ==========================================================================
# VeroRun — One-command deploy script (v2.1)
# ==========================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo bash   # fresh install (public base)
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

# ── Colors ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; WARN="${YELLOW}[WARN]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"

# ── Git mirror: DISABLED — ghproxy.com unstable, direct GitHub preferred ──

# ── CN Network Auto-Adaptation (v1.0) ────────────────────────────────
# 中国网络环境优化：apt 镜像切换 / pip 多源竞速 / git 超时保护
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

step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }
fail_step() { echo -e "${FAIL} $1"; }

# ── Git SSH auth setup ───────────────────────────────────────────────

ensure_git_auth() {
    # Skip SSH setup if using HTTPS repo (e.g. public base mirror)
    if echo "${GIT_REPO}" | grep -q '^https://'; then
        return 0
    fi

    local ssh_key="/root/.ssh/id_ed25519"

    # Generate SSH key for root if not exists
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

    # Ensure github.com in known_hosts
    if [ ! -f /root/.ssh/known_hosts ] || ! grep -q '^github\.com' /root/.ssh/known_hosts 2>/dev/null; then
        echo -e "${INFO} Adding github.com to known_hosts..."
        ssh-keyscan github.com >> /root/.ssh/known_hosts 2>/dev/null || true
    fi

    # Switch existing HTTPS remote to SSH
    if [ -d "${APP_HOME}/.git" ]; then
        local current_url
        current_url=$(git -C "${APP_HOME}" remote get-url origin 2>/dev/null || echo "")
        if echo "${current_url}" | grep -q '^https://'; then
            echo -e "${INFO} Switching git remote to SSH..."
            git -C "${APP_HOME}" remote set-url origin "${GIT_REPO}"
            done_step "Git remote switched to SSH"
        fi
    fi
}

# ── Interactive directory conflict resolution ────────────────────────
# 文档 verorun-deploy-guide.html §6.3：目录冲突时三选一（备份/删除/中止）
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
        git fetch origin "${GIT_BRANCH}"
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
# Seed initial data
# ==========================================================================
# ── Admin credentials temp file ──────────────────────────────────────
VR_ADMIN_CREDS_FILE="/root/.verorun-creds"

do_seed() {
    step "Seed initial data"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        echo -e "${FAIL} Python venv not found at ${VENV_DIR}"
        echo -e "${INFO} Run 'install.sh install' first"
        exit 1
    fi

    # Seed is grouped under the same manual gate as DB migration:
    # pass --approve-migrate to inject initial data
    if [ "${APPROVE_MIGRATE:-0}" != "1" ]; then
        echo -e "${WARN} Skipped seed data (pass --approve-migrate to inject admin/plans/products)"
        return 0
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

    printf 'VR_ADMIN_USERNAME="%s"\nVR_ADMIN_PASSWORD="%s"\n' "${_user}" "${_pass}" > "${VR_ADMIN_CREDS_FILE}"
    chmod 600 "${VR_ADMIN_CREDS_FILE}"
    # 审计 C2 加固：脚本异常退出时清理凭据文件（prompt 仅在 install 模式调用，无 EXIT trap 冲突）
    trap 'rm -f "${VR_ADMIN_CREDS_FILE}"' EXIT
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
# Rollback
# ==========================================================================
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

assert_debug_disabled() {
    # Production gate: refuse to continue if DEBUG is enabled in .env
    # Protects against developer mistakes causing performance/memory issues in prod
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

update_env() {
    local env_file="${APP_HOME}/.env"
    if [ ! -f "${env_file}" ]; then
        generate_env
        return
    fi

    # Fill missing Phase 1 keys
    local missing=()
    for key in PLUGIN_LICENSE_SECRET CAPTCHA_SECRET_KEY DEV_ACCOUNTS_ENCRYPTION_KEY LICENSE_SERVER_SECRET PROBE_SECRET INTERNAL_SERVICE_TOKEN; do
        if ! grep -q "^${key}=" "${env_file}" 2>/dev/null; then
            local val
            val=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            echo "${key}=${val}" >> "${env_file}"
            missing+=("${key}")
        fi
    done

    # Fill missing DEBUG keys with production-safe defaults
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

# ==========================================================================
# systemd services
# ==========================================================================
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

        # Build optional RuntimeDirectory block (only emitted when runtime_dir is set)
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
# 启动健康检查：/health 不返回 200 → systemd 认为启动失败（最多等待 TimeoutStartSec）
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
    # Used by admin/app.py for update_status.json + update.log (no more root-permission 500s).
    write_one_service "verorun-admin" 8084 "admin.app" "--timeout 300 --max-requests=1000 --graceful-timeout=30 --log-level warning --config admin/gunicorn_config.py" "admin/run_gunicorn.py" "verorun"

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
        UPDATE_FAILED=1
    fi
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

# Parse flags: --region cn / --region=cn / --approve-migrate
# 审计 H4 修复：原 --region) 分支为空操作，--region cn 空格分隔形式的值被丢弃
while [ $# -gt 0 ]; do
    case "${1}" in
        --region=*) REGION="${1#*=}" ;;
        --region) shift; [ $# -gt 0 ] && REGION="${1}" ;;
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
