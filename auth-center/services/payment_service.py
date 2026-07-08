#!/usr/bin/env python3
"""
Shop Payment Service — 商城支付服务
商城订单支付逻辑（支付宝/微信均委托 gateway 实现，此处仅封装 shop 专用流程）

配置优先级：
1. system_config 表（alipay_app_id / alipay_private_key / alipay_public_key）
2. 环境变量（ALIPAY_APP_ID / NOTIFY_BASE）
3. 未配置 → 桩模式（stub, 用于开发/测试）
"""

import os, sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _resolve_notify_base():
    """获取通知域名：环境变量 → deploy 配置"""
    notify_base = os.environ.get('NOTIFY_BASE', '')
    if notify_base:
        return notify_base
    try:
        from services.deployment_config import deploy
        return deploy.url()
    except Exception:
        return ''


def create_shop_payment(order_id: str, total_amount: float, subject: str = '商城订单') -> dict:
    """
    为商城订单创建支付宝支付，委托 gateway/alipay.py 处理实际签名通信

    Returns:
        {'success': bool, 'stub': bool, 'pay_url': str, 'order_id': str, ...}
    """
    from routes.subscription.gateway.alipay import call_alipay_page_pay

    amount_fen = int(round(total_amount * 100))
    result = call_alipay_page_pay(order_id, subject, amount_fen)

    if result.get('stub', False):
        return {
            'success': True,
            'stub': True,
            'pay_url': '',
            'order_id': order_id,
            'note': result.get('note', '开发模式 — 支付宝未配置'),
            'stub_auto_confirm': True,
        }

    return {
        'success': True,
        'stub': False,
        'pay_url': result.get('pay_url', ''),
        'form_html': result.get('form_html', ''),
        'gateway': 'https://openapi.alipay.com/gateway.do',
        'order_id': order_id,
        'amount': result.get('amount', f'{amount_fen/100:.2f}'),
        'note': '请使用支付宝完成支付',
    }


def verify_notify(data: dict) -> bool:
    """验证支付宝异步通知签名，委托 gateway/alipay.py"""
    from routes.subscription.gateway.alipay import _get_alipay_public_key, _verify_sign
    pub_key = _get_alipay_public_key()
    if not pub_key:
        return False
    sign = data.pop('sign', '')
    data.pop('sign_type', '')
    return _verify_sign(data, sign, pub_key)


def confirm_shop_order(order_id: str, trade_no: str = '', payment_method: str = 'alipay'):
    """
    确认商城订单已支付
    - 更新 order_items.status = paid
    - 记录支付信息
    - 创建 user_purchases
    """
    from models import get_db
    now = datetime.now().isoformat()
    with get_db() as conn:
        items = conn.execute(
            'SELECT * FROM order_items WHERE order_id=? AND status="pending"',
            (order_id,)
        ).fetchall()
        if not items:
            return False, '订单不存在或已支付'

        for item in items:
            conn.execute(
                '''UPDATE order_items SET status='paid', paid_at=?, payment_method=?,
                   payment_trade_no=? WHERE id=?''',
                (now, payment_method, trade_no, item['id'])
            )
            # 创建购买记录
            existing = conn.execute(
                'SELECT id FROM user_purchases WHERE user_id=? AND product_id=? AND order_id=?',
                (item['user_id'], item['product_id'], order_id)
            ).fetchone()
            if not existing:
                conn.execute(
                    '''INSERT INTO user_purchases (user_id, product_id, order_id,
                       purchase_type, status, created_at)
                       VALUES (?,?,?,'once','active',?)''',
                    (item['user_id'], item['product_id'], order_id, now)
                )
        conn.commit()
    
    # 触发事件：订单支付成功
    try:
        from plugin_manager.event_bus import get_event_bus, EventName
        get_event_bus().emit(EventName.ORDER_PAID, order_id=order_id, trade_no=trade_no,
                             payment_method=payment_method)
    except Exception:
        pass
    
    return True, '支付成功'
