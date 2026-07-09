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


class AnalyticsPlugin(BasePlugin):
    name = 'analytics'
    version = '0.1.0'
    description = 'Analytics Middleware & Dashboard — Server-side Cookieless Analytics'
    author = 'VeroRun'

    _middleware = None
    _processor_thread = None

    def on_install(self, registry):
        """安装时初始化独立数据库表"""
        from analytics.models import init_analytics_tables
        try:
            init_analytics_tables()
            print('[Analytics] Independent DB initialized (data/analytics.db)')
        except Exception as e:
            print(f'[Analytics] DB init warning: {e}')
        return True

    def on_enable(self, registry):
        """启用时: 注册中间件 + 启动聚合线程 + 初始化 i18n"""
        from analytics.middleware import AnalyticsMiddleware
        from analytics.processor import AnalyticsProcessor
        from analytics.dashboard import init_i18n

        # 初始化 i18n
        init_i18n(self.t)

        # 初始化数据库表（幂等）
        from analytics.models import init_analytics_tables
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
        return True

    def register_routes(self):
        """注册 Analytics 仪表盘 Blueprint"""
        from analytics.dashboard import analytics_bp
        return [analytics_bp]

    def on_disable(self, registry):
        """禁用时: 卸载 Blueprint
        注意: Flask 中间件无法热卸载，需重启服务后完全移除
        """
        self._middleware = None
        print('[Analytics] Disabled — restart required to fully remove middleware')
        return True
