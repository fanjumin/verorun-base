#!/bin/bash
# ==========================================================================
# VeroRun / easykai.cn — 裸机一键部署脚本 (v1.0)
# ==========================================================================
# 适用: Ubuntu 22.04 / 24.04 全新 VPS (Google Cloud / 阿里云 / 腾讯云等)
#
# 用法:
#   curl -sSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/main/deploy/bootstrap.sh | sudo bash
#
#   参数说明:
#     $1 域名      (默认: easykai.cn)
#     $2 安装路径   (默认: /var/www/verorun)
#     $3 Git 仓库   (默认: https://github.com/fanjumin/VeroRunSystem.git)
#     $4 Git 分支   (默认: main)
#
#   示例:
#     sudo bash bootstrap.sh
#     sudo bash bootstrap.sh mysite.com
#     sudo bash bootstrap.sh mysite.com /opt/myapp
# ==========================================================================

set -euo pipefail

# ── 参数 ──────────────────────────────────────────────────────────────
DOMAIN="${1:-easykai.cn}"
APP_ROOT="${2:-/var/www/verorun}"
GIT_REPO="${3:-https://github.com/fanjumin/VeroRunSystem.git}"
GIT_BRANCH="${4:-main}"

# ── 颜色 ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; }
info() { echo -e "${BLUE}[i]${NC} $*"; }

# ── 路径常量 ──────────────────────────────────────────────────────────
SYS_USER="www-data"
VENV_DIR="${APP_ROOT}/venv"

# ==========================================================================
# 阶段 0: 前置检查
# ==========================================================================
banner() {
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║       VeroRun 裸机部署脚本  v1.0                       ║"
    echo "  ║       域名: ${DOMAIN}                                   ║"
    echo "  ║       路径: ${APP_ROOT}                                  ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo ""
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "请用 sudo 运行: sudo bash bootstrap.sh"
        exit 1
    fi
    log "root 权限确认"
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        err "无法识别操作系统，需要 Ubuntu 22.04+"
        exit 1
    fi
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        warn "检测到 $ID，脚本专为 Ubuntu 设计，可能不兼容"
        read -p "是否继续? (y/N): " yn
        [ "$yn" != "y" ] && exit 1
    fi
    log "OS: $NAME $VERSION_ID"
}

# ==========================================================================
# 阶段 1: 系统环境安装
# ==========================================================================
install_system_deps() {
    log "更新 apt 源..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq

    log "安装系统依赖 (python3, nginx, redis, certbot, git)..."
    apt-get install -y -qq \
        python3 python3-venv python3-pip python3-dev \
        nginx redis-server \
        certbot python3-certbot-nginx \
        git curl wget \
        build-essential libssl-dev \
        > /dev/null 2>&1

    log "系统依赖安装完成"
}

install_nodejs() {
    if command -v node &>/dev/null; then
        NODE_VER=$(node -v)
        log "Node.js 已安装: $NODE_VER"
    else
        log "安装 Node.js 20.x..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
        apt-get install -y -qq nodejs > /dev/null 2>&1
        log "Node.js $(node -v) 安装完成"
    fi
}

install_pm2() {
    if command -v pm2 &>/dev/null; then
        log "PM2 已安装: $(pm2 -v)"
    else
        log "安装 PM2..."
        npm install -g pm2 > /dev/null 2>&1
        log "PM2 $(pm2 -v) 安装完成"
    fi
}

create_system_user() {
    # www-data 是 Ubuntu 内置的 Web 服务用户，无需创建
    if id "$SYS_USER" &>/dev/null; then
        log "用户 $SYS_USER 已存在（Ubuntu 内置）"
    else
        log "创建用户 $SYS_USER ..."
        useradd -r -s /usr/sbin/nologin "$SYS_USER"
        log "用户 $SYS_USER 创建完成"
    fi

    mkdir -p "$APP_ROOT"
}

# ==========================================================================
# 阶段 2: 代码部署
# ==========================================================================
clone_repo() {
    if [ -d "${APP_ROOT}/.git" ]; then
        log "仓库已存在，执行 git pull..."
        cd "$APP_ROOT"
        git fetch origin "$GIT_BRANCH"
        git reset --hard "origin/$GIT_BRANCH"
        log "代码已更新到最新"
    else
        rm -rf "$APP_ROOT"
        log "克隆仓库 $GIT_REPO (分支: $GIT_BRANCH)..."
        git clone -b "$GIT_BRANCH" "$GIT_REPO" "$APP_ROOT"
        log "代码克隆完成"
    fi
}

