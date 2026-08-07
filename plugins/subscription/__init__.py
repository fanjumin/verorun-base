#!/usr/bin/env python3
"""
Subscription Plugin — 统一按需订阅管理
=========================================
按 Feature/SKU 独立订阅，废弃套餐制。
支持双环境支付路由：
  - verorun.cn  → Alipay / WeChat Pay
  - verorun.com → Stripe / PayPal

使用方式:
    from plugins.subscription.services import has_subscription, SubscriptionService
    from plugins.subscription.routes import sub_bp
"""

from plugin_manager.base import BasePlugin


class SubscriptionPlugin(BasePlugin):
    name = 'subscription'
    version = '1.0.0'
    description = 'Pay-as-you-go subscription marketplace — per-item billing with dual-environment payments'
    author = 'VeroRun'

    # L-04: 配置 Schema（与 plugin.json settings_schema 对齐）
    config_schema = {
        'trial_days': {'type': 'integer', 'default': 0, 'minimum': 0},
        'grace_days': {'type': 'integer', 'default': 3, 'minimum': 0},
        'auto_renew_default': {'type': 'boolean', 'default': True},
    }

    def on_install(self, registry):
        """安装时创建独立数据库表 + 种子 SKU 目录"""
        from .models import init_tables, seed_default_items
        try:
            init_tables()
            seed_default_items()
            print('[Subscription] DB tables created and seeded')
        except Exception as e:
            print(f'[Subscription] DB init error: {e}')
            return False
        return True

    def on_enable(self, registry):
        """启用时: 确保表存在 + 种子 + 初始化 i18n"""
        from .models import init_tables, seed_default_items
        init_tables()
        seed_default_items()

        # 初始化插件 i18n
        from . import routes as _routes
        from . import services as _services
        _routes.init_i18n(self.t)
        _services.init_i18n(self.t)
        print('[Subscription] Plugin i18n initialized')

        return True

    def register_routes(self):
        """注册订阅 Blueprint"""
        from .routes import sub_bp
        return [sub_bp]

    def register_jobs(self):
        """注册 APScheduler 定时任务"""
        from .scheduler import SUBSCRIPTION_JOBS
        return SUBSCRIPTION_JOBS

    def on_disable(self, registry):
        print('[Subscription] Disabled')
        return True

    def on_uninstall(self, registry):
        """卸载时清理插件独立 schema（H-05）

        仅删除 subscription schema 中的插件表，不动主库公共数据。
        返回 False 表示卸载失败，PluginManager 将中止卸载。
        """
        from plugins._base.db import get_raw_connection, PgConnection
        try:
            conn = PgConnection(get_raw_connection())
            try:
                conn.execute("DROP SCHEMA IF EXISTS subscription CASCADE")
                conn.commit()
                print('[Subscription] Schema dropped')
            finally:
                conn.close()
        except Exception as e:
            print(f'[Subscription] Uninstall error: {e}')
            return False
        return True
