#!/usr/bin/env python3
"""Stripe Payment Gateway — Subscription checkout + Webhook.

Uses providers.payment.stripe.StripePaymentGateway.
Environment: STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET, NOTIFY_BASE
"""
import os, json
from flask import request, jsonify

NOTIFY_BASE = os.environ.get('NOTIFY_BASE', '')
NOTIFY_URL = NOTIFY_BASE + '/subscription/notify/stripe'
RETURN_URL = NOTIFY_BASE + '/subscribe/success'


def _get_gateway():
    from providers.payment.stripe import StripePaymentGateway
    return StripePaymentGateway()


def _is_stub():
    return not os.environ.get('STRIPE_SECRET_KEY', '').strip()


def create_checkout_session(order_no: str, description: str, amount_cents: int,
                            customer_email: str = '') -> dict:
    """Create a Stripe Checkout Session for subscription payment.

    Args:
        order_no: Internal order number
        description: Description for the payment
        amount_cents: Amount in cents (USD)
        customer_email: Optional customer email for pre-filled checkout

    Returns:
        dict with checkout_url, session_id, or error
    """
    gw = _get_gateway()
    if not gw.is_configured():
        return {'stub': True, 'stripe_public_key': '',
                'checkout_url': '', 'error': 'Stripe not configured'}

    try:
        import stripe as stripe_lib
        stripe_lib.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
        session = stripe_lib.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': description},
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=RETURN_URL + '?session_id={CHECKOUT_SESSION_ID}&order_no=' + order_no,
            cancel_url=NOTIFY_BASE + '/subscribe?canceled=1',
            customer_email=customer_email or None,
            metadata={'order_no': order_no},
        )
        return {
            'stub': False,
            'provider': 'stripe',
            'checkout_url': session.url,
            'session_id': session.id,
            'stripe_public_key': os.environ.get('STRIPE_PUBLISHABLE_KEY', ''),
        }
    except Exception as e:
        return {'stub': True, 'error': str(e), 'checkout_url': ''}


def handle_webhook() -> tuple:
    """Handle Stripe webhook event.

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
            payment_method='stripe',
            channel_order_id=transaction_id,
            notify_id=result.get('raw', {}).get('id', ''),
            notify_raw=json.dumps(result.get('raw', {})),
        )

    return jsonify({'status': 'ok'}), 200


def refund_order(trade_no: str, amount_fen: int = 0):
    """Stripe 退款

    Args:
        trade_no: Stripe PaymentIntent ID 或 Checkout Session ID
        amount_fen: 退款金额（cents）

    Returns:
        {'success': bool, 'refund_no': str, 'error': str}
    """
    if _is_stub():
        print('[Stripe Refund] Stub mode')
        return {'success': True, 'refund_no': f'STRIPEREFUND{trade_no}', 'error': ''}

    try:
        import stripe
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')

        pi_id = trade_no
        if trade_no.startswith('cs_'):
            session = stripe.checkout.Session.retrieve(trade_no)
            pi_id = session.payment_intent or trade_no

        refund_params = {'payment_intent': pi_id}
        if amount_fen > 0:
            refund_params['amount'] = amount_fen

        refund = stripe.Refund.create(**refund_params)
        return {'success': True, 'refund_no': refund.id, 'error': ''}

    except Exception as e:
        print(f'[Stripe Refund] Error: {e}')
        return {'success': False, 'refund_no': '', 'error': str(e)}