setup_python_venv() {
    log "创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"

    log "安装 Python 依赖 (这可能需要几分钟)..."
    "${VENV_DIR}/bin/pip" install --upgrade pip > /dev/null 2>&1
    "${VENV_DIR}/bin/pip" install -r "${APP_ROOT}/requirements.txt" > /dev/null 2>&1
    log "Python 依赖安装完成"
}

generate_env() {
    if [ -f "${APP_ROOT}/.env" ]; then
        log ".env 已存在，保留现有配置"
        return
    fi

    log "生成 .env 配置..."
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > "${APP_ROOT}/.env" << EOF
# VeroRun 生产环境配置 — 由 bootstrap.sh 自动生成
# 部署后请修改 API Key 等敏感值
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=${DOMAIN}
DB_PATH=data/easykai.db
JWT_SECRET=${JWT_SECRET}
FLASK_SECRET_KEY=${FLASK_SECRET}
EASYKAI_MODE=main
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DB=verorun
PG_USER=easykai
PG_PASSWORD=
DASHSCOPE_TEXT_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here
EOF
    log ".env 已生成 (JWT/Flask 密钥已随机生成，API Key 请稍后在后台修改)"
}

create_data_dir() {
    log "创建数据目录..."
    mkdir -p "${APP_ROOT}/data/logs"
    # 创建空 SQLite 数据库目录，让应用自动建表
    touch "${APP_ROOT}/data/.gitkeep"
}

setup_permissions() {
    log "设置文件权限..."
    chown -R "${SYS_USER}:${SYS_USER}" "$APP_ROOT"
    chmod 755 "$APP_ROOT"
    chmod 600 "${APP_ROOT}/.env"
}

# ==========================================================================
# 阶段 3: Nginx 配置
# ==========================================================================
write_nginx_config() {
    log "写入 Nginx 配置..."

    cat > /etc/nginx/sites-available/easykai.conf << 'NGINX_EOF'
# ========================================================
# VeroRun / easykai — 统一 Nginx 配置
# 由 bootstrap.sh 自动生成
# ========================================================
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# ── www / 根域 ─────────────────────────────────────────
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

# ── platform 子域名 ─────────────────────────────────────
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

# ── agent 子域名 ────────────────────────────────────────
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

    # 替换占位符
    sed -i "s|__DOMAIN__|${DOMAIN}|g" /etc/nginx/sites-available/easykai.conf
    sed -i "s|__APP_ROOT__|${APP_ROOT}|g" /etc/nginx/sites-available/easykai.conf

    # 启用站点
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/easykai.conf /etc/nginx/sites-enabled/easykai.conf

    log "Nginx 配置已写入并启用"
}

test_nginx() {
    log "验证 Nginx 配置..."
    if nginx -t 2>&1; then
        log "Nginx 配置语法正确"
    else
        err "Nginx 配置有误，请检查 /etc/nginx/sites-available/easykai.conf"
        exit 1
    fi
}

setup_ssl() {
    log "尝试申请 SSL 证书..."
    info "请确保域名 ${DOMAIN} *.${DOMAIN} 已解析到本机公网 IP"

    # 先确保 nginx 运行（HTTP 模式，certbot 需要）
    systemctl restart nginx

    # 申请证书（非交互模式）
    if certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" -d "platform.${DOMAIN}" -d "agent.${DOMAIN}" \
        --non-interactive --agree-tos --email "admin@${DOMAIN}" --redirect 2>&1; then
        log "SSL 证书申请成功"
        # certbot 会自动更新 nginx 配置添加 SSL
    else
        warn "SSL 证书申请失败（域名可能未解析或 80 端口不通）"
        warn "当前仅启用 HTTP 模式，稍后可手动运行: certbot --nginx"
    fi

    systemctl restart nginx
}

