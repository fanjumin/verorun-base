#!/bin/bash
# ==========================================================================
# VeroRun — 一键部署脚本 (v2.0)
# ==========================================================================
# 支持两种模式:
#   1. 全新安装: curl -sSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/deploy.sh | sudo bash
#   2. 增量更新: sudo bash deploy/deploy.sh update
#
# 用法:
#   sudo bash deploy.sh                # 全新安装
#   sudo bash deploy.sh update         # 增量更新（拉代码→装依赖→重启服务）
#   sudo bash deploy.sh restart        # 仅重启服务
#   sudo bash deploy.sh health         # 健康检查
#   sudo bash deploy.sh rollback       # 回滚到上一个版本
# ==========================================================================
set -euo pipefail

# ── 默认配置 ──────────────────────────────────────────────────────────
: "${DEPLOY_MODE:=update}"              # install | update | restart | health | rollback
: "${GIT_REPO:=https://github.com/fanjumin/VeroRunSystem.git}"
: "${GIT_BRANCH:=master}"
: "${APP_USER:=easykai}"
: "${APP_HOME:=/home/${APP_USER}/easykai-workspace/easykai.cn}"
: "${VENV_DIR:=${APP_HOME}/venv}"
: "${LOG_DIR:=/var/log/easykai}"
: "${SERVICE_DIR:=/etc/systemd/system}"
: "${DOMAIN:=easykai.cn}"

# ── 颜色 ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
OK="${GREEN}[OK]${NC}"; WARN="${YELLOW}[WARN]${NC}"; FAIL="${RED}[FAIL]${NC}"; INFO="${BLUE}[i]${NC}"

step() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }
done_step() { echo -e "${OK} $1"; }
fail_step() { echo -e "${FAIL} $1"; }

# ── 检测模式 ──────────────────────────────────────────────────────────

detect_mode() {
    local mode="${1:-}"
    if [ -n "$mode" ]; then
        DEPLOY_MODE="$mode"
    elif [ -f "${APP_HOME}/.env" ]; then
        DEPLOY_MODE="update"
    else
        DEPLOY_MODE="install"
    fi
    echo -e "${INFO} 部署模式: ${DEPLOY_MODE}"
}

# ==========================================================================
# 全新安装
# ==========================================================================
do_install() {
    step "系统依赖安装"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip python3-dev \
        nginx git curl wget build-essential libpq-dev libssl-dev
    done_step "系统依赖安装完成"

    step "PostgreSQL 安装"
    if ! systemctl is-active --quiet postgresql 2>/dev/null; then
        apt-get install -y -qq postgresql postgresql-client
        systemctl enable --now postgresql
    fi
    done_step "PostgreSQL 运行中"

    step "创建用户 & 目录"
    if ! id "${APP_USER}" &>/dev/null; then
        useradd -m -s /bin/bash "${APP_USER}"
    fi
    mkdir -p "${APP_HOME}" "${LOG_DIR}"
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" "${LOG_DIR}"
    done_step "用户 ${APP_USER} 就绪"

    step "拉取代码"
    if [ -d "${APP_HOME}/.git" ]; then
        cd "${APP_HOME}"
        git fetch origin "${GIT_BRANCH}"
        git reset --hard "origin/${GIT_BRANCH}"
    else
        rm -rf "${APP_HOME}"
        git clone -b "${GIT_BRANCH}" "${GIT_REPO}" "${APP_HOME}"
    fi
    chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}"
    done_step "代码拉取完成 ($(git -C "${APP_HOME}" log --oneline -1))"

    step "Python 虚拟环境"
    if [ ! -f "${VENV_DIR}/bin/python" ]; then
        sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
    fi
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip -q
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -r "${APP_HOME}/requirements.txt" -q
    done_step "Python 依赖安装完成"

    step "生成 .env"
    generate_env
    done_step ".env 已生成"

    step "systemd 服务"
    write_systemd_services
    done_step "systemd 服务已配置"

    step "Nginx"
    write_nginx_config
    nginx -t && systemctl reload nginx
    done_step "Nginx 配置完成"

    step "启动服务"
    restart_services
    done_step "服务已启动"

    print_summary
}

# ==========================================================================
# 增量更新
# ==========================================================================
do_update() {
    local before_commit
    before_commit=$(git -C "${APP_HOME}" log --oneline -1 2>/dev/null || echo "unknown")

    step "备份当前版本"
    mkdir -p "${APP_HOME}/.rollback"
    cp "${APP_HOME}/.env" "${APP_HOME}/.rollback/.env.bak" 2>/dev/null || true
    done_step "环境变量已备份"

    step "拉取最新代码"
    cd "${APP_HOME}"
    git fetch origin "${GIT_BRANCH}"
    git merge "origin/${GIT_BRANCH}" --ff-only 2>/dev/null || {
        echo -e "${WARN} 快进合并失败，执行 reset"
        git reset --hard "origin/${GIT_BRANCH}"
    }
    local after_commit
    after_commit=$(git log --oneline -1)
    done_step "代码更新: ${before_commit:0:7} → ${after_commit:0:7}"

    step "更新 .env (补充缺失密钥)"
    update_env
    done_step ".env 已同步"

    step "更新 Python 依赖"
    sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install -r "${APP_HOME}/requirements.txt" -q
    done_step "依赖更新完成"

    step "重启服务"
    restart_services
    done_step "服务已重启"

    step "健康检查"
    health_check
}

