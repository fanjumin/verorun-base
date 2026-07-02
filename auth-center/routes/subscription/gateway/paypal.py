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
        return_url=RETURN_URL + '?order_no=' + order_no,
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