# ==========================================================================
# 阶段 4: PM2 进程管理配置
# ==========================================================================
write_pm2_config() {
    log "写入 PM2 配置..."

    cat > "${APP_ROOT}/ecosystem.config.js" << PM2_EOF
// VeroRun PM2 进程配置 — 由 bootstrap.sh 自动生成
module.exports = {
  apps: [
    // ─── 主站 8081 (auth-center) ───
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
    // ─── Health Guardian (看门狗) ───
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

    log "PM2 配置已写入 ${APP_ROOT}/ecosystem.config.js"
}

setup_pm2_systemd() {
    log "配置 PM2 systemd 自启动..."

    # PM2 的 PM2_HOME 放在 easykai 用户目录下
    PM2_HOME="/home/${SYS_USER}/.pm2"

    # 创建 systemd service
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
    log "PM2 systemd 服务已配置"
}

start_services() {
    log "启动所有服务..."

    # 先停掉可能残留的进程
    pkill -f "run_auth_wsgi.py" 2>/dev/null || true
    pkill -f "run_gunicorn.py" 2>/dev/null || true
    pkill -f "health_guardian.py" 2>/dev/null || true
    sleep 2

    # 确保 PM2_HOME 目录存在且权限正确
    PM2_HOME="/home/${SYS_USER}/.pm2"
    mkdir -p "$PM2_HOME"
    chown -R "${SYS_USER}:${SYS_USER}" "$PM2_HOME"

    # 以 easykai 用户启动 PM2
    sudo -u "$SYS_USER" env PM2_HOME="$PM2_HOME" pm2 start "${APP_ROOT}/ecosystem.config.js"

    # 保存 PM2 进程列表（用于 resurrect）
    sudo -u "$SYS_USER" env PM2_HOME="$PM2_HOME" pm2 save

    log "所有服务已通过 PM2 启动"
}

# ==========================================================================
# 阶段 5: 验证
# ==========================================================================
verify_services() {
    log "等待服务就绪..."
    sleep 5

    local failed=0

    check_port() {
        local port=$1 name=$2
        if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://127.0.0.1:${port}/" 2>/dev/null | grep -qE '^(2|3)'; then
            log "  ${name} (:${port}) — OK"
        else
            err "  ${name} (:${port}) — 未响应"
            failed=1
        fi
    }

    echo ""
    info "冒烟测试..."
    check_port 8081 "easykai-main"
    check_port 8083 "easykai-platform"
    check_port 8084 "easykai-admin"

    if [ "$failed" -eq 0 ]; then
        echo ""
        log "所有服务启动成功!"
    else
        echo ""
        warn "部分服务未就绪，请运行 pm2 logs 查看日志"
    fi
}

# ==========================================================================
# 部署摘要
# ==========================================================================
print_summary() {
    local PUBLIC_IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "未知")

    echo ""
    echo "  ╔══════════════════════════════════════════════════════════════╗"
    echo "  ║              部署完成!                                        ║"
    echo "  ╠══════════════════════════════════════════════════════════════╣"
    echo "  ║  域名:      ${DOMAIN}                                          $(printf '%*s' $((48 - ${#DOMAIN})) '')║"
    echo "  ║  IP:        ${PUBLIC_IP}                                       $(printf '%*s' $((48 - ${#PUBLIC_IP})) '')║"
    echo "  ║                                                              ║"
    echo "  ║  服务端口:                                                    ║"
    echo "  ║    主站 (8081):    https://${DOMAIN}                          $(printf '%*s' $((35 - ${#DOMAIN})) '')║"
    echo "  ║    Platform (8083): https://platform.${DOMAIN}                $(printf '%*s' $((28 - ${#DOMAIN})) '')║"
    echo "  ║    Admin (8084):    https://agent.${DOMAIN}                   $(printf '%*s' $((28 - ${#DOMAIN})) '')║"
    echo "  ║                                                              ║"
    echo "  ║  常用命令:                                                    ║"
    echo "  ║    pm2 status          — 查看进程状态                         ║"
    echo "  ║    pm2 logs            — 查看日志                             ║"
    echo "  ║    pm2 restart all     — 重启所有服务                         ║"
    echo "  ║                                                              ║"
    echo "  ║  后续步骤:                                                    ║"
    echo "  ║    1. 编辑 ${APP_ROOT}/.env 填入真实 API Key                   ║"
    echo "  ║    2. 如果 SSL 未成功，手动运行: certbot --nginx              ║"
    echo "  ║    3. 访问 https://agent.${DOMAIN}/admin/ 管理后台            $(printf '%*s' $((28 - ${#DOMAIN})) '')║"
    echo "  ╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# ==========================================================================
# 主流程
# ==========================================================================
main() {
    banner
    check_root
    check_os

    echo ""
    info "开始部署到: ${APP_ROOT}"
    info "Git 仓库:    ${GIT_REPO}"
    info "分支:        ${GIT_BRANCH}"
    echo ""

    # 阶段 1
    echo "━━━ 阶段 1/5: 系统环境 ━━━"
    install_system_deps
    install_nodejs
    install_pm2
    create_system_user

    # 阶段 2
    echo "━━━ 阶段 2/5: 代码部署 ━━━"
    clone_repo
    setup_python_venv
    generate_env
    create_data_dir
    setup_permissions

    # 阶段 3
    echo "━━━ 阶段 3/5: Nginx 配置 ━━━"
    write_nginx_config
    test_nginx
    setup_ssl

    # 阶段 4
    echo "━━━ 阶段 4/5: PM2 进程管理 ━━━"
    write_pm2_config
    setup_pm2_systemd
    start_services

    # 阶段 5
    echo "━━━ 阶段 5/5: 验证 ━━━"
    verify_services

    print_summary
}

main "$@"
