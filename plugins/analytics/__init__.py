#!/usr/bin/env python3
"""
Analytics Plugin — Server-side Cookieless Analytics
=====================================================
独立数据库 data/analytics.db，不依赖主库。

插件能力:
  - on_enable:  初始化 11 张分析表 + 注册请求中间件 + 启动后台聚合线程
  - on_disable: 卸载 Blueprint（中间件需重启才生效）
  - register_routes: 注册 /admin/analytics 仪表盘
"""

import os
import sys
import threading

# 确保 analytics 包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin
from plugin_manager.hooks import get_hook_registry


class AnalyticsPlugin(BasePlugin):
    name = 'analytics'
    version = '1.2.0'
    description = 'Analytics Middleware & Dashboard — Server-side Cookieless Analytics'
    author = 'VeroRun'

    _middleware = None
    _processor_thread = None

    def get_config_value(self, key: str, default=None):
        """优先 PluginManager，回退到 plugin.json 默认值"""
        try:
            mgr = getattr(self.app.extensions, 'get', lambda x: None)('plugin_manager')
            if mgr:
                pm_cfg = mgr.get_config(self.identifier) or {}
                if key in pm_cfg:
                    return pm_cfg[key]
        except Exception:
            pass
        return self._config.get(key, default)

    def on_install(self, registry):
        """安装时初始化独立数据库表"""
        from .models import init_analytics_tables
        try:
            init_analytics_tables()
            print('[Analytics] Independent DB initialized (data/analytics.db)')
        except Exception as e:
            print(f'[Analytics] DB init warning: {e}')
        return True

    def on_enable(self, registry):
        """启用时: 注册中间件 + 启动聚合线程 + 初始化 i18n"""
        from .middleware import AnalyticsMiddleware
        from .processor import AnalyticsProcessor
        from .dashboard import init_i18n

        # 初始化 i18n
        init_i18n(self.t)

        # 初始化数据库表（幂等）
        from .models import init_analytics_tables
        init_analytics_tables()

        # 注册请求中间件
        sample_rate = self.get_config_value('sample_rate', 1.0)
        geoip_enabled = self.get_config_value('geoip_enabled', True)
        service_name = self.get_config_value('service_name', 'admin')

        self._middleware = AnalyticsMiddleware(
            self.app,
            service_name=service_name,
            geoip_enabled=geoip_enabled,
            sample_rate=sample_rate
        )

        # 启动后台聚合处理器（每 60 秒）
        processor = AnalyticsProcessor()

        def _loop():
            import time
            while True:
                try:
                    processor.process()
                except Exception as e:
                    print(f'[Analytics Processor] Error: {e}')
                time.sleep(60)

        self._processor_thread = threading.Thread(
            target=_loop, daemon=True, name='analytics-processor'
        )
        self._processor_thread.start()

        print(f'[Analytics] Middleware registered [{service_name}] sample_rate={sample_rate}')
        print(f'[Analytics] Background processor started (60s interval)')
        print('[Analytics] Dashboard filter registered (module-level)')
        return True

    def register_routes(self):
        """注册 Analytics 仪表盘 Blueprint"""
        from .dashboard import analytics_bp
        return [analytics_bp]

    def on_disable(self, registry):
        """禁用时: 卸载 Blueprint
        注意: Flask 中间件无法热卸载，需重启服务后完全移除
        """
        self._middleware = None
        print('[Analytics] Disabled — restart required to fully remove middleware')
        return True


# ═══════════════════════════════════════════════════════════════
# Module-level: dashboard.data filter + enrich function
# 在模块导入时注册，不依赖 on_enable() 调用。
# 当 PluginManager 跳过 enable()（插件已 ACTIVE）时仍能工作。
# ═══════════════════════════════════════════════════════════════

