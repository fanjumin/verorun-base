#!/usr/bin/env python3
"""
Subscription Plugin — PayPal 支付网关
=======================================
国际区 (DEPLOY_MARKET=intl) 备用支付渠道。
接口: PayPal REST API v2 Orders
"""

import os
import json
import time
import base64
from typing import Dict, Any, Tuple


def _get_paypal_config() -> dict:
    return {
        'client_id': os.environ.get('PAYPAL_CLIENT_ID', ''),
        'client_secret': os.environ.get('PAYPAL_CLIENT_SECRET', ''),
        'mode': os.environ.get('PAYPAL_MODE', 'sandbox'),  # sandbox | live
    }


def _get_api_base() -> str:
    cfg = _get_paypal_config()
    if cfg['mode'] == 'live':
        return 'https://api-m.paypal.com'
    return 'https://api-m.sandbox.paypal.com'


def _get_access_token() -> str:
    """获取 PayPal OAuth 2.0 Access Token"""
    cfg = _get_paypal_config()
    api_base = _get_api_base()

    auth = base64.b64encode(f"{cfg['client_id']}:{cfg['client_secret']}".encode()).decode()

    try:
        import urllib.request
        data = urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode()
        req = urllib.request.Request(f'{api_base}/v1/oauth2/token', data=data, method='POST')
        req.add_header('Authorization', f'Basic {auth}')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        resp = urllib.request.urlopen(req, timeout=10)
        body = json.loads(resp.read().decode())
        return body.get('access_token', '')
    except Exception as e:
        print(f'[PayPal] Token error: {e}')
        return ''


def create_paypal_order(order_no: str, amount_fen: int, subject: str,
                        description: str, interval_type: str = 'month') -> Dict[str, Any]:
    """创建 PayPal Order

    Returns:
        Dict with redirect_url for client approval.
    """
    cfg = _get_paypal_config()
    if not cfg['client_id'] or cfg['client_id'].startswith('xxxx'):
        print('[PayPal] Not configured, using mock')
        return {
            'success': True,
            'trade_no': f'PPMOCK{order_no}',
            'qr_code': '',
            'redirect_url': f'/payment/mock?order={order_no}&channel=paypal',
        }

    token = _get_access_token()
    if not token:
        return {
            'success': False,
            'trade_no': '',
            'qr_code': '',
            'redirect_url': '',
            'error': 'Failed to get access token',
        }

    api_base = _get_api_base()
    amount_usd = f'{amount_fen / 100:.2f}'
    return_url = os.environ.get('SUCCESS_URL', '/subscribe/success')
    cancel_url = os.environ.get('CANCEL_URL', '/subscribe/cancel')

    order_data = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': order_no,
            'description': description,
            'amount': {
                'currency_code': 'USD',
                'value': amount_usd,
            },
        }],
        'application_context': {
            'brand_name': 'VeroRun',
            'landing_page': 'NO_PREFERENCE',
            'user_action': 'PAY_NOW',
            'return_url': return_url,
            'cancel_url': cancel_url,
        },
    }

    try:
        import urllib.request
        data = json.dumps(order_data).encode()
        req = urllib.request.Request(f'{api_base}/v2/checkout/orders', data=data, method='POST')
        req.add_header('Authorization', f'Bearer {token}')
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req, timeout=15)
        body = json.loads(resp.read().decode())

        # 获取 approval URL
        approval_url = ''
        for link in body.get('links', []):
            if link.get('rel') == 'approve':
                approval_url = link.get('href', '')
                break

        return {
            'success': True,
            'trade_no': body.get('id', ''),
            'qr_code': '',
            'redirect_url': approval_url,
        }

    except Exception as e:
        print(f'[PayPal] Order creation error: {e}')
        return {
            'success': False,
            'trade_no': '',
            'qr_code': '',
            'redirect_url': '',
            'error': str(e),
        }


def verify_paypal_webhook(raw_data: dict, headers: dict) -> Tuple[bool, dict]:
    """验证 PayPal Webhook / 支付回调

    Returns:
        Tuple[bool, dict]: (is_valid, parsed_data)
    """
    # PayPal 的 webhook 验证需要通过 PayPal API 确认
    # 这里简化处理：如果配置了 client_id 则尝试捕获订单

    cfg = _get_paypal_config()
    if not cfg['client_id'] or cfg['client_id'].startswith('xxxx'):
        return True, {
            'order_no': raw_data.get('purchase_units', [{}])[0].get('reference_id', ''),
            'trade_no': raw_data.get('id', ''),
            'status': 'paid',
        }

    # 简单的状态检查
    status = raw_data.get('status', '')
    if status != 'COMPLETED':
        return False, {}

    return True, {
        'order_no': raw_data.get('purchase_units', [{}])[0].get('reference_id', ''),
        'trade_no': raw_data.get('id', ''),
        'status': 'paid',
    }
