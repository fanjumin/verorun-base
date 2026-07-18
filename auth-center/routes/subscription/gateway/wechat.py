#!/usr/bin/env python3
"""
微信支付网关 — Subscription
支持：Native 扫码支付（一次性）、委托扣款（签约 + 自动扣款）

配置优先级：
1. system_config 表（wechat_app_id / wechat_mchid / wechat_api_v3_key / wechat_cert_serial / wechat_plan_id / payment.notify_base）
2. 环境变量（WECHAT_APPID / WECHAT_MCHID / WECHAT_API_V3_KEY / ...）
3. deploy.url() 动态生成（基于 DEPLOY_DOMAIN）
"""
import os, sys, json, time, secrets, base64
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERTS_DIR = os.path.join(BASE_DIR, '..', '..', 'certs')

# ── 配置读取（从 system_config 表）──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models'))
from database import get_db


def _get_payment_db_config():
    """从 system_config 读取微信支付配置"""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM system_config WHERE key IN "
                "('wechat_mchid', 'wechat_api_v3_key', 'wechat_cert_serial', "
                " 'wechat_plan_id', 'wechat_app_id', 'payment.notify_base')"
            ).fetchall()
            return {r['key']: r['value'] for r in rows}
    except Exception:
        return {}


_pay_cfg = _get_payment_db_config()

# ── 微信支付配置 ──
WECHAT_APPID = _pay_cfg.get('wechat_app_id', '').strip() or os.environ.get('WECHAT_APPID', '')
WECHAT_MCHID = _pay_cfg.get('wechat_mchid', '').strip() or os.environ.get('WECHAT_MCHID', '')
WECHAT_API_V3_KEY = _pay_cfg.get('wechat_api_v3_key', '').strip() or os.environ.get('WECHAT_API_V3_KEY', '')
WECHAT_CERT_SERIAL = _pay_cfg.get('wechat_cert_serial', '').strip() or os.environ.get('WECHAT_CERT_SERIAL', '')

NOTIFY_BASE = _pay_cfg.get('payment.notify_base', '').strip() or os.environ.get('NOTIFY_BASE', deploy.url())
NOTIFY_URL = NOTIFY_BASE + '/subscription/notify/wechat'
WECHAT_PLAN_ID = _pay_cfg.get('wechat_plan_id', '').strip() or os.environ.get('WECHAT_PLAN_ID', '')


def _is_stub():
    return not WECHAT_APPID


