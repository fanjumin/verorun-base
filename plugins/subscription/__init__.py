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

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class SubscriptionPlugin(BasePlugin):
    name = 'subscription'
    version = '1.0.0'
    description = 'Pay-as-you-go subscription marketplace — per-item billing with dual-environment payments'
    author = 'VeroRun'

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
        """启用时: 确保表存在 + 种子 + 初始化 i18n + 注册定时任务"""
        from .models import init_tables, seed_default_items
        init_tables()
        seed_default_items()

        # 初始化插件 i18n
        from . import routes as _routes
        from . import services as _services
        _routes.init_i18n(self.t)
        _services.init_i18n(self.t)
        print('[Subscription] Plugin i18n initialized')

        # 注册定时任务（到期检查 + 自动续费）
        try:
            from .scheduler import seed_subscription_schedules
            seed_subscription_schedules()
            print('[Subscription] Scheduled jobs registered')
        except Exception as e:
            print(f'[Subscription] Scheduler warning: {e}')

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
