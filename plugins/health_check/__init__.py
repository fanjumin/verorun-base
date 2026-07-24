#!/usr/bin/env python3
"""
Health Check — 系统健康巡检中心 + 插件
============================================
全站自动化健康巡检：可扩展检查框架、定时自动巡检、仪表盘、
异常告警（邮件/站内信/Webhook）、与 Workflow 引擎集成（自动恢复）。
使用 PostgreSQL health schema，8 张表完全自包含。

使用方式:
    from plugins.health_check import health_bp
    app.register_blueprint(health_bp)
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from .routes import health_bp
from .models import init_health_tables, get_db

from plugin_manager.base import BasePlugin

__all__ = ['health_bp', 'init_health_tables', 'get_db', 'HealthCheckPlugin']


class HealthCheckPlugin(BasePlugin):
    name = 'health_check'
    version = '1.2.0'
    description = 'System Health Check — Automated health monitoring + alerting + trend analysis'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立数据库表"""
        from .models import init_health_tables
        try:
            init_health_tables()
            print('[HealthCheck] Database tables initialized (PG health schema)')
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

        # 注册 Dashboard 数据注入 filter
        try:
            from plugin_manager.hooks import get_hook_registry
            _hooks = get_hook_registry()
            already = any(
                h.get('identifier') == 'health_check'
                for hooks_list in _hooks.list_filters('dashboard.data').values()
                for h in hooks_list
            )
            if not already:
                _hooks.add_filter('dashboard.data', enrich_dashboard,
                                   priority=15, identifier='health_check')
                print('[HealthCheck] Dashboard data filter registered')
        except Exception as e:
            print(f'[HealthCheck] Dashboard filter registration warning: {e}')

        return True

    def register_routes(self):
        """注册健康巡检 Blueprint"""
        from . import health_bp
        return [health_bp]

    def on_disable(self, registry):
        print('[HealthCheck] Disabled')
        return True


# ═══════════════════════════════════════════════════════════════
# Dashboard data enrichment
# ═══════════════════════════════════════════════════════════════

def enrich_dashboard(value, conn=None):
    """从 health_check 独立 DB 注入健康数据到 Dashboard"""
    data = value
    from .models import get_latest_status, get_unread_alert_count, get_health_trend

    try:
        status = get_latest_status()
        if status:
            passed = status.get('passed', 0) or 0
            warnings = status.get('warnings', 0) or 0
            errors = status.get('errors', 0) or 0
            total = passed + warnings + errors
            # 与 health_check 插件 Overview 页保持一致: passed/total*100
            if total > 0:
                score = round(passed * 100 / total, 1)
            else:
                score = 100.0
            data['health_score'] = score
            data['health_passed'] = passed
            data['health_warnings'] = warnings
            data['health_errors'] = errors
    except Exception:
        pass
    try:
        data['unread_alerts'] = get_unread_alert_count()
    except Exception:
        pass
    try:
        trend = get_health_trend(7)
        data['health_trend_7d'] = trend if trend else []
    except Exception:
        pass

    return data