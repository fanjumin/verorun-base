#!/usr/bin/env python3
"""
Health Check Plugin — System Health Monitoring
================================================
独立数据库 data/health.db，8 张表完全自包含。

插件能力:
  - on_install: 初始化健康巡检表
  - on_enable:  迁移 schema + 种子默认检查项 + 注册定时巡检
  - register_routes: 注册 /admin/health/* 仪表盘
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class HealthCheckPlugin(BasePlugin):
    name = 'health_check'
    version = '0.1.0'
    description = 'System Health Check — Automated health monitoring + alerting + trend analysis'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立数据库表"""
        from health_check.models import init_health_tables
        try:
            init_health_tables()
            print('[HealthCheck] Independent DB initialized (data/health.db)')
        except Exception as e:
            print(f'[HealthCheck] DB init warning: {e}')
        return True

    def on_enable(self, registry):
        """启用时: 初始化表 + 迁移 schema + 种子检查项 + 注册定时巡检"""
        from health_check.models import init_health_tables, migrate_alert_schema, seed_default_checks

        init_health_tables()
        migrate_alert_schema()
        seed_default_checks()
        print('[HealthCheck] Tables initialized, schema migrated, default checks seeded')

        # 初始化插件 i18n（注入 self.t 到各模块）
        from health_check import routes as _routes
        from health_check import checkers as _checkers
        from health_check import discovery as _discovery
        from health_check import scheduler_setup as _sched
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
        from health_check import health_bp
        return [health_bp]

    def on_disable(self, registry):
        print('[HealthCheck] Disabled')
        return True