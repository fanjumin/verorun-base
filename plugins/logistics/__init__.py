#!/usr/bin/env python3
"""
Logistics Plugin — 物流配送查询插件（完全独立）
================================================
快递鸟物流轨迹查询，支持 600+ 快递公司。
- 独立数据库：logistics.db（查询日志）
- 配置通过主库 system_config 只读
"""
from i18n import _
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin
from plugin_manager.logger import get_plugin_logger

logger = get_plugin_logger('logistics')


class LogisticsPlugin(BasePlugin):

    def on_install(self, registry):
        """安装时初始化独立 logistics.db"""
        from .models import init_logistics_db
        init_logistics_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库（幂等）"""
        from .models import init_logistics_db
        init_logistics_db()
        logger.info(_('Logistics plugin enabled'))
        return True

    def register_routes(self):
        """注册 Flask 路由"""
        from .routes import logistics_bp
        return [logistics_bp]

    def on_disable(self, registry):
        logger.info(_('Logistics plugin disabled'))
        return True

    def on_uninstall(self, registry):
        """Uninstall cleanup: drop logistics schema and all its data"""
        from .models import get_logistics_db
        conn = get_logistics_db()
        conn.execute("DROP SCHEMA IF EXISTS logistics CASCADE")
        conn.commit()
        logger.info(_('Logistics plugin uninstalled — schema dropped'))
        return True

    # ── 对外接口 ──

    def get_kdniao_config(self):
        """从插件配置读取快递鸟商户ID和API Key（环境变量可覆盖）"""
        import os
        eid = os.environ.get('KDNIAO_EBUSINESS_ID', '').strip()
        api_key = os.environ.get('KDNIAO_API_KEY', '').strip()
        if not eid:
            eid = self.get_config_value('kdniao_eid', '').strip()
        if not api_key:
            api_key = self.get_config_value('kdniao_api_key', '').strip()
        return eid, api_key

    def query_track(self, shipper_code, logistic_code, order_code='', customer_name='', eid='', api_key=''):
        from .services import query_track as _q
        if not eid or not api_key:
            eid, api_key = self.get_kdniao_config()
        return _q(shipper_code, logistic_code, order_code, customer_name, eid, api_key)

    def get_shipping_status_text(self, shipping_status):
        from .services import get_shipping_status_text as _g
        return _g(shipping_status)

    def get_dashboard_stats(self):
        """Dashboard stats (§2.3): query count and success rate from logistics schema"""
        stats = {'total_queries': 0, 'success_rate': 0}
        try:
            from .models import get_logistics_db
            conn = get_logistics_db()
            total = conn.execute('SELECT COUNT(*) AS c FROM logistics_queries').fetchone()
            stats['total_queries'] = total['c'] if total else 0
            if stats['total_queries'] > 0:
                success = conn.execute(
                    "SELECT COUNT(*) AS c FROM logistics_queries WHERE success=1"
                ).fetchone()
                stats['success_rate'] = round(success['c'] / stats['total_queries'] * 100, 1)
        except Exception as e:
            logger.warning(f'get_dashboard_stats failed: {e}')
        return stats
