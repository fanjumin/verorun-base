#!/bin/bash
# ============================================================
# 易站AI — 单容器入口脚本
# 职责：校验 /app/.env 存在 → 启动 Supervisor（nodaemon 前台运行）
# ============================================================
set -e

# 校验环境文件（应用启动必需）
if [ ! -f /app/.env ]; then
    echo "WARN: /app/.env not found — services will run without env config" >&2
fi

# 审计 v3 M2 修复：Supervisor 各 program 无 JWT_SECRET 等密钥环境变量
# 启动前将 .env 导出到环境，supervisord 子进程（gunicorn/nginx）自动继承
if [ -f /app/.env ]; then
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
