#!/usr/bin/env python3
"""
Payment Gateway Plugin — 支付配置插件（完全独立）
==================================================
- 独立 schema：PostgreSQL schema `payment`（payment_logs + payment_configs）
- 独立路由：/admin/payment/configs/*（替代主库 /user/config）
- 支持：支付宝、微信支付、Stripe、PayPal
- 市场自动检测：CN 显示支付宝/微信，INTL 显示 Stripe/PayPal
"""
from i18n import _
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class PaymentPlugin(BasePlugin):
    name = 'payment'
    version = '1.0.0'
    description = 'Payment Gateway — Alipay/WeChat/Stripe/PayPal configuration management'
    author = 'VeroRun'

    def on_install(self, registry):
        self._init_db()
        return True

    def on_enable(self, registry):
        self._init_db()
        print(_('[PaymentPlugin] ✅ Payment plugin enabled (independent PG schema)'))
        return True

    def _init_db(self):
        from .models import init_payment_tables, migrate_from_main_db
        init_payment_tables()
        migrate_from_main_db()

    def register_routes(self):
        """注册插件独立路由"""
        from .routes.admin import payment_admin_bp
        print('[PaymentPlugin] ✅ /admin/payment/* 路由已注册')
        return [payment_admin_bp]

    def on_disable(self, registry):
        print(_('[PaymentPlugin] ⚠️ Payment plugin disabled'))
        return True

    def on_uninstall(self, registry=None):
        """卸载时清理独立 schema，确保零残留（§12.5）

        注意：PluginManager.uninstall() 以无参方式调用本方法，
        故签名必须使用 registry=None 默认值，避免 TypeError 被静默吞掉。
        """
        try:
            from .models import drop_payment_schema
            drop_payment_schema()
            print('[PaymentPlugin] ✅ Schema payment dropped (uninstall)')
        except Exception as e:
            print(f'[PaymentPlugin] ⚠️ on_uninstall cleanup failed: {e}')
        return True

    def get_schema_version(self) -> str:
        """当前 schema 版本（§10.6）"""
        from .models import get_schema_version as _gsv
        return _gsv()

    def migrate(self, from_version: str, to_version: str) -> bool:
        """schema 迁移入口（§10.6），当前无迁移脚本"""
        from .models import migrate as _migrate
        return _migrate(from_version, to_version)

    def get_dashboard_stats(self) -> dict:
        """Dashboard 统计指标（§2.3/§10.5）"""
        try:
            from .models import get_dashboard_stats
            return get_dashboard_stats()
        except Exception as e:
            print(f'[PaymentPlugin] ⚠️ get_dashboard_stats failed: {e}')
            return {}

    # ── 对外接口 ──

    def create_shop_payment(self, order_id, total_amount, subject=_('Mall order')):
        from .services import create_shop_payment as _c
        return _c(order_id, total_amount, subject)

    def confirm_shop_order(self, order_id):
        from .services import confirm_shop_order as _co
        return _co(order_id)

    def verify_notify(self, data):
        from .services import verify_notify as _v
        return _v(data)
