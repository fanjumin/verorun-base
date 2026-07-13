#!/usr/bin/env python3
"""
Subscription Plugin — Stripe 支付网关
=======================================
国际区 (DEPLOY_MARKET=intl) 默认支付渠道。
接口: Stripe Checkout Session
"""

import os
import json
from typing import Dict, Any, Tuple


def _get_stripe_config() -> dict:
    return {
        'secret_key': os.environ.get('STRIPE_SECRET_KEY', ''),
        'publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY', ''),
        'webhook_secret': os.environ.get('STRIPE_WEBHOOK_SECRET', ''),
    }


def create_stripe_session(order_no: str, amount_fen: int, subject: str,
                          description: str, interval_type: str = 'month') -> Dict[str, Any]:
    """创建 Stripe Checkout Session

    Returns:
        Dict with redirect_url for client redirect.
    """
    cfg = _get_stripe_config()
    sk = cfg['secret_key']

    if not sk or sk.startswith('sk_live_xxx'):
        # 未配置或占位符
        print('[Stripe] Not configured, using mock')
        return {
            'success': True,
            'trade_no': f'STRIPEMOCK{order_no}',
            'qr_code': '',
            'redirect_url': f'/payment/mock?order={order_no}&channel=stripe',
        }

    try:
        import stripe
        stripe.api_key = sk

        # 构建 price name
        interval_str = 'Monthly' if interval_type == 'month' else 'Yearly'

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{subject} ({interval_str})',
                        'description': description,
                    },
                    'unit_amount': amount_fen,  # Stripe 用 smallest currency unit (cents)
                    'recurring': {
                        'interval': interval_type,
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=os.environ.get('SUCCESS_URL', '/subscribe/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=os.environ.get('CANCEL_URL', '/subscribe/cancel'),
            metadata={
                'order_no': order_no,
            },
        )

        return {
            'success': True,
            'trade_no': session.id,
            'qr_code': '',
            'redirect_url': session.url or '',
        }

    except ImportError:
        print('[Stripe] stripe-python not installed, using mock')
        return {
            'success': True,
            'trade_no': f'STRIPEMOCK{order_no}',
            'qr_code': '',
            'redirect_url': f'/payment/mock?order={order_no}&channel=stripe',
        }
    except Exception as e:
        print(f'[Stripe] Error: {e}')
        return {
            'success': False,
            'trade_no': '',
            'qr_code': '',
            'redirect_url': '',
            'error': str(e),
        }


def refund_stripe_session(trade_no: str, amount_fen: int = 0) -> Dict[str, Any]:
    """Stripe 退款

    Args:
        trade_no: Stripe PaymentIntent ID 或 Checkout Session ID
        amount_fen: 退款金额（cents），0 表示全额退款

    Returns:
        {'success': bool, 'refund_no': str, 'error': str}
    """
    cfg = _get_stripe_config()
    sk = cfg['secret_key']

    if not sk or sk.startswith('sk_live_xxx'):
        print('[Stripe Refund] Not configured, using mock')
        return {'success': True, 'refund_no': f'STRIPEREFUND{trade_no}', 'error': ''}

    try:
        import stripe
        stripe.api_key = sk

        # 如果是 Checkout Session ID (cs_xxx)，先获取 PaymentIntent
        pi_id = trade_no
        if trade_no.startswith('cs_'):
            session = stripe.checkout.Session.retrieve(trade_no)
            pi_id = session.payment_intent or trade_no

        refund_params = {'payment_intent': pi_id}
        if amount_fen > 0:
            refund_params['amount'] = amount_fen

        refund = stripe.Refund.create(**refund_params)

        return {'success': True, 'refund_no': refund.id, 'error': ''}

    except ImportError:
        print('[Stripe Refund] stripe-python not installed, using mock')
        return {'success': True, 'refund_no': f'STRIPEREFUND{trade_no}', 'error': ''}
    except Exception as e:
        print(f'[Stripe Refund] Error: {e}')
        return {'success': False, 'refund_no': '', 'error': str(e)}


def verify_stripe_webhook(raw_data: dict, headers: dict) -> Tuple[bool, dict]:
    """验证 Stripe Webhook 事件

    Returns:
        Tuple[bool, dict]: (is_valid, parsed_data)
    """
    cfg = _get_stripe_config()
    webhook_secret = cfg['webhook_secret']

    if not webhook_secret or webhook_secret.startswith('whsec_xxx'):
        # Mock mode
        return True, {
            'order_no': raw_data.get('data', {}).get('object', {}).get('metadata', {}).get('order_no', ''),
            'trade_no': raw_data.get('data', {}).get('object', {}).get('id', ''),
            'status': 'paid',
        }

    try:
        import stripe
        stripe.api_key = cfg['secret_key']

        # 从请求体获取原始 payload（调用方需要传入 payload 字符串）
        payload = raw_data.get('_raw_payload', '')
        sig_header = headers.get('Stripe-Signature', '')

        if not payload or not sig_header:
            return False, {}

        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

        if event.type == 'checkout.session.completed':
            session = event.data.object
            return True, {
                'order_no': session.get('metadata', {}).get('order_no', ''),
                'trade_no': session.get('id', ''),
                'status': 'paid',
            }

        return False, {}

    except ImportError:
        return True, {
            'order_no': raw_data.get('data', {}).get('object', {}).get('metadata', {}).get('order_no', ''),
            'trade_no': raw_data.get('data', {}).get('object', {}).get('id', ''),
            'status': 'paid',
        }
    except Exception as e:
        print(f'[Stripe] Webhook verify error: {e}')
        return False, {}
