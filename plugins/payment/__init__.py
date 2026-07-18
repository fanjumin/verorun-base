#!/usr/bin/env python3
"""
Payment Gateway Plugin — 支付配置插件（完全独立）
==================================================
- 独立数据库：data/payment.db（payment_logs + payment_configs）
- 独立路由：/admin/payment/configs/*（替代主库 /user/config）
- 支持：支付宝、微信支付、Stripe、PayPal
- 市场自动检测：CN 显示支付宝/微信，INTL 显示 Stripe/PayPal
"""
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
        print(_'[PaymentPlugin] ✅ Payment plugin enabled (standalone database)')
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
        print(_'[PaymentPlugin] ⚠️ Payment plugin disabled')
        return True

    # ── 对外接口 ──

    def create_shop_payment(self, order_id, total_amount, subject=_'Mall order'):
        from .services import create_shop_payment as _c
        return _c(order_id, total_amount, subject)

    def confirm_shop_order(self, order_id):
        from .services import confirm_shop_order as _co
        return _co(order_id)

    def verify_notify(self, data):
        from .services import verify_notify as _v
        return _v(data)
