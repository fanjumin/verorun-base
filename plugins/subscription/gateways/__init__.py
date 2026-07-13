#!/usr/bin/env python3
"""
Subscription Plugin — 支付网关入口
====================================
根据 DEPLOY_MARKET 自动路由支付渠道:
  - cn   → Alipay / WeChat Pay
  - intl → Stripe / PayPal
"""

import os
from typing import Dict, Any


def create_payment(order_no: str, amount_fen: int, subject: str, description: str,
                   channel: str = 'alipay', interval_type: str = 'month') -> Dict[str, Any]:
    """统一支付入口：根据 channel 路由到对应网关

    Returns:
        Dict with keys: qr_code, redirect_url, trade_no, success
    """
    market = os.environ.get('DEPLOY_MARKET', 'cn')

    if channel == 'alipay' and market == 'cn':
        from .alipay import create_alipay_order
        return create_alipay_order(order_no, amount_fen, subject, description)

    elif channel == 'wechat' and market == 'cn':
        from .wechat import create_wechat_order
        return create_wechat_order(order_no, amount_fen, subject, description, interval_type)

    elif channel == 'stripe':
        from .stripe import create_stripe_session
        return create_stripe_session(order_no, amount_fen, subject, description, interval_type)

    elif channel == 'paypal':
        from .paypal import create_paypal_order
        return create_paypal_order(order_no, amount_fen, subject, description, interval_type)

    else:
        # 降级到 mock
        print(f'[Subscription] Unknown channel {channel}, falling back to mock')
        return {
            'success': True,
            'trade_no': f'MOCK{order_no}',
            'qr_code': '',
            'redirect_url': f'/payment/mock?order={order_no}',
        }


def verify_notify(channel: str, raw_data: dict, headers: dict = None) -> tuple:
    """统一支付回调验证

    Returns:
        Tuple[bool, dict]: (is_valid, parsed_data)
    """
    if channel == 'alipay':
        from .alipay import verify_alipay_notify
        return verify_alipay_notify(raw_data, headers or {})

    elif channel == 'wechat':
        from .wechat import verify_wechat_notify
        return verify_wechat_notify(raw_data, headers or {})

    elif channel == 'stripe':
        from .stripe import verify_stripe_webhook
        return verify_stripe_webhook(raw_data, headers or {})

    elif channel == 'paypal':
        from .paypal import verify_paypal_webhook
        return verify_paypal_webhook(raw_data, headers or {})

    else:
        return False, {'error': f'Unknown channel: {channel}'}


def process_refund(order_no: str, amount_fen: int, channel: str, trade_no: str = '') -> Dict[str, Any]:
    """统一退款入口：根据 channel 路由到对应网关

    Args:
        order_no: 原订单号
        amount_fen: 退款金额（分）
        channel: 支付渠道
        trade_no: 网关交易号

    Returns:
        Dict with keys: success, refund_no, error
    """
    if channel == 'alipay':
        from .alipay import refund_alipay_order
        return refund_alipay_order(order_no, amount_fen)

    elif channel == 'wechat':
        from .wechat import refund_wechat_order
        return refund_wechat_order(order_no, amount_fen)

    elif channel == 'stripe':
        from .stripe import refund_stripe_session
        return refund_stripe_session(trade_no, amount_fen)

    elif channel == 'paypal':
        from .paypal import refund_paypal_order
        return refund_paypal_order(trade_no, amount_fen)

    else:
        return {'success': False, 'refund_no': '', 'error': f'Unknown channel: {channel}'}
