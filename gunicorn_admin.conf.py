"""Gunicorn 配置 — Admin 后台服务 (port 8084)

用途:
    python3 run_admin_wsgi.py -c gunicorn_admin.conf.py

注意:
    - 不启用 preload（SQLite 兼容性）：每个 worker 独立初始化
    - workers=2：SQLite 写密集型场景最优（更多 worker 增加锁争用）
    - timeout=120：cold start 可能有 20+ 秒的初始化时间
"""
import os

# ─── 绑定 ───────────────────────────────────────────────
bind = '0.0.0.0:8084'

# ─── Worker 进程 ───────────────────────────────────────
workers = 2
worker_class = 'sync'
threads = 1

# ─── 超时 ───────────────────────────────────────────────
timeout = 120                  # 冷启动最长等待时间
graceful_timeout = 30          # 优雅重启等待时间
keepalive = 5                  # 长连接保持秒数

# ─── 请求限制（防止内存泄漏）────────────────────────────
max_requests = 1000
max_requests_jitter = 200

# ─── 日志 ───────────────────────────────────────────────
accesslog = '-'
errorlog = '-'
loglevel = 'info'
capture_output = True

# ─── 进程管理 ───────────────────────────────────────────
daemon = False
pidfile = None
umask = 0o022

# ─── 安全 ───────────────────────────────────────────────
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8192
