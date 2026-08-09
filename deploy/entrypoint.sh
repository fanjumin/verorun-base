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

# 确保 Supervisor 运行目录存在
mkdir -p /var/run/supervisor
chmod 755 /var/run/supervisor

# 前台运行 Supervisor（nodaemon=true），接管容器 PID 1
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
