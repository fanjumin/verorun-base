#!/usr/bin/env python3
"""
Currency Converter Plugin — 多币种展示插件
============================================
启用后接管系统价格展示层，根据用户偏好自动换算币种显示。
遵循插件标准 v1.1，完全独立于主库。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class CurrencyConverterPlugin(BasePlugin):
    name = 'currency_converter'
    version = '0.1.0'
    description = 'Currency Converter — Multi-currency display with real-time exchange rates'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立数据库"""
        from .models import init_db
        init_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库、加载汇率、配置缓存"""
        from .models import init_db
        init_db()

        # 配置服务层
        from .services import configure, _load_rates_from_db, sync_rates
        import asyncio
        cfg = self.plugin_info.metadata.get('config', {}) if self.plugin_info else {}
        base_currency = cfg.get('base_currency', 'CNY')
        cache_ttl = cfg.get('cache_ttl_minutes', 60) * 60
        configure(base_currency=base_currency, cache_ttl=cache_ttl)

        # 尝试从数据库加载已有汇率
        loaded = _load_rates_from_db()
        if not loaded:
            # 首次启用，尝试同步
            try:
                asyncio.run(sync_rates())
            except Exception as e:
                print(f'[CurrencyConverter] Initial sync failed: {e}, will use defaults')

        print(f'[CurrencyConverter] Plugin enabled (base: {base_currency})')
        return True

    def register_routes(self):
        """注册 Flask 路由"""
        from .routes import currency_bp
        return [currency_bp]

    def register_jobs(self):
        """注册定时同步任务"""
        from .scheduler import sync_exchange_rates
        cfg = self.plugin_info.metadata.get('config', {}) if self.plugin_info else {}
        interval = cfg.get('refresh_interval_minutes', 60)
        return [{
            'id': 'currency_sync_rates',
            'func': sync_exchange_rates,
            'trigger': 'interval',
            'minutes': interval,
            'max_instances': 1,
            'replace_existing': True,
        }]

    def get_event_handlers(self):
        """监听用户登录事件以同步偏好"""
        def _on_user_login(**kwargs):
            pass  # 登录后由前端加载 Cookie 中的偏好
        return {}

    def get_dashboard_stats(self):
        """Dashboard 统计：汇率覆盖数、最新同步时间"""
        try:
            from .models import get_db
            conn = get_db()
            count = conn.execute('SELECT COUNT(*) FROM exchange_rates').fetchone()[0]
            latest = conn.execute(
                'SELECT fetched_at FROM exchange_rates ORDER BY fetched_at DESC LIMIT 1'
            ).fetchone()
            return {
                'currency_rates': count,
                'last_sync': latest['fetched_at'] if latest else 'never',
            }
        except Exception:
            return {'currency_rates': 0, 'last_sync': 'error'}

    def on_disable(self, registry):
        """禁用时清理内存缓存"""
        from .services import _RATE_CACHE, _CACHE_TIME
        _RATE_CACHE.clear()
        _CACHE_TIME = 0
        print('[CurrencyConverter] Plugin disabled, cache cleared')
        return True
