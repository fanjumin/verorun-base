#!/usr/bin/env python3
"""
Health Check — 系统健康巡检中心 + 插件
============================================
全站自动化健康巡检：可扩展检查框架、定时自动巡检、仪表盘、
异常告警（邮件/站内信/Webhook）、与 Workflow 引擎集成（自动恢复）。
独立数据库 data/health.db，8 张表完全自包含。

使用方式:
    from plugins.health_check import health_bp
    app.register_blueprint(health_bp)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .routes import health_bp
from .models import init_health_tables, get_db

from plugin_manager.base import BasePlugin

__all__ = ['health_bp', 'init_health_tables', 'get_db', 'HealthCheckPlugin']


class HealthCheckPlugin(BasePlugin):
    name = 'health_check'
    version = '0.1.0'
    description = 'System Health Check — Automated health monitoring + alerting + trend analysis'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立数据库表"""
        from .models import init_health_tables
        try:
            init_health_tables()
            print('[HealthCheck] Independent DB initialized (data/health.db)')
        except Exception as e:
            print(f'[HealthCheck] DB init warning: {e}')
        return True

    def on_enable(self, registry):
        """启用时: 初始化表 + 迁移 schema + 种子检查项 + 注册定时巡检"""
        from .models import init_health_tables, migrate_alert_schema, seed_default_checks

        init_health_tables()
        migrate_alert_schema()
        seed_default_checks()
        print('[HealthCheck] Tables initialized, schema migrated, default checks seeded')

        # 初始化插件 i18n（注入 self.t 到各模块）
        from . import routes as _routes
        from . import checkers as _checkers
        from . import discovery as _discovery
        from . import scheduler_setup as _sched
        _routes.init_i18n(self.t)
        _checkers.init_i18n(self.t)
        _discovery.init_i18n(self.t)
        _sched.init_i18n(self.t)
        print('[HealthCheck] Plugin i18n initialized')

        # 注册定时巡检（写入 orchestrator cron_jobs 表）
        try:
            _sched.seed_health_schedules()
            print('[HealthCheck/Scheduler] Health check schedules registered')
        except Exception as e:
            print(f'[HealthCheck/Scheduler] Warning: {e}')

        return True

    def register_routes(self):
        """注册健康巡检 Blueprint"""
        from . import health_bp
        return [health_bp]

    def on_disable(self, registry):
        print('[HealthCheck] Disabled')
        return True