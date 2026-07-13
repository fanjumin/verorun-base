#!/usr/bin/env python3
"""
支付宝支付网关 — Subscription
支持：电脑网站支付（一次性）、周期扣款签约 + 自动扣款

配置优先级：
1. system_config 表（alipay_app_id / payment.notify_base）
2. 环境变量（ALIPAY_APP_ID / NOTIFY_BASE）
3. deploy.url() 动态生成（基于 DEPLOY_DOMAIN）
"""
import os, sys, json, time, secrets, base64, urllib.parse
from datetime import datetime
from flask import request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from models import DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERTS_DIR = os.path.join(BASE_DIR, '..', '..', '..', 'certs')

# ── 支付宝配置（从 system_config 读取） ──
def _get_alipay_db_config():
    """从 system_config 读取支付宝网关配置"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT key, value FROM system_config WHERE key IN "
            "('alipay_app_id', 'alipay_private_key', 'alipay_public_key', 'payment.notify_base')"
        ).fetchall()
        conn.close()
        return {r['key']: r['value'] for r in rows}
    except Exception:
        return {}

_alipay_cfg = _get_alipay_db_config()
ALIPAY_APP_ID = _alipay_cfg.get('alipay_app_id', '').strip() or os.environ.get('ALIPAY_APP_ID', '')
ALIPAY_GATEWAY = 'https://openapi.alipay.com/gateway.do'

NOTIFY_BASE = _alipay_cfg.get('payment.notify_base', '').strip() or os.environ.get('NOTIFY_BASE', deploy.url())
NOTIFY_URL = NOTIFY_BASE + '/subscription/notify/alipay'
RETURN_URL = NOTIFY_BASE + '/subscribe/success'


def _is_stub():
    return not ALIPAY_APP_ID


def _ensure_pem_format(key_str: str, key_type: str = 'PRIVATE KEY') -> str:
    """确保密钥字符串有正确的 PEM 头尾标记。"""
    key_str = key_str.strip()
    begin_marker = f'-----BEGIN {key_type}-----'
    end_marker = f'-----END {key_type}-----'
    if not key_str.startswith('-----BEGIN '):
        key_str = begin_marker + '\n' + key_str + '\n' + end_marker
    return key_str


def _get_private_key():
    """读取商户私钥：优先 DB → 文件"""
    cfg = _get_alipay_db_config()
    private_key = cfg.get('alipay_private_key', '').strip()
    if private_key:
        return _ensure_pem_format(private_key, 'PRIVATE KEY')
    key_path = os.path.join(CERTS_DIR, 'alipay_private_key.pem')
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read()
    return None


def _get_alipay_public_key():
    """读取支付宝公钥：优先 DB → 文件"""
    cfg = _get_alipay_db_config()
    public_key = cfg.get('alipay_public_key', '').strip()
    if public_key:
        return _ensure_pem_format(public_key, 'PUBLIC KEY')
    key_path = os.path.join(CERTS_DIR, 'alipay_public_key.pem')
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read()
    return None


def _sign(params, private_key):
    """RSA2 签名"""
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    # 按 key 排序，拼接
    sorted_keys = sorted(params.keys())
    sign_str = '&'.join([f'{k}={params[k]}' for k in sorted_keys])

    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    sig = key.sign(
        sign_str.encode('utf-8'),
        asym_padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode()


def _verify_sign(data, sign, alipay_public_key_str):
    """验证支付宝回调签名"""
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa
    sorted_keys = sorted([k for k in data.keys() if k != 'sign' and k != 'sign_type'])
    sign_str = '&'.join([f'{k}={data[k]}' for k in sorted_keys])

    public_key = serialization.load_pem_public_key(alipay_public_key_str.encode())
    try:
        public_key.verify(
            base64.b64decode(sign),
            sign_str.encode('utf-8'),
            asym_padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


# ============================================================
# 一次性支付（电脑网站支付 / 手机网站支付）
# ============================================================

def call_alipay_page_pay(order_no, description, amount_fen):
    """
    生成支付宝电脑网站支付参数
    返回前端可以直接跳转的 form_html 或 qr_code
    """
    if _is_stub():
        return {'stub': True, 'note': '开发模式 — 支付宝未配置', 'stub_auto_confirm': True}

    private_key = _get_private_key()
    if not private_key:
        return {'stub': True, 'note': '缺少支付宝私钥证书'}

    params = {
        'app_id': ALIPAY_APP_ID,
        'method': 'alipay.trade.page.pay',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'notify_url': NOTIFY_URL,
        'return_url': RETURN_URL,
        'biz_content': json.dumps({
            'out_trade_no': order_no,
            'product_code': 'FAST_INSTANT_TRADE_PAY',
            'total_amount': f'{amount_fen/100:.2f}',
            'subject': description,
        }, ensure_ascii=False),
    }
    sign = _sign(params, private_key)
    params['sign'] = sign

    # 生成自动提交的 form HTML
    form_html = '<form id="alipay_submit" name="alipay_submit" action="' + ALIPAY_GATEWAY + '" method="POST" accept-charset="utf-8">'
    for k, v in params.items():
        form_html += f'<input type="hidden" name="{k}" value="{v}"/>'
    form_html += '<input type="submit" value="支付宝支付" style="display:none"></form>'
    form_html += '<script>document.forms["alipay_submit"].submit();</script>'

    # 同时生成 GET URL（更可靠，前端可直接跳转）
    query_parts = []
    for k, v in params.items():
        query_parts.append(urllib.parse.quote(k) + '=' + urllib.parse.quote(str(v)))
    pay_url = ALIPAY_GATEWAY + '?' + '&'.join(query_parts)

    return {
        'stub': False,
        'method': 'alipay',
        'pay_url': pay_url,
        'form_html': form_html,
        'order_no': order_no,
        'amount': f'¥{amount_fen/100:.2f}',
    }


# ============================================================
# 周期扣款（签约 + 自动扣款）
# ============================================================

def create_cycle_sign_request(user_id, plan_key, period, price_fen):
    """
    创建支付宝周期扣款签约请求
    返回签约 URL，用户跳转到支付宝完成签约
    """
    if _is_stub():
        return {'stub': True, 'sign_url': None, 'agreement_no': 'STUB_' + secrets.token_hex(8).upper()}

    private_key = _get_private_key()
    if not private_key:
        return {'stub': True, 'error': '缺少支付宝私钥证书'}

    external_agreement_no = 'AG' + datetime.now().strftime('%Y%m%d%H%M%S') + secrets.token_hex(4).upper()

    params = {
        'app_id': ALIPAY_APP_ID,
        'method': 'alipay.user.agreement.page.sign',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'notify_url': NOTIFY_URL,
        'return_url': RETURN_URL,
        'biz_content': json.dumps({
            'product_code': 'CYCLE_PAY_AUTH_P',
            'sign_scene': 'INDUSTRY|ENERGY',
            'external_agreement_no': external_agreement_no,
            'access_params': {'channel': 'ALIPAYAPP'},
            'period_rule_params': {
                'period_type': 'DAY',
                'period': 30 if period == 'month' else 365,
                'execute_time': datetime.now().strftime('%Y-%m-%d'),
                'single_amount': price_fen,
            },
        }, ensure_ascii=False),
    }
    sign = _sign(params, private_key)
    params['sign'] = sign

    # 生成签约链接（用户跳转到支付宝签约页）
    sign_url = ALIPAY_GATEWAY + '?' + '&'.join([f'{k}={params[k]}' for k in params])

    return {
        'stub': False,
        'sign_url': sign_url,
        'agreement_no': external_agreement_no,
    }


def execute_charge(agreement_id, order_no, amount_fen, subject=None):
    """
    执行支付宝周期扣款（协议扣款）
    返回 (success, fail_reason)
    """
    if _is_stub():
        return True, None

    private_key = _get_private_key()
    if not private_key:
        return False, '缺少支付宝私钥'

    params = {
        'app_id': ALIPAY_APP_ID,
        'method': 'alipay.trade.pay',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'biz_content': json.dumps({
            'out_trade_no': order_no,
            'total_amount': f'{amount_fen/100:.2f}',
            'subject': subject,
            'auth_no': agreement_id,
            'scene': 'INDUSTRY|ENERGY',
        }, ensure_ascii=False),
    }
    sign = _sign(params, private_key)
    params['sign'] = sign

    # 发送请求
    import urllib.request
    data = '&'.join([f'{k}={urllib.parse.quote(str(params[k]))}' for k in params])
    req = urllib.request.Request(ALIPAY_GATEWAY, data=data.encode('utf-8'))
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        # 解析支付宝响应
        response = result.get('alipay_trade_pay_response', {})
        if response.get('code') == '10000':
            return True, None
        elif response.get('code') in ('10003', '20000'):
            # 处理中/未知 → 需要主动查询
            return _poll_charge_result(order_no)
        else:
            return False, response.get('sub_msg', '扣款失败')
    except Exception as e:
        return False, str(e)


def _poll_charge_result(order_no, max_retries=5):
    """主动查询支付结果"""
    import urllib.request, urllib.parse
    private_key = _get_private_key()
    if not private_key:
        return False, '缺少支付宝私钥'

    for i in range(max_retries):
        time.sleep(3)
        params = {
            'app_id': ALIPAY_APP_ID,
            'method': 'alipay.trade.query',
            'format': 'JSON',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'biz_content': json.dumps({'out_trade_no': order_no}, ensure_ascii=False),
        }
        sign = _sign(params, private_key)
        params['sign'] = sign

        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(ALIPAY_GATEWAY, data=data)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read())
            query_resp = result.get('alipay_trade_query_response', {})
            if query_resp.get('trade_status') == 'TRADE_SUCCESS':
                return True, None
            elif query_resp.get('trade_status') == 'TRADE_CLOSED':
                return False, '交易关闭'
        except Exception:
            continue
    return False, '查询超时'


def unsign_agreement(agreement_id):
    """
    解约支付宝免密协议
    """
    if _is_stub():
        return True

    private_key = _get_private_key()
    if not private_key:
        return False

    params = {
        'app_id': ALIPAY_APP_ID,
        'method': 'alipay.user.agreement.unsign',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'biz_content': json.dumps({
            'agreement_id': agreement_id,
        }, ensure_ascii=False),
    }
    sign = _sign(params, private_key)
    params['sign'] = sign

    import urllib.request, urllib.parse
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(ALIPAY_GATEWAY, data=data)
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


# ============================================================
# 退款
# ============================================================

def refund_order(order_no: str, amount_fen: int, refund_no: str = None):
    """支付宝退款 — alipay.trade.refund

    Args:
        order_no: 原订单 out_trade_no
        amount_fen: 退款金额（分）
        refund_no: 退款请求号

    Returns:
        {'success': bool, 'refund_no': str, 'error': str}
    """
    import uuid
    if _is_stub():
        print('[Alipay Refund] Stub mode')
        return {'success': True, 'refund_no': f'ALIREFUND{order_no}', 'error': ''}

    private_key = _get_private_key()
    if not private_key:
        return {'success': False, 'refund_no': '', 'error': 'Alipay private key not configured'}

    amount_yuan = f'{amount_fen / 100:.2f}'
    refund_no = refund_no or f'REF{int(time.time())}{uuid.uuid4().hex[:8].upper()}'

    params = {
        'app_id': ALIPAY_APP_ID,
        'method': 'alipay.trade.refund',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'biz_content': json.dumps({
            'out_trade_no': order_no,
            'refund_amount': amount_yuan,
            'out_request_no': refund_no,
        }, ensure_ascii=False),
    }
    params['sign'] = _sign(params, private_key)

    try:
        import urllib.request, urllib.parse
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(ALIPAY_GATEWAY, data=data)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        resp = urllib.request.urlopen(req, timeout=10)
        body = resp.read().decode()
        result = json.loads(body)
        response = result.get('alipay_trade_refund_response', {})

        if response.get('code') == '10000':
            return {'success': True, 'refund_no': refund_no, 'error': ''}

        err_msg = response.get('sub_msg', response.get('msg', 'unknown'))
        print(f'[Alipay Refund] Failed: {err_msg}')
        return {'success': False, 'refund_no': '', 'error': err_msg}
    except Exception as e:
        print(f'[Alipay Refund] Error: {e}')
        return {'success': False, 'refund_no': '', 'error': str(e)}


# ============================================================
# 回调处理
# ============================================================

def handle_notify():
    """处理支付宝异步通知"""
    data = request.form.to_dict()
    sign = data.pop('sign', '')
    sign_type = data.pop('sign_type', '')

    # 验签
    pub_key = _get_alipay_public_key()
    if pub_key and not _verify_sign(data, sign, pub_key):
        return 'failure'

    trade_status = data.get('trade_status', '')
    if trade_status != 'TRADE_SUCCESS':
        return 'failure'

    order_no = data.get('out_trade_no', '')
    trade_no = data.get('trade_no', '')       # 支付宝交易号
    notify_id = data.get('notify_id', '')     # 通知ID（幂等）

    if order_no:
        from .. import _fulfill_order
        _fulfill_order(order_no, 'alipay', trade_no, notify_id, json.dumps(data))
        return 'success'

    return 'failure'
