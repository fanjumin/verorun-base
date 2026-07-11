#!/usr/bin/env python3
"""
Logistics Plugin — 物流配送查询插件（完全独立）
================================================
快递鸟物流轨迹查询，支持 600+ 快递公司。
- 独立数据库：logistics.db（查询日志）
- 配置通过主库 system_config 只读
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class LogisticsPlugin(BasePlugin):
    name = 'logistics'
    version = '0.1.0'
    description = 'Logistics Express — shipment tracking via Kdniao API with 600+ carriers'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立 logistics.db"""
        from .models import init_logistics_db
        init_logistics_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库（幂等）"""
        from .models import init_logistics_db
        init_logistics_db()
        print('[LogisticsPlugin] ✅ 物流配送插件已启用 (logistics.db)')
        return True

    def register_routes(self):
        """注册 Flask 路由"""
        from .routes import logistics_bp
        return [logistics_bp]

    def on_disable(self, registry):
        print('[LogisticsPlugin] ⚠️  物流配送插件已禁用')
        return True

    # ── 对外接口 ──

    def query_track(self, shipper_code, logistic_code, order_code='', customer_name='', eid='', api_key=''):
        from .services import query_track as _q
        return _q(shipper_code, logistic_code, order_code, customer_name, eid, api_key)

    def get_shipping_status_text(self, shipping_status):
        from .services import get_shipping_status_text as _g
        return _g(shipping_status)
