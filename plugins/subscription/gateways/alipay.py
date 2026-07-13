#!/usr/bin/env python3
"""
Subscription Plugin — 支付宝支付网关
=======================================
中国区 (DEPLOY_MARKET=cn) 默认支付渠道。
接口: alipay.trade.precreate (扫码支付)
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Tuple


def _get_alipay_config() -> dict:
    """从 system_config 或环境变量获取支付宝配置"""
    cfg = {
        'app_id': os.environ.get('ALIPAY_APP_ID', ''),
        'private_key': os.environ.get('ALIPAY_PRIVATE_KEY', ''),
        'public_key': os.environ.get('ALIPAY_PUBLIC_KEY', ''),
        'notify_base': os.environ.get('NOTIFY_BASE', ''),
    }

    # 尝试从主库 system_config 表读取
    if not cfg['app_id']:
        try:
            import sqlite3
            db_path = os.environ.get('DB_PATH', '')
            if db_path and os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT key, value FROM system_config WHERE key IN "
                    "('alipay_app_id', 'alipay_private_key', 'alipay_public_key', 'payment.notify_base')"
                ).fetchall()
                conn.close()
                for r in rows:
                    k = r['key']
                    if k == 'alipay_app_id':
                        cfg['app_id'] = r['value']
                    elif k == 'alipay_private_key':
                        cfg['private_key'] = r['value']
                    elif k == 'alipay_public_key':
                        cfg['public_key'] = r['value']
                    elif k == 'payment.notify_base':
                        cfg['notify_base'] = r['value']
        except Exception:
            pass

    return cfg


def _ensure_pem(key_str: str, key_type: str = 'PRIVATE KEY') -> str:
    """确保密钥为 PEM 格式"""
    if not key_str:
        return ''
    if '-----BEGIN' in key_str:
        return key_str
    lines = [key_str[i:i+64] for i in range(0, len(key_str), 64)]
    return f'-----BEGIN {key_type}-----\n' + '\n'.join(lines) + f'\n-----END {key_type}-----\n'


def _sign(params: dict, private_key: str) -> str:
    """支付宝 RSA2 签名"""
    sorted_keys = sorted(k for k in params if params[k] != '' and k != 'sign' and k != 'sign_type')
    sign_str = '&'.join(f'{k}={params[k]}' for k in sorted_keys)
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        import base64
        key_pem = _ensure_pem(private_key)
        key = serialization.load_pem_private_key(
            key_pem.encode(), password=None, backend=default_backend())
        signature = key.sign(sign_str.encode(), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode()
    except ImportError:
        import hashlib
        return hashlib.sha256(sign_str.encode()).hexdigest()


def _verify(params: dict, signature: str, public_key: str) -> bool:
    """验证支付宝回调签名"""
    sorted_keys = sorted(k for k in params if k != 'sign' and k != 'sign_type')
    sign_str = '&'.join(f'{k}={params[k]}' for k in sorted_keys)
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        import base64
        key_pem = _ensure_pem(public_key, 'PUBLIC KEY')
        key = serialization.load_pem_public_key(key_pem.encode(), backend=default_backend())
        key.verify(base64.b64decode(signature), sign_str.encode(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def create_alipay_order(order_no: str, amount_fen: int, subject: str,
                        description: str) -> Dict[str, Any]:
    """创建支付宝扫码支付订单"""
    cfg = _get_alipay_config()
    app_id = cfg['app_id']

    if not app_id:
        # 未配置，降级到 mock
        print('[Alipay] Not configured, using mock')
        return {
            'success': True,
            'trade_no': f'ALIMOCK{order_no}',
            'qr_code': f'https://mock.qr/alipay/{order_no}',
            'redirect_url': '',
        }

    gateway = 'https://openapi.alipay.com/gateway.do'
    if os.environ.get('ALIPAY_SANDBOX') == 'true':
        gateway = 'https://openapi-sandbox.dl.alipaydev.com/gateway.do'

    notify_base = cfg['notify_base']
    notify_url = f'{notify_base}/api/subscription/notify/alipay' if notify_base else ''

    amount_yuan = f'{amount_fen / 100:.2f}'
    params = {
        'app_id': app_id,
        'method': 'alipay.trade.precreate',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'notify_url': notify_url,
        'biz_content': json.dumps({
            'out_trade_no': order_no,
            'total_amount': amount_yuan,
            'subject': subject,
            'body': description or subject,
            'timeout_express': '30m',
        }, ensure_ascii=False),
    }
    params['sign'] = _sign(params, cfg['private_key'])

    try:
        import urllib.request
        import urllib.parse
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(gateway, data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read().decode()
        result = json.loads(body)
        response = result.get('alipay_trade_precreate_response', {})

        if response.get('code') == '10000' and response.get('qr_code'):
            return {
                'success': True,
                'trade_no': response.get('trade_no', ''),
                'qr_code': response['qr_code'],
                'redirect_url': '',
            }

        print(f'[Alipay] Order creation failed: {response.get("sub_msg", response.get("msg"))}')
        return {
            'success': False,
            'trade_no': '',
            'qr_code': '',
            'redirect_url': '',
            'error': response.get('sub_msg', response.get('msg', 'unknown')),
        }
    except Exception as e:
        print(f'[Alipay] Request error: {e}')
        return {
            'success': False,
            'trade_no': '',
            'qr_code': '',
            'redirect_url': '',
            'error': str(e),
        }


def verify_alipay_notify(raw_data: dict, headers: dict) -> Tuple[bool, dict]:
    """验证支付宝回调通知

    Returns:
        Tuple[bool, dict]: (is_valid, {order_no, trade_no, trade_status, total_amount})
    """
    cfg = _get_alipay_config()
    if not cfg['app_id']:
        return True, {
            'order_no': raw_data.get('out_trade_no', ''),
            'trade_no': raw_data.get('trade_no', ''),
            'trade_status': 'TRADE_SUCCESS',
        }

    sign = raw_data.get('sign', '')
    if not sign:
        return False, {}

    is_valid = _verify(raw_data, sign, cfg['public_key'])
    if not is_valid:
        print('[Alipay] Signature verification failed')
        return False, {}

    trade_status = raw_data.get('trade_status', '')
    if trade_status not in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
        print(f'[Alipay] Trade status not success: {trade_status}')
        return False, {}

    return True, {
        'order_no': raw_data.get('out_trade_no', ''),
        'trade_no': raw_data.get('trade_no', ''),
        'trade_status': trade_status,
        'total_amount': raw_data.get('total_amount', '0'),
    }
