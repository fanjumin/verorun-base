#!/usr/bin/env python3
"""PayPal Payment Gateway — Subscription checkout + Webhook.

Uses providers.payment.paypal.PayPalPaymentGateway.
Environment: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_WEBHOOK_ID, NOTIFY_BASE
"""
import os, json
from flask import request, jsonify

NOTIFY_BASE = os.environ.get('NOTIFY_BASE', '')
NOTIFY_URL = NOTIFY_BASE + '/subscription/notify/paypal'
RETURN_URL = NOTIFY_BASE + '/subscribe/success'


def _get_gateway():
    from providers.payment.paypal import PayPalPaymentGateway
    return PayPalPaymentGateway()


def _is_stub():
    return not os.environ.get('PAYPAL_CLIENT_ID', '').strip()


def create_order(order_no: str, description: str, amount_cents: int) -> dict:
    """Create a PayPal Order for subscription payment.

    Args:
        order_no: Internal order number
        description: Description for the payment
        amount_cents: Amount in cents (USD)

    Returns:
        dict with approval_url, order_id, or error
    """
    gw = _get_gateway()
    if not gw.is_configured():
        return {'stub': True, 'error': 'PayPal not configured', 'approval_url': ''}

    result = gw.create_payment(
        order_no=order_no,
        description=description,
        amount_cents=amount_cents,
        currency='USD',
        return_url=RETURN_URL + '%sorder_no=' + order_no,
    )
    if result.get('success'):
        return {
            'stub': False,
            'provider': 'paypal',
            'approval_url': result.get('payment_url', ''),
            'order_id': result.get('transaction_id', ''),
        }
    return {'stub': True, 'error': result.get('error', 'PayPal order creation failed'),
            'approval_url': ''}


def handle_webhook() -> tuple:
    """Handle PayPal webhook event.

    Returns:
        Flask response (200 for verified, 400 for invalid)
    """
    gw = _get_gateway()
    payload = request.get_data()
    headers = dict(request.headers)

    result = gw.verify_webhook(payload, headers)
    if not result.get('verified'):
        return jsonify({'status': 'ignored', 'error': result.get('error', 'verification failed')}), 400

    order_no = result.get('order_no', '')
    status = result.get('status', '')

    if status == 'paid' and order_no:
        transaction_id = result.get('transaction_id', '')
        from .. import _fulfill_order
        _fulfill_order(
            order_no=order_no,
            payment_method='paypal',
            channel_order_id=transaction_id,
            notify_id=result.get('raw', {}).get('id', ''),
            notify_raw=json.dumps(result.get('raw', {})),
        )

    return jsonify({'status': 'ok'}), 200


def refund_order(trade_no: str, amount_fen: int = 0):
    """PayPal 退款

    Args:
        trade_no: PayPal Order ID
        amount_fen: 退款金额（cents），0 表示全额退款

    Returns:
        {'success': bool, 'refund_no': str, 'error': str}
    """
    if _is_stub():
        print('[PayPal Refund] Stub mode')
        return {'success': True, 'refund_no': f'PPREFUND{trade_no}', 'error': ''}

    try:
        gw = _get_gateway()
        result = gw.refund_payment(trade_no, amount_fen)
        if result.get('success'):
            return {'success': True, 'refund_no': result.get('refund_id', ''), 'error': ''}
        return {'success': False, 'refund_no': '', 'error': result.get('error', 'refund failed')}
    except AttributeError:
        # Provider doesn't have refund_payment, use direct API
        pass

    # Fallback: direct PayPal API
    try:
        import urllib.request, base64

        client_id = os.environ.get('PAYPAL_CLIENT_ID', '')
        client_secret = os.environ.get('PAYPAL_CLIENT_SECRET', '')
        mode = os.environ.get('PAYPAL_MODE', 'sandbox')
        api_base = 'https://api-m.paypal.com' if mode == 'live' else 'https://api-m.sandbox.paypal.com'

        # Get token
        auth = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
        data = urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode()
        req = urllib.request.Request(f'{api_base}/v1/oauth2/token', data=data, method='POST')
        req.add_header('Authorization', f'Basic {auth}')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        resp_body = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        token = resp_body.get('access_token', '')

        if not token:
            return {'success': False, 'refund_no': '', 'error': 'Failed to get access token'}

        # Get order to find capture ID
        req = urllib.request.Request(f'{api_base}/v2/checkout/orders/{trade_no}', method='GET')
        req.add_header('Authorization', f'Bearer {token}')
        order_data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())

        capture_id = ''
        for pu in order_data.get('purchase_units', []):
            for cap in pu.get('payments', {}).get('captures', []):
                capture_id = cap.get('id', '')
                break
            if capture_id:
                break

        if not capture_id:
            return {'success': False, 'refund_no': '', 'error': 'No capture found'}

        # Refund
        refund_data = {}
        if amount_fen > 0:
            refund_data = {
                'amount': {
                    'value': f'{amount_fen / 100:.2f}',
                    'currency_code': 'USD',
                }
            }

        data = json.dumps(refund_data).encode() if refund_data else b''
        req = urllib.request.Request(f'{api_base}/v2/payments/captures/{capture_id}/refund', data=data, method='POST')
        req.add_header('Authorization', f'Bearer {token}')
        req.add_header('Content-Type', 'application/json')
        refund_result = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

        if refund_result.get('status') == 'COMPLETED':
            return {'success': True, 'refund_no': refund_result.get('id', ''), 'error': ''}

        return {'success': False, 'refund_no': '', 'error': refund_result.get('status', 'refund failed')}

    except Exception as e:
        print(f'[PayPal Refund] Error: {e}')
        return {'success': False, 'refund_no': '', 'error': str(e)}
