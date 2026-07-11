#!/usr/bin/env python3
"""
Payment Gateway Plugin — 支付配置插件
======================================
提供支付宝/微信支付的配置管理面板。
支付流程委托给 auth-center/services/payment_service.py。
- 独立数据库：payment.db（交易日志）
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class PaymentPlugin(BasePlugin):
    name = 'payment'
    version = '0.1.0'
    description = 'Payment Gateway — Alipay/WeChat Pay configuration management'
    author = 'VeroRun'

    def on_install(self, registry):
        from .models import init_payment_db
        init_payment_db()
        return True

    def on_enable(self, registry):
        from .models import init_payment_db
        init_payment_db()
        print('[PaymentPlugin] ✅ 支付配置插件已启用 (payment.db)')
        return True

    def register_routes(self):
        return []

    def on_disable(self, registry):
        print('[PaymentPlugin] ⚠️  支付配置插件已禁用')
        return True

    # ── 对外接口 ──

    def create_shop_payment(self, order_id, total_amount, subject='商城订单'):
        from .services import create_shop_payment as _c
        return _c(order_id, total_amount, subject)

    def confirm_shop_order(self, order_id):
        from .services import confirm_shop_order as _co
        return _co(order_id)

    def verify_notify(self, data):
        from .services import verify_notify as _v
        return _v(data)