def enrich_dashboard(value, conn=None):
    """从 analytics 独立 PG 查询仪表盘数据，注入到 data dict

    双库策略:
      - analytics 特化表（daily_stats / visitor_sessions / page_stats）
        → 通过 .models.get_db() 连接独立 PostgreSQL
      - 主库表（agent_token_daily / billing_orders）
        → 复用上层传入的 conn（SQLite / PG 均可）
    """
    data = value
    # ── Part A: Analytics PG 连接 ──
    try:
        from .models import get_db as get_analytics_db
        aconn = get_analytics_db()
    except Exception:
        aconn = None

    if aconn is not None:
        def _rb():
            try:
                aconn._conn.rollback()
            except Exception:
                pass
        try:
            pvuv = aconn.execute(
                "SELECT pv, uv FROM analytics_daily_stats WHERE date=CURRENT_DATE::text"
            ).fetchone()
            data['today_pv'] = pvuv['pv'] if pvuv else 0
            data['today_uv'] = pvuv['uv'] if pvuv else 0
        except Exception:
            pass
        finally:
            _rb()
        try:
            online = aconn.execute(
                "SELECT COUNT(DISTINCT visitor_hash) as c FROM analytics_visitor_sessions "
                "WHERE end_time>=EXTRACT(EPOCH FROM NOW()) - 300"
            ).fetchone()
            data['online_now'] = online['c'] if online else 0
        except Exception:
            pass
        finally:
            _rb()
        try:
            pages = aconn.execute(
                "SELECT path, pv FROM analytics_page_stats WHERE date=CURRENT_DATE::text "
                "ORDER BY pv DESC LIMIT 3"
            ).fetchall()
            data['top_pages'] = [{'path': r['path'], 'pv': r['pv']} for r in pages]
        except Exception:
            pass
        finally:
            _rb()
        try:
            trend = aconn.execute(
                "SELECT date, pv, uv FROM analytics_daily_stats "
                "WHERE date >= (CURRENT_DATE - INTERVAL '30 days')::text ORDER BY date ASC"
            ).fetchall()
            data['trend_30d'] = [dict(r) for r in trend]
        except Exception:
            pass
        finally:
            aconn.close()

    # ── Part B: 主库连接（conn 由上层 dashboard() 传入） ──
    if conn is not None:
        def _rb_conn():
            try:
                conn._conn.rollback()
            except Exception:
                pass
        try:
            r = conn.execute(
                "SELECT COALESCE(SUM(total_tokens),0) as c FROM agent_token_daily WHERE stat_date=CURRENT_DATE::text"
            ).fetchone()
            data['today_tokens'] = r['c'] if r else 0
        except Exception:
            pass
        finally:
            _rb_conn()
        try:
            agents = conn.execute(
                "SELECT t.agent_id, t.agent_name, t.total_tokens as total "
                "FROM agent_token_daily t WHERE t.stat_date=CURRENT_DATE::text "
                "ORDER BY t.total_tokens DESC LIMIT 3"
            ).fetchall()
            data['top_token_agents'] = [dict(r) for r in agents]
        except Exception:
            pass
        finally:
            _rb_conn()
        try:
            rev = conn.execute(
                "SELECT DATE(paid_at) as date, COALESCE(SUM(amount),0) as revenue "
                "FROM billing_orders WHERE status='paid' AND paid_at >= CURRENT_DATE - INTERVAL '30 days' "
                "GROUP BY DATE(paid_at) ORDER BY date ASC"
            ).fetchall()
            data['revenue_trend_30d'] = [dict(r) for r in rev]
        except Exception:
            pass
        finally:
            _rb_conn()
    return data


# 注册 filter（模块导入时执行，worker 重启后自动生效）
_hooks = get_hook_registry()
existing = _hooks.list_filters('dashboard.data')
already = any(
    h.get('identifier') == 'analytics'
    for hooks_list in existing.values()
    for h in hooks_list
)
if not already:
    _hooks.add_filter('dashboard.data', enrich_dashboard,
                       priority=10, identifier='analytics')
    print('[Analytics] Module-level dashboard filter registered')
else:
    print('[Analytics] Dashboard filter already registered, skip')