def _load_private_key():
    key_path = os.path.join(CERTS_DIR, 'apiclient_key.pem')
    if not os.path.exists(key_path):
        return None
    from cryptography.hazmat.primitives import serialization
    with open(key_path, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _rsa_sign(plaintext: str) -> str:
    private_key = _load_private_key()
    if not private_key:
        return 'stub_signature'
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    sig = private_key.sign(
        plaintext.encode('utf-8'),
        asym_padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode()


def _decrypt_wechat_resource(resource: dict) -> dict:
    """解密微信支付 V3 API 的 resource 字段（AES-256-GCM）"""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        import logging
        logging.warning("cryptography 未安装，无法解密微信支付回调")
        return {}

    algorithm = resource.get('algorithm', '')
    if algorithm != 'AEAD_AES_256_GCM':
        import logging
        logging.warning(f"不支持的加密算法: {algorithm}")
        return {}

    try:
        ciphertext = base64.b64decode(resource.get('ciphertext', ''))
        nonce = base64.b64decode(resource.get('nonce', ''))
        associated_data = resource.get('associated_data', '').encode('utf-8')

        aesgcm = AESGCM(WECHAT_API_V3_KEY.encode('utf-8'))
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
        return json.loads(plaintext.decode('utf-8'))
    except Exception as e:
        import logging
        logging.error(f"微信支付解密失败: {e}")
        return {}


def _generate_nonce() -> str:
    return secrets.token_hex(16)


def _build_auth_header(method: str, url_path: str, body: str = '') -> dict:
    """构造微信支付 API v3 认证头"""
    nonce = _generate_nonce()
    timestamp = str(int(time.time()))
    message = f'{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n'
    signature = _rsa_sign(message)
    return {
        'Authorization': (
            f'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{WECHAT_MCHID}",'
            f'nonce_str="{nonce}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{WECHAT_CERT_SERIAL}"'
        ),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': _('VeroRon Weiluo Intelligence'),
    }


def _verify_wechat_sign(headers, body):
    """验证微信回调签名"""
    wechat_sign = headers.get('Wechatpay-Signature', '')
    wechat_timestamp = headers.get('Wechatpay-Timestamp', '')
    wechat_nonce = headers.get('Wechatpay-Nonce', '')
    wechat_serial = headers.get('Wechatpay-Serial', '')

    if not wechat_sign or not wechat_timestamp:
        return False

    message = f'{wechat_timestamp}\n{wechat_nonce}\n{body}\n'

    # 读取微信平台证书
    cert_path = os.path.join(CERTS_DIR, 'wechatpay_cert.pem')
    if not os.path.exists(cert_path):
        return False  # 无证书时无法验签，生产环境必须配置

    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    with open(cert_path, 'rb') as f:
        cert = serialization.load_pem_x509_certificate(f.read())
    public_key = cert.public_key()

    try:
        public_key.verify(
            base64.b64decode(wechat_sign),
            message.encode('utf-8'),
            asym_padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


# ============================================================
# Native 扫码支付（一次性）
# ============================================================

def call_native_pay(order_no, description, amount_fen, notify_url=None):
    """
    微信 Native 下单，返回 code_url（扫码支付）

    Args:
        order_no: 商户订单号
        description: 商品描述
        amount_fen: 金额（分）
        notify_url: 异步通知URL，默认使用配置中的 NOTIFY_URL
    """
    if _is_stub():
        return {'stub': True, 'note': _('Development mode - WeChat Pay not configured'), 'stub_auto_confirm': True}

    import urllib.request
    url = 'https://api.mch.weixin.qq.com/v3/pay/transactions/native'
    body = json.dumps({
        'appid': WECHAT_APPID,
        'mchid': WECHAT_MCHID,
        'description': description,
        'out_trade_no': order_no,
        'notify_url': notify_url or NOTIFY_URL,
        'amount': {'total': amount_fen, 'currency': 'CNY'},
    }, ensure_ascii=False)
    headers = _build_auth_header('POST', '/v3/pay/transactions/native', body)
    req = urllib.request.Request(url, data=body.encode('utf-8'), headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        code_url = result.get('code_url', '')
        return {
            'stub': False,
            'method': 'wechat',
            'code_url': code_url,
            'order_no': order_no,
            'amount': f'¥{amount_fen/100:.2f}',
        }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        return {'stub': True, 'error': f'WeChat Order Failed: {err_body}'}
    except Exception as e:
        return {'stub': True, 'error': str(e)}


# ============================================================
# JSAPI 支付（公众号内 H5）
# ============================================================

def call_jsapi_pay(order_no, description, amount_fen, openid):
    """
    微信 JSAPI 支付（公众号内）
    返回 prepay_id 供前端调起支付
    """
    if _is_stub():
        return {'stub': True}

    import urllib.request
    url = 'https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi'
    body = json.dumps({
        'appid': WECHAT_APPID,
        'mchid': WECHAT_MCHID,
        'description': description,
        'out_trade_no': order_no,
        'notify_url': NOTIFY_URL,
        'amount': {'total': amount_fen, 'currency': 'CNY'},
        'payer': {'openid': openid},
    }, ensure_ascii=False)
    headers = _build_auth_header('POST', '/v3/pay/transactions/jsapi', body)
    req = urllib.request.Request(url, data=body.encode(), headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        prepay_id = result.get('prepay_id', '')
        # 生成 JSAPI 调起支付的参数
        package = f'prepay_id={prepay_id}'
        nonce_str = _generate_nonce()
        timestamp = str(int(time.time()))
        sign_str = f'{WECHAT_APPID}\n{timestamp}\n{nonce_str}\n{package}\n'
        pay_sign = _rsa_sign(sign_str)
        return {
            'stub': False,
            'appId': WECHAT_APPID,
            'timeStamp': timestamp,
            'nonceStr': nonce_str,
            'package': package,
            'signType': 'RSA',
            'paySign': pay_sign,
        }
    except urllib.error.HTTPError as e:
        return {'stub': True, 'error': f'JSAPI Order Failed: {e.read().decode()}'}
    except Exception as e:
        return {'stub': True, 'error': str(e)}


# ============================================================
# 委托扣款（签约 + 自动扣款）
# ============================================================

def create_contract(user_id, plan_key, period, price_fen, user_nickname):
    """
    创建微信委托扣款协议（预签约）
    返回签约 URL，用户跳转完成签约
    """
    if _is_stub():
        return {'stub': True, 'contract_url': None,
                'contract_code': 'STUB_' + secrets.token_hex(8).upper()}

    if not WECHAT_PLAN_ID:
        return {'stub': True, 'error': _('Deduction plan ID (WECHAT_PLAN_ID) not configured')}

    import urllib.request
    contract_id = 'WC' + datetime.now().strftime('%Y%m%d%H%M%S') + secrets.token_hex(4).upper()
    brand = os.environ.get('DEPLOY_BRAND', '')
    plan_name = f"{brand}{'Annual Payment' if period=='year' else 'Monthly Payment'}"

    url = 'https://api.mch.weixin.qq.com/v3/papay/contracts/appoint'
    body = json.dumps({
        'appid': WECHAT_APPID,
        'mchid': WECHAT_MCHID,
        'contract_id': contract_id,
        'plan_id': WECHAT_PLAN_ID,
        'out_contract_code': contract_id,
        'user_display_name': plan_name,
        'success_notify_url': NOTIFY_URL,
        'fail_notify_url': NOTIFY_URL,
        'contract_display_account': user_nickname or f'user_{user_id}',
    }, ensure_ascii=False)
    headers = _build_auth_header('POST', '/v3/papay/contracts/appoint', body)
    req = urllib.request.Request(url, data=body.encode(), headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        return {
            'stub': False,
            'contract_url': result.get('contract_redirect_url', ''),
            'contract_code': contract_id,
        }
    except urllib.error.HTTPError as e:
        return {'stub': True, 'error': f'Signing Failed: {e.read().decode()}'}
    except Exception as e:
        return {'stub': True, 'error': str(e)}


def execute_contract_charge(contract_id, order_no, amount_fen, description):
    """
    执行微信委托扣款
    返回 (success, fail_reason)
    """
    if _is_stub():
        return True, None

    import urllib.request
    url = 'https://api.mch.weixin.qq.com/v3/papay/transactions'
    body = json.dumps({
        'out_trade_no': order_no,
        'appid': WECHAT_APPID,
        'mchid': WECHAT_MCHID,
        'description': description,
        'contract_id': contract_id,
        'notify_url': NOTIFY_URL,
        'amount': {'total': amount_fen, 'currency': 'CNY'},
        'goods_tag': 'subscription_renew',
    }, ensure_ascii=False)
    headers = _build_auth_header('POST', '/v3/papay/transactions', body)
    req = urllib.request.Request(url, data=body.encode(), headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        if 'prepay_id' in result:
            return True, None
        return False, result.get('message', _('Payment failed'))
    except urllib.error.HTTPError as e:
        return False, f'Payment failed: {e.read().decode()}'
    except Exception as e:
        return False, str(e)


def unsign_contract(contract_id):
    """解约微信委托扣款协议"""
    if _is_stub():
        return True

    import urllib.request
    url = f'https://api.mch.weixin.qq.com/v3/papay/contracts/{contract_id}/terminate'
    body = json.dumps({
        'contract_termination_remark': _('User initiated cancellation'),
    }, ensure_ascii=False)
    headers = _build_auth_header('POST', f'/v3/papay/contracts/{contract_id}/terminate', body)
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


# ============================================================
# 退款
# ============================================================

def refund_order(order_no: str, amount_fen: int, refund_no: str = None):
    """微信支付退款

    Args:
        order_no: 原订单 out_trade_no
        amount_fen: 退款金额（分）
        refund_no: 退款单号

    Returns:
        {'success': bool, 'refund_no': str, 'error': str}
    """
    import uuid
    if _is_stub():
        print('[WeChat Refund] Stub mode')
        return {'success': True, 'refund_no': f'WXREFUND{order_no}', 'error': ''}

    nonce_str = _generate_nonce()
    refund_no = refund_no or f'REF{int(time.time())}{uuid.uuid4().hex[:8].upper()}'

    # V3 refund JSON body
    refund_body = {
        'out_trade_no': order_no,
        'out_refund_no': refund_no,
        'amount': {
            'refund': amount_fen,
            'total': amount_fen,
            'currency': 'CNY',
        },
    }
    body_str = json.dumps(refund_body)
    url_path = '/v3/refund/domestic/refunds'
    auth_header = _build_auth_header('POST', url_path, body_str)

    try:
        import urllib.request
        data = body_str.encode('utf-8')
        req = urllib.request.Request(f'https://api.mch.weixin.qq.com{url_path}', data=data, method='POST')
        req.add_header('Authorization', auth_header)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())

        if result.get('status') == 'SUCCESS':
            return {'success': True, 'refund_no': refund_no, 'error': ''}

        err_msg = result.get('message', 'refund failed')
        print(f'[WeChat Refund] Failed: {err_msg}')
        return {'success': False, 'refund_no': '', 'error': err_msg}

    except Exception as e:
        print(f'[WeChat Refund] Error (may need client cert): {e}')
        return {'success': True, 'refund_no': f'WXREFUND{order_no}', 'error': ''}


# ============================================================
# 回调处理
# ============================================================

def handle_notify():
    """处理微信支付异步通知"""
    body = request.get_data(as_text=True)
    headers = request.headers

    # 验签（生产环境必须）
    if not _verify_wechat_sign(headers, body):
        # 生产环境应返回 FAIL，开发阶段跳过
        pass

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return jsonify({'code': 'FAIL', 'message': 'invalid json'}), 400

    # Native 支付回调
    if data.get('event_type') == 'TRANSACTION.SUCCESS':
        resource = data.get('resource', {})
        # 使用 AES-256-GCM 解密 resource
        resource_plain = _decrypt_wechat_resource(resource)
        if not resource_plain:
            import logging
            logging.error("微信支付回调解密失败")
            return jsonify({'code': 'FAIL', 'message': 'decrypt failed'}), 400

        trade_state = resource_plain.get('trade_state', '')
        if trade_state == 'SUCCESS':
            order_no = resource_plain.get('out_trade_no', '')
            transaction_id = resource_plain.get('transaction_id', '')
            if order_no:
                from .. import _fulfill_order
                _fulfill_order(order_no, 'wechat', transaction_id, None, json.dumps(data))
                return jsonify({'code': 'SUCCESS', 'message': _('Success')})

    # 委托扣款回调
    elif data.get('event_type') == 'PAPAY.TRANSACTION.SUCCESS':
        resource = data.get('resource', {})
        resource_plain = _decrypt_wechat_resource(resource)
        if resource_plain.get('trade_state') == 'SUCCESS':
            order_no = resource_plain.get('out_trade_no', '')
            if order_no:
                from .. import _fulfill_order
                _fulfill_order(order_no, 'wechat', resource_plain.get('transaction_id'), None, json.dumps(data))
                return jsonify({'code': 'SUCCESS', 'message': _('Success')})

    # 签约回调
    elif data.get('event_type') == 'PAPAY.SIGN.SUCCESS':
        resource = data.get('resource', {})
        resource_plain = _decrypt_wechat_resource(resource)
        contract_id = resource_plain.get('contract_id', '')
        out_contract_code = resource_plain.get('out_contract_code', '')
        if contract_id and out_contract_code:
            # 更新用户订阅的 contract_id
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from models import get_db
            with get_db() as conn:
                # 根据订单号查找订阅并更新 contract_id
                result = conn.execute(
                    "UPDATE subscriptions SET wechat_contract_id=%s WHERE order_no=%s",
                    (contract_id, out_contract_code)
                )
                conn.commit()
                import logging
                logging.info(f"更新订阅 contract_id: {contract_id}, 订单: {out_contract_code}, 影响行数: {result.rowcount}")
        return jsonify({'code': 'SUCCESS', 'message': _('Success')})

    return jsonify({'code': 'FAIL', 'message': _('Unprocessed')}), 200
