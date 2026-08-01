#!/usr/bin/env python3
"""
VeroGuard — 统一守护进程配置（修正版）
============================================
所有参数优先级：环境变量 > 默认值
"""

import os

# ── 健康监控 ───────────────────────────────────
TARGETS = [
    "http://127.0.0.1:8085/health",
    "http://127.0.0.1:8081/health",
    "http://127.0.0.1:8084/health",
    "http://127.0.0.1:8083/health",
]

# 修正：使用 install.sh 创建的实际 systemd 服务名
SERVICE_MAP = {
    "http://127.0.0.1:8085/health": "verorun-health",
    "http://127.0.0.1:8081/health": "verorun-main",
    "http://127.0.0.1:8084/health": "verorun-admin",
    "http://127.0.0.1:8083/health": "verorun-auth",
}

CHECK_INTERVAL  = int(os.getenv('GUARDIAN_CHECK_INTERVAL', '30'))
MAX_FAILURES    = int(os.getenv('GUARDIAN_MAX_FAILURES', '3'))
COOLDOWN_SECS   = int(os.getenv('GUARDIAN_COOLDOWN', '300'))
ROLLBACK_TAG    = os.getenv('GUARDIAN_ROLLBACK_TAG', 'stable')
WEBHOOK_URL     = os.getenv('GUARDIAN_WEBHOOK_URL', '')
PROJECT_DIR     = os.getenv('GUARDIAN_PROJECT_DIR',
                    '/opt/verorun')
LOG_FILE        = os.getenv('GUARDIAN_LOG_FILE',
                    '/var/log/verorun-guardian.log')
GITHUB_RAW_BASE = os.getenv('GUARDIAN_GITHUB_RAW',
                    'https://raw.githubusercontent.com/fanjumin/VeroRunSystem')

# ── 回滚文件列表（修正点 6：扩展覆盖守护进程自身） ──
FILES_TO_ROLLBACK = [
    # 守护进程自身
    "veroguard/guardian.py",
    "veroguard/config.py",
    "veroguard/modules/health.py",
    "veroguard/modules/integrity.py",
    "veroguard/modules/fingerprint.py",
    "veroguard/modules/communicator.py",
    "veroguard/modules/executor.py",
    "veroguard/modules/runtime.py",
    # 核心服务文件
    "auth_server.py",
    "auth-center/models/database.py",
    "auth-center/services/jwt_service.py",
    "auth-center/services/license_service.py",
    "main_site/app.py",
    "admin/app.py",
    "plugin_manager/manager.py",
    "plugin_manager/license.py",
    # health check 插件
    "plugins/health_check/routes.py",
    "plugins/health_check/checkers.py",
    "plugins/health_check/ai_fixer.py",
    "plugins/health_check/models.py",
    "plugins/health_check/templates/health.html",
]

# ── 完整性校验 ─────────────────────────────────
INTEGRITY_CHECK_INTERVAL = int(os.getenv('GUARDIAN_INTEGRITY_INTERVAL', '300'))

# ── 心跳上报 ───────────────────────────────────
HEARTBEAT_INTERVAL = int(os.getenv('GUARDIAN_HEARTBEAT_INTERVAL', '300'))
PROBE_SECRET       = os.getenv('PROBE_SECRET', '')
DEPLOYMENT_CODE    = os.getenv('DEPLOYMENT_CODE', '')
REMOTE_URL         = os.getenv('GUARDIAN_REMOTE_URL', 'https://api.verorun.com')

# ── 状态文件路径 ───────────────────────────────
STATUS_FILE = os.getenv('GUARDIAN_STATUS_FILE',
                '/var/run/verorun-guardian/status.json')
