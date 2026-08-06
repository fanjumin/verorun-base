#!/usr/bin/env python3
"""
Payment Plugin Services — 支付核心逻辑
=======================================
支付创建/确认/回调验证委托给 auth-center/services/payment_service.py
（真实支付逻辑与 gateway 签名通信位于 auth-center）。

auth-center 目录在模块加载时一次性加入 sys.path（与 ali_api/email/logistics
等插件一致），避免每个调用重复 sys.path.insert。
"""
from i18n import _
import os
import sys

_AUTH_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
if _AUTH_DIR not in sys.path:
    sys.path.insert(0, _AUTH_DIR)


def create_shop_payment(order_id, total_amount, subject=_('Mall order')):
    from services.payment_service import create_shop_payment as _create
    return _create(order_id, total_amount, subject)


def confirm_shop_order(order_id):
    from services.payment_service import confirm_shop_order as _confirm
    return _confirm(order_id)


def verify_notify(data):
    from services.payment_service import verify_notify as _verify
    return _verify(data)
