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

# 前台运行 Supervisor（nodaemon=true），接管容器 PID 1
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
