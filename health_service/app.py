#!/usr/bin/env python3
"""
Health Service — 独立 Flask 入口 (v2.0)
============================================
将 Health Check 从 admin Flask (8084) 剥离为独立服务 (8085)，
确保 admin 挂了 Health Check 仍可运行。

用法:
    # 开发:
    python3 health_service/app.py

    # 生产 (gunicorn):
    gunicorn -w 2 -b 0.0.0.0:8085 health_service.app:app
"""
import os
import sys

# 确保能从项目根目录 import health_check
# 注意: 用 append() 而不是 insert(0, ...)，避免项目中的 platform/ 包 shadow stdlib platform 模块
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from flask import Flask
from health_check.routes import health_bp
from health_check.models import init_health_tables, migrate_alert_schema

app = Flask(__name__)
app.register_blueprint(health_bp)  # url_prefix 已在 BP 定义中: /admin/health


@app.route('/health')
def ping():
    """Liveness probe — health-service 自身"""
    return {'status': 'ok', 'service': 'health-service'}


@app.route('/ready')
def ready():
    """Readiness probe — 检查数据库连接"""
    try:
        from health_check.models import get_db
        db = get_db()
        db.execute('SELECT 1').fetchone()
        return {'status': 'ready', 'service': 'health-service'}
    except Exception as e:
        return {'status': 'not_ready', 'error': str(e)}, 503


if __name__ == '__main__':
    init_health_tables()
    migrate_alert_schema()
    app.run(host='0.0.0.0', port=8085, debug=False)
