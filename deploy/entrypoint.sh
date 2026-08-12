#!/bin/bash
# ============================================================
# VeroRun — Single-container entrypoint script
# Purpose: verify /app/.env exists → start Supervisor (nodaemon, foreground)
# ============================================================
set -e

# Verify the environment file (required for app startup)
# 审计 M-5 修复：exit immediately when .env is missing and the critical secret (JWT_SECRET) is not injected,
# to avoid starting the service without secrets (crash after startup or unsafe defaults).
# Compatibility: when docker-compose already injects env vars via env_file(.env), JWT_SECRET is ready → allow startup.
# Escape hatch: explicitly set VR_SKIP_ENV_CHECK=1 to skip this check.
if [ ! -f /app/.env ]; then
    if [ -z "${JWT_SECRET:-}" ] && [ "${VR_SKIP_ENV_CHECK:-}" != "1" ]; then
        echo "FATAL: /app/.env not found and JWT_SECRET not set — refusing to start (set VR_SKIP_ENV_CHECK=1 to bypass)" >&2
        exit 1
    fi
    echo "WARN: /app/.env not found — using environment variables injected by docker-compose" >&2
fi

# 审计 v3 M2 修复：Supervisor programs lack secret env vars such as JWT_SECRET
# Export .env into the environment before starting; supervisord child processes (gunicorn/nginx) inherit it automatically
if [ -f /app/.env ]; then
    # 审计 P2-5：verify .env contains no shell metacharacters before sourcing, to prevent injection
    if grep -q '[;&|`$()]' /app/.env 2>/dev/null; then
        echo "FATAL: /app/.env contains shell metacharacters" >&2
        exit 1
    fi
    set -a
    # shellcheck disable=SC1091
    source /app/.env
    set +a
fi

# Ensure the Supervisor runtime directory exists
mkdir -p /var/run/supervisor
chmod 755 /var/run/supervisor

# 审计 D6：Docker variant TLS —— detect mounted certificates (SSL_CERT_DIR, e.g. host /etc/letsencrypt/live)
# If present, enable 443 ssl + HSTS; otherwise delete the placeholders to stay plain HTTP (container nginx -t passes).
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

# Run Supervisor in the foreground (nodaemon=true), taking over container PID 1
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