# ==========================================================================
# 回滚
# ==========================================================================
do_rollback() {
    step "回滚到上一个版本"
    cd "${APP_HOME}"
    git reflog --oneline -5 | head -5
    if git reset --hard HEAD~1; then
        systemctl restart easykai-admin easykai-auth easykai-main
        echo -e "${OK} 已回滚到 $(git log --oneline -1)"
    else
        echo -e "${FAIL} 回滚失败"
    fi
}

# ==========================================================================
# .env 管理
# ==========================================================================
generate_env() {
    local env_file="${APP_HOME}/.env"
    if [ -f "${env_file}" ]; then
        echo -e "${WARN} .env 已存在，跳过生成"
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
# VeroRun 生产环境配置 — 由 deploy.sh 自动生成
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=${DOMAIN}
DB_PATH=${APP_HOME}/data/easykai.db
PG_HOST=localhost
PG_PORT=5432
PG_DB=verorun
PG_USER=verorun
PG_PASSWORD=change-me-in-production
JWT_SECRET=${JWT_SECRET}
FLASK_SECRET_KEY=${FLASK_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
EASYKAI_MODE=main

# Phase 1 — 安全加固密钥 (2026-07-28)
PLUGIN_LICENSE_SECRET=${PLUGIN_LICENSE_SECRET}
CAPTCHA_SECRET_KEY=${CAPTCHA_SECRET_KEY}
DEV_ACCOUNTS_ENCRYPTION_KEY=${DEV_ACCOUNTS_ENCRYPTION_KEY}
LICENSE_SERVER_SECRET=${LICENSE_SERVER_SECRET}

# API Keys (请替换为真实值)
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

    # 补充缺失的 Phase 1 密钥
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
        echo -e "${OK} 已补充缺失密钥: ${missing[*]}"
        chmod 600 "${env_file}"
    else
        echo -e "${OK} .env 所有密钥已就位"
    fi
}

# ==========================================================================
# systemd 服务
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

    # 8081 — 主站 (auth-center)
    write_one_service "easykai-main" 8081 "main" "--timeout 120 --log-level warning"

    # 8083 — Platform (auth-center)
    write_one_service "easykai-auth" 8083 "auth_center" "--timeout 120 --log-level warning"

    # 8084 — Admin
    write_one_service "easykai-admin" 8084 "admin" "--timeout 120 --max-requests=1000 --graceful-timeout=30 --log-level warning"
}

restart_services() {
    local services=("easykai-admin" "easykai-auth" "easykai-main")
    for svc in "${services[@]}"; do
        if systemctl is-enabled --quiet "${svc}" 2>/dev/null; then
            systemctl restart "${svc}"
            sleep 2
            if systemctl is-active --quiet "${svc}"; then
                echo -e "${OK} ${svc} 运行中"
            else
                echo -e "${FAIL} ${svc} 启动失败 — 查看: journalctl -u ${svc} -n 20"
            fi
        else
            echo -e "${WARN} ${svc} 未配置，跳过"
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
        echo -e "${WARN} Nginx 配置已存在，跳过"
        return
    fi

    cat > "${nginx_conf}" << NGXEOF
# VeroRun Nginx — 由 deploy.sh 自动生成

server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN} platform.${DOMAIN} agent.${DOMAIN};

    # ── 主站 ─────────────────────────────────
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

    # ── Platform 子域名 ───────────────────────
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

    # ── Agent 子域名 ──────────────────────────
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
# 健康检查
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
            echo -e "  ${FAIL} ${name} (:${port}) → 无响应"
            all_ok=false
        fi
    }

    check_port 8081 "easykai-main"
    check_port 8083 "easykai-platform"
    check_port 8084 "easykai-admin"

    # 检查新表迁移日志
    echo ""
    echo -e "${INFO} 迁移日志检查:"
    for svc in easykai-admin easykai-auth easykai-main; do
        journalctl -u "${svc}" --since "1 min ago" 2>/dev/null | grep -i "\[Migration\]" | tail -2 || true
    done

    if $all_ok; then
        echo -e "\n${OK} 全部服务健康"
    else
        echo -e "\n${FAIL} 部分服务异常，请检查日志"
    fi
}

# ==========================================================================
# 摘要
# ==========================================================================
print_summary() {
    local PUBLIC_IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "unknown")

    echo ""
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║              部署完成!                                        ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  主站:      https://${DOMAIN}                                  ║"
    echo "  ║  Platform:  https://platform.${DOMAIN}                         ║"
    echo "  ║  Admin:     https://agent.${DOMAIN}/admin/                     ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  常用命令:                                                    ║"
    echo "  ║    systemctl status easykai-{main,auth,admin}                 ║"
    echo "  ║    journalctl -u easykai-admin -f                             ║"
    echo "  ║    bash deploy/deploy.sh update                               ║"
    echo "  ║    bash deploy/deploy.sh rollback                             ║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ==========================================================================
# 主入口
# ==========================================================================

# 需要 root 权限
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${FAIL} 请用 sudo 运行: sudo bash deploy.sh [update|restart|health|rollback]"
    exit 1
fi

detect_mode "${1:-}"

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
        echo "用法: sudo bash deploy.sh [install|update|restart|health|rollback]"
        exit 1
        ;;
esac