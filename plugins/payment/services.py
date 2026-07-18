#!/usr/bin/env python3
"""
Payment Plugin Services — 支付核心逻辑
=======================================
委托给旧 auth-center/services/payment_service.py。
"""
import os
import sys


def create_shop_payment(order_id, total_amount, subject=_('Mall order')):
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)
    from services.payment_service import create_shop_payment as _create
    return _create(order_id, total_amount, subject)


def confirm_shop_order(order_id):
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)
    from services.payment_service import confirm_shop_order as _confirm
    return _confirm(order_id)


def verify_notify(data):
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)
    from services.payment_service import verify_notify as _verify
    return _verify(data)
