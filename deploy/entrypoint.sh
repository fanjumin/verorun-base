#!/bin/bash
# ============================================================
# VeroRun — 单容器入口脚本
# 职责：校验 /app/.env 存在 → 启动 Supervisor（nodaemon 前台运行）
# ============================================================
set -e

# 校验环境文件（应用启动必需）
# 审计 M-5 修复：.env 缺失且关键密钥（JWT_SECRET）未注入时立即退出，
# 避免服务以缺失密钥状态启动（启动后崩溃或使用不安全默认值）。
# 兼容性：docker-compose 已通过 env_file(.env) 注入环境变量时 JWT_SECRET 就绪 → 放行。
# 逃生阀：显式设置 VR_SKIP_ENV_CHECK=1 可跳过该检查。
if [ ! -f /app/.env ]; then
    if [ -z "${JWT_SECRET:-}" ] && [ "${VR_SKIP_ENV_CHECK:-}" != "1" ]; then
        echo "FATAL: /app/.env not found and JWT_SECRET not set — refusing to start (set VR_SKIP_ENV_CHECK=1 to bypass)" >&2
        exit 1
    fi
    echo "WARN: /app/.env not found — using environment variables injected by docker-compose" >&2
fi

# 审计 v3 M2 修复：Supervisor 各 program 无 JWT_SECRET 等密钥环境变量
# 启动前将 .env 导出到环境，supervisord 子进程（gunicorn/nginx）自动继承
if [ -f /app/.env ]; then
    # 审计 P2-5：source 前校验 .env 不含 shell 元字符，防注入
    if grep -q '[;&|`$()]' /app/.env 2>/dev/null; then
        echo "FATAL: /app/.env contains shell metacharacters" >&2
        exit 1
    fi
    set -a
    # shellcheck disable=SC1091
    source /app/.env
    set +a
fi

# 确保 Supervisor 运行目录存在
mkdir -p /var/run/supervisor
chmod 755 /var/run/supervisor

# 审计 D6：Docker 变体 TLS —— 检测挂载证书（SSL_CERT_DIR，如宿主 /etc/letsencrypt/live）
# 存在则启用 443 ssl + HSTS；无证书则删除占位符保持纯 HTTP（容器 nginx -t 通过）。
_NGINX_CONF=/etc/nginx/sites-enabled/default
_SSL_CERT_DIR="${SSL_CERT_DIR:-/etc/letsencrypt/live}"
if [ -f "${_SSL_CERT_DIR}/fullchain.pem" ] && [ -f "${_SSL_CERT_DIR}/privkey.pem" ]; then
    echo "[TLS] certificate found in ${_SSL_CERT_DIR} — enabling HTTPS 443"
    sed -i 's|__SSL_LISTEN__|    listen 443 ssl http2;|' "${_NGINX_CONF}"
    sed -i "s|__SSL_CERT__|    ssl_certificate     ${_SSL_CERT_DIR}/fullchain.pem;\\
    ssl_certificate_key ${_SSL_CERT_DIR}/privkey.pem;\\
    ssl_protocols TLSv1.2 TLSv1.3;\\
    ssl_ciphers HIGH:!aNULL:!MD5;\\
    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;|" "${_NGINX_CONF}"
else
    echo "[TLS] no certificate in ${_SSL_CERT_DIR} — serving plain HTTP (set SSL_CERT_DIR to enable HTTPS)"
    sed -i '/__SSL_LISTEN__/d; /__SSL_CERT__/d' "${_NGINX_CONF}"
fi

# 前台运行 Supervisor（nodaemon=true），接管容器 PID 1
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
