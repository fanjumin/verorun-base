#!/usr/bin/env python3
"""
Subscription Module — Blueprint Registration
Admin backend = admin backend | VeroRon = user portal
"""
import os, sys, json, secrets, hashlib, time
from datetime import datetime, timedelta
from contextlib import contextmanager
from flask import Blueprint, request, jsonify, render_template, redirect, make_response, send_file
from i18n import _

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'models'))
from database import get_db

sub_bp = Blueprint('subscription', __name__, url_prefix='/subscription')

def now_iso():
    return datetime.now().isoformat()

# ── Helpers ──
def api_res(data=None, error=None, status=200):
    r = {'success': error is None, 'ts': datetime.now().isoformat()}
    if data is not None: r['data'] = data
    if error: r['error'] = error
    return jsonify(r), (status if error else 200)

def api_err(msg, code=400):
    return api_res(error=msg, status=code)

def _get_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth and auth.startswith('Bearer '):
        return auth[7:]
    return request.cookies.get('sso_token') or request.cookies.get('tm_token') or None

def _require_auth():
    """Verify JWT from Authorization header OR cookie, return user payload."""
    from services.jwt_service import validate_token
    token = _get_token_from_request()
    if not token:
        return None
    return validate_token(token)

def _require_admin():
    """Verify JWT + is_admin, return (payload, None) or (None, error_resp)."""
    from services.jwt_service import validate_token
    token = _get_token_from_request()
    payload = validate_token(token) if token else None
    if not payload:
        return None, api_err(_('Please log in first'), 401)
    if not payload.get('is_admin'):
        return None, api_err(_('Admin Only'), 403)
    return payload, None

def _audit_log(user_id, action, detail='', admin_id=None, sub_id=None):
    ip = request.remote_addr or ''
    with get_db() as conn:
        conn.execute(
            'INSERT INTO subscription_audit_log (user_id, sub_id, action, detail, ip_address, admin_id) VALUES (%s,%s,%s,%s,%s,%s)',
            (user_id, sub_id, action, detail, ip, admin_id))
        conn.commit()

# ── Plan definitions (can be overridden by DB) ──
def get_plan(plan_key):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM subscription_plans WHERE plan_key=%s', (plan_key,)).fetchone()
        if row: return dict(row)
    return None

def get_all_plans(active_only=True):
    with get_db() as conn:
        if active_only:
            rows = conn.execute('SELECT * FROM subscription_plans WHERE is_active=1 ORDER BY sort_order').fetchall()
        else:
            rows = conn.execute('SELECT * FROM subscription_plans ORDER BY sort_order').fetchall()
    return [dict(r) for r in rows]

def get_user_subscription(user_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM subscriptions WHERE user_id=%s', (user_id,)).fetchone()
        if row: return dict(row)
    return None

# ── Generate order_no ──
def new_order_no(prefix='SUB'):
    return prefix + datetime.now().strftime('%Y%m%d%H%M%S') + secrets.token_hex(4).upper()

def new_agreement_no(prefix='AG'):
    return prefix + datetime.now().strftime('%Y%m%d%H%M%S') + secrets.token_hex(4).upper()

# ============================================================
# USER-FACING ROUTES (易站智能)
# ============================================================

@sub_bp.route('/plans', methods=['GET'])
def list_plans():
    """获取所有套餐（用户端，含特性列表）"""
    plans = get_all_plans()
    # 读取每个套餐的特性
    for p in plans:
        try:
            feats = json.loads(p.get('features_json', '[]')) if p.get('features_json') else []
        except:
            feats = []
        p['features'] = feats
    return api_res({'plans': plans})

@sub_bp.route('/plans/features', methods=['GET'])
def list_plan_features():
    """获取所有套餐的特性对比矩阵"""
    plans = get_all_plans()
    # 收集所有唯一的特性名
    all_features = []
    features_map = {}
    for p in plans:
        try:
            feats = json.loads(p.get('features_json', '[]')) if p.get('features_json') else []
        except:
            feats = []
        features_map[p['plan_key']] = feats
        for f in feats:
            if isinstance(f, dict) and f.get('name') and f['name'] not in all_features:
                all_features.append(f['name'])
            elif isinstance(f, str) and f not in all_features:
                all_features.append(f)

    # 构建对比矩阵
    matrix = []
    for feat_name in all_features:
        row = {'feature': feat_name, 'plans': {}}
        for p in plans:
            pk = p['plan_key']
            feats = features_map.get(pk, [])
            has = False
            for f in feats:
                if isinstance(f, dict) and f.get('name') == feat_name:
                    has = f.get('included', True)
                elif isinstance(f, str) and f == feat_name:
                    has = True
            row['plans'][pk] = {'included': has}
        matrix.append(row)

    return api_res({
        'plans': [{'plan_key': p['plan_key'], 'name': p['name'], 'tier': p['tier'],
                    'price_month': p['price_month'], 'price_year': p['price_year'],
                    'sort_order': p['sort_order'], 'features': features_map.get(p['plan_key'], [])}
                   for p in plans],
        'matrix': matrix,
    })

@sub_bp.route('/my', methods=['GET'])
def my_subscription():
    """获取当前用户的订阅状态"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']
    sub = get_user_subscription(uid)
    plan = get_plan(sub['plan_key']) if sub else None

    # 计算剩余天数
    days_remaining = 0
    auto_renew = False
    if sub:
        end = datetime.fromisoformat(sub['current_period_end'])
        days_remaining = max(0, (end - datetime.now()).days)
        auto_renew = bool(sub.get('auto_renew', False))

    # 最近的订单
    recent_orders = []
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM subscription_orders WHERE user_id=%s AND user_deleted=0 ORDER BY created_at DESC LIMIT 5',
            (uid,)).fetchall()
        recent_orders = [dict(r) for r in rows]

    # 下次扣款金额
    next_billing_amount = 0
    next_billing_date = ''
    if sub and plan and auto_renew:
        if sub['period'] == 'year':
            next_billing_amount = plan['price_year']
        else:
            next_billing_amount = plan['price_month']
        next_billing_date = sub.get('current_period_end', '')

    return api_res({
        'active': sub is not None and sub['status'] in ('active', 'trialing'),
        'subscription': dict(sub) if sub else None,
        'plan': plan,
        'days_remaining': days_remaining,
        'auto_renew': auto_renew,
        'next_billing_amount': next_billing_amount,
        'next_billing_date': next_billing_date,
        'recent_orders': recent_orders,
    })

@sub_bp.route('/my/invoices', methods=['GET'])
def my_invoices():
    """获取当前用户的发票记录"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']
    limit = int(request.args.get('limit', 20))

    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM invoices WHERE user_id=%s ORDER BY created_at DESC LIMIT %s',
            (uid, limit)).fetchall()
    return api_res({'invoices': [dict(r) for r in rows]})


@sub_bp.route('/my/invoices/<invoice_no>/download', methods=['GET'])
def download_invoice(invoice_no):
    """下载发票 PDF"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']

    with get_db() as conn:
        inv = conn.execute(
            'SELECT * FROM invoices WHERE invoice_no=%s AND user_id=%s',
            (invoice_no, uid)).fetchone()
        if not inv:
            return api_err(_('Invoice Not Found'), 404)
        inv = dict(inv)

    pdf_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        'data', 'invoices', inv['pdf_path'])

    if os.path.exists(pdf_path):
        return flask.send_file(pdf_path, mimetype='application/pdf',
                               as_attachment=True,
                               download_name=f'{invoice_no}.pdf')
    else:
        # PDF 文件可能未生成（fpdf2 未安装等情况），返回 JSON 数据
        return api_res({
            'invoice_no': inv['invoice_no'],
            'amount': f"¥{inv['amount_yuan']:.2f}",
            'plan_name': inv['plan_name'],
            'date': inv['created_at'],
            'status': inv['status'],
            'note': 'PDF file not available, install fpdf2 to enable PDF generation'
        })

@sub_bp.route('/my/payment-method', methods=['PUT'])
def update_payment_method():
    ""_"Change payment method"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']
    data = request.get_json(force=True) or {}
    method = data.get('payment_method', '')
    market = os.environ.get('DEPLOY_MARKET', 'cn')
    cn_methods = ('wechat', 'alipay')
    intl_methods = ('stripe', 'paypal')
    valid_methods = cn_methods + intl_methods
    if method not in valid_methods:
        return api_err(_(_'Payment_method is invalid'))
    if market == 'cn' and method in intl_methods:
        return api_err(_(_'This payment method is not supported in the current market'))
    if market == 'intl' and method in cn_methods:
        return api_err(_(_'This payment method is not supported in the current market'))

    with get_db() as conn:
        conn.execute(
            'UPDATE subscriptions SET payment_method=%s, updated_at=NOW() WHERE user_id=%s',
            (method, uid))
        conn.commit()
    _audit_log(uid, 'update_payment_method', f_'Switch to {method}')
    return api_res({'message': _'Payment method updated'})

@sub_bp.route('/create', methods=['POST'])
def create_subscription():
    """
    创建新订阅订单
    POST: { plan_key, period, payment_method, coupon%s }
    返回支付参数
    """
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']
    data = request.get_json() or {}

    plan_key = data.get('plan_key', '')
    period = data.get('period', 'month')
    payment_method = data.get('payment_method', 'wechat')
    coupon_code = data.get('coupon', '')

    if period not in ('month', 'quarter', 'semi_annual', 'year'):
        return api_err(_('period must be one of: month/quarter/semi_annual/year'))
    market = os.environ.get('DEPLOY_MARKET', 'cn')
    cn_methods = ('wechat', 'alipay')
    intl_methods = ('stripe', 'paypal')
    valid_methods = cn_methods + intl_methods
    if payment_method not in valid_methods:
        return api_err(_(_'Payment_method is invalid:') + payment_method)
    if market == 'cn' and payment_method in intl_methods:
        return api_err(_(_'This payment method is not supported in the current market'))
    if market == 'intl' and payment_method in cn_methods:
        return api_err(_(_'This payment method is not supported in the current market'))

    plan = get_plan(plan_key)
    if not plan:
        return api_err(_(_'Invalid Package: ') + plan_key)

    period_price_map = {'year': 'price_year', 'semi_annual': 'price_semi_annual', 'quarter': 'price_quarter', 'month': 'price_month'}
    period_label_map = {'year': _'Annual Payment', 'semi_annual': _'Semi-annual payment', 'quarter': _'Quarterly Payment', 'month': _'Monthly payment'}
    amount_fen = plan.get(period_price_map[period], 0) or plan['price_month']
    if amount_fen <= 0:
        return api_err(_('Free plan, no purchase needed'))

    # 检查已有活跃订阅
    existing = get_user_subscription(uid)
    if existing and existing['status'] in ('active', 'trialing'):
        # 已有订阅 → 走升级流程
        return _handle_upgrade(uid, existing, plan, period, payment_method)

    # 生成订单
    order_no = new_order_no()
    desc = f'{plan["name"]}{period_label_map[period]}'

    # 优惠券折扣（走插件引擎）
    discount_fen = 0
    if coupon_code:
        try:
            from plugins.coupons import get_engine
            engine = get_engine()
            if engine:
                result = engine.validate(coupon_code, amount_fen / 100.0,
                                          user_id=uid, plan=plan_key)
                if result.get('valid'):
                    discount_fen = int(result['discount'] * 100)
                    # 记录使用
                    engine.apply_to_order(coupon_code, uid, order_no, amount_fen / 100.0)
        except Exception:
            pass

    final_amount = max(0, amount_fen - discount_fen)

    with get_db() as conn:
        # 创建订单
        conn.execute(
            'INSERT INTO subscription_orders (order_no, user_id, amount_fen, item_type, plan_key, period, payment_method, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
            (order_no, uid, final_amount, 'new', plan_key, period, payment_method, 'pending'))
        conn.commit()

    # 根据支付方式生成支付参数
    pay_params = _generate_pay_params(order_no, desc, final_amount, payment_method)

    return api_res({
        'order_no': order_no,
        'plan': plan,
        'period': period,
        'amount': f'¥{final_amount/100:.2f}',
        'amount_fen': final_amount,
        'discount_fen': discount_fen,
        'pay_params': pay_params,
        'stub': pay_params.get('stub', False),
    }, status=201)


def _handle_upgrade(uid, existing, new_plan, new_period, payment_method):
    """已有订阅时的升级/降级处理"""
    old_plan = get_plan(existing['plan_key'])
    now = datetime.now()
    period_end = datetime.fromisoformat(existing['current_period_end'])
    days_remaining = max(0, (period_end - now).days)
    total_days = 30 if existing['period'] == 'month' else 365

    # 计算剩余价值
    old_price = old_plan['price_year'] if existing['period'] == 'year' else old_plan['price_month']
    new_price = new_plan['price_year'] if new_period == 'year' else new_plan['price_month']
    prorated_credit = old_price * days_remaining // total_days if total_days > 0 else 0

    # 判断升级还是降级
    tier_order = ['free', 'premium', 'pro', 'enterprise']
    old_tier_idx = tier_order.index(old_plan['tier']) if old_plan['tier'] in tier_order else 0
    new_tier_idx = tier_order.index(new_plan['tier']) if new_plan['tier'] in tier_order else 0
    is_upgrade = new_tier_idx > old_tier_idx

    amount_due = max(0, new_price - prorated_credit)

    order_no = new_order_no('UPG' if is_upgrade else 'DNG')
    item_type = 'upgrade' if is_upgrade else 'downgrade'

    with get_db() as conn:
        if is_upgrade:
            # 升级：立即生效，生成差价订单
            conn.execute(
                'INSERT INTO subscription_orders (order_no, user_id, amount_fen, item_type, plan_key, period, payment_method, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (order_no, uid, amount_due, item_type, new_plan['plan_key'], new_period, payment_method, 'pending'))
            # 立即更新套餐（差价支付成功后, 在 fulfill 里确认）
            conn.execute(
                "UPDATE subscriptions SET plan_key=%s, period=%s, pending_plan_key=NULL, pending_period=NULL, updated_at=NOW() WHERE user_id=%s",
                (new_plan['plan_key'], new_period, uid))
        else:
            # 降级：下个周期生效
            conn.execute(
                'INSERT INTO subscription_orders (order_no, user_id, amount_fen, item_type, plan_key, period, payment_method, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                (order_no, uid, amount_due, item_type, new_plan['plan_key'], new_period, payment_method, 'pending'))
            conn.execute(
                'UPDATE subscriptions SET pending_plan_key=%s, pending_period=%s, pending_at=%s WHERE user_id=%s',
                (new_plan['plan_key'], new_period, period_end.isoformat(), uid))
        conn.commit()

    desc = f_'Upgrade {new_plan["name"]}' if is_upgrade else f_'Downgrade {new_plan["name"]}'
    pay_params = _generate_pay_params(order_no, desc, amount_due, payment_method)

    return api_res({
        'order_no': order_no,
        'type': item_type,
        'plan': new_plan,
        'period': new_period,
        'amount': f'¥{amount_due/100:.2f}',
        'amount_fen': amount_due,
        'prorated_credit': prorated_credit,
        'pay_params': pay_params,
        'stub': pay_params.get('stub', False),
    }, status=201)


def _generate_pay_params(order_no, desc, amount_fen, method):
    """生成支付参数"""
    if method == 'wechat':
        return _gen_wechat_pay(order_no, desc, amount_fen)
    elif method == 'stripe':
        return _gen_stripe_pay(order_no, desc, amount_fen)
    elif method == 'paypal':
        return _gen_paypal_pay(order_no, desc, amount_fen)
    else:
        return _gen_alipay_pay(order_no, desc, amount_fen)


def _gen_wechat_pay(order_no, desc, amount_fen):
    """微信 Native 扫码支付（一次性）"""
    from .gateway.wechat import call_native_pay
    return call_native_pay(order_no, desc, amount_fen)


def _gen_alipay_pay(order_no, desc, amount_fen):
    """支付宝电脑网站支付（一次性）"""
    from .gateway.alipay import call_alipay_page_pay
    return call_alipay_page_pay(order_no, desc, amount_fen)


def _gen_stripe_pay(order_no, desc, amount_fen):
    """Stripe Checkout Session 支付（USD）"""
    from .gateway.stripe import create_checkout_session
    return create_checkout_session(order_no, desc, amount_fen)


def _gen_paypal_pay(order_no, desc, amount_fen):
    """PayPal Order 支付（USD）"""
    from .gateway.paypal import create_order
    return create_order(order_no, desc, amount_fen)


# ============================================================
# 支付回调入口
# ============================================================

def _handle_alipay_notify():
    """支付宝异步通知处理"""
    from .gateway.alipay import handle_notify as alipay_handle
    return alipay_handle()

def _handle_wechat_notify():
    """微信异步通知处理"""
    from .gateway.wechat import handle_notify as wechat_handle
    return wechat_handle()

def _handle_stripe_notify():
    """Stripe Webhook 处理"""
    from .gateway.stripe import handle_webhook as stripe_handle
    return stripe_handle()

def _handle_paypal_notify():
    """PayPal Webhook 处理"""
    from .gateway.paypal import handle_webhook as paypal_handle
    return paypal_handle()

@sub_bp.route('/notify/<channel>', methods=['POST'])
def payment_notify(channel):
    """
    统一支付回调入口
    POST /subscription/notify/wechat   — 微信回调
    POST /subscription/notify/alipay   — 支付宝回调
    POST /subscription/notify/stripe   — Stripe Webhook
    POST /subscription/notify/paypal   — PayPal Webhook
    """
    if channel == 'wechat':
        return _handle_wechat_notify()
    elif channel == 'alipay':
        return _handle_alipay_notify()
    elif channel == 'stripe':
        return _handle_stripe_notify()
    elif channel == 'paypal':
        return _handle_paypal_notify()
    return jsonify({'code': 'FAIL', 'message': 'unknown channel'}), 400


# ============================================================
# 订单履约（支付成功后执行）
# ============================================================

def _fulfill_order(order_no, payment_method=None, channel_order_id=None, notify_id=None, notify_raw=None):
    """
    支付成功后执行履约：更新订单状态 + 创建/更新订阅
    幂等安全：已履约的订单跳过
    """
    with get_db() as conn:
        order = conn.execute('SELECT * FROM subscription_orders WHERE order_no=%s', (order_no,)).fetchone()
        if not order or order['status'] != 'pending':
            return True  # 幂等：已处理

        conn.execute(
            "UPDATE subscription_orders SET status='paid', paid_at=NOW(), payment_method=COALESCE(%s,payment_method), channel_order_id=COALESCE(%s,channel_order_id), notify_id=COALESCE(%s,notify_id), notify_raw=COALESCE(%s,notify_raw), updated_at=NOW() WHERE order_no=%s",
            (payment_method, channel_order_id, notify_id, notify_raw, order_no))
        order = dict(order)

        uid = order['user_id']
        plan_key = order['plan_key']
        period = order['period']
        item_type = order['item_type']

        plan = get_plan(plan_key)
        expire_days = {'year': 365, 'semi_annual': 182, 'quarter': 90, 'month': 30}.get(period, 30)
        now = datetime.now()

        if item_type == 'new':
            # 新建订阅
            period_start = now.isoformat()
            period_end = (now + timedelta(days=expire_days)).isoformat()
            conn.execute(
                "INSERT INTO subscriptions (user_id, plan_key, period, status, current_period_start, current_period_end, created_at, updated_at) VALUES (%s,%s,%s,'active',%s,%s,NOW(),NOW()) ON CONFLICT (user_id) DO UPDATE SET plan_key=EXCLUDED.plan_key, period=EXCLUDED.period, status=EXCLUDED.status, current_period_start=EXCLUDED.current_period_start, current_period_end=EXCLUDED.current_period_end, updated_at=NOW()",
                (uid, plan_key, period, period_start, period_end))

        elif item_type in ('upgrade',):
            # 升级：已更新 plan_key，但需要更新 period_end
            existing = conn.execute('SELECT * FROM subscriptions WHERE user_id=%s', (uid,)).fetchone()
            if existing:
                old_end = datetime.fromisoformat(existing['current_period_end'])
                new_end = max(old_end, (now + timedelta(days=expire_days)))
                conn.execute(
                    'UPDATE subscriptions SET plan_key=%s, period=%s, current_period_end=%s, updated_at=NOW() WHERE user_id=%s',
                    (plan_key, period, new_end.isoformat(), uid))

        elif item_type == 'renew':
            # 续费：延长周期
            conn.execute(
                "UPDATE subscriptions SET current_period_start=current_period_end, current_period_end=NOW() + (%s * INTERVAL '1 day'), status='active', auto_renew=1, updated_at=NOW() WHERE user_id=%s",
                (expire_days, uid))

        # 更新 app_authorizations（供 Trademind/其他服务使用）
        tier = plan['tier']
        expire_at = (now + timedelta(days=expire_days)).isoformat()
        conn.execute(
            "UPDATE app_authorizations SET tier=%s, tier_expire_at=%s WHERE user_id=%s AND app_name='trademind'",
            (tier, expire_at, uid))
        if conn.total_changes == 0:
            conn.execute(
                "INSERT INTO app_authorizations (user_id, app_name, tier, tier_expire_at) VALUES (%s,'trademind',%s,%s)",
                (uid, tier, expire_at))

        # 更新 skill_keys 的 tier（社区使用）
        conn.execute("UPDATE skill_keys SET tier=%s WHERE user_id=%s", (tier, uid))

        conn.commit()

    # 自动生成发票
    try:
        from services.invoice_service import create_invoice_record
        period_text = 'Monthly' if period == 'month' else 'Yearly'
        create_invoice_record(
            order_no=order_no,
            user_id=uid,
            amount_fen=order['amount_fen'],
            plan_name=plan.get('name', plan_key),
            period_text=period_text,
            user_name=f'User#{uid}',
        )
    except Exception as e:
        print(f'[Invoice] auto-generate skipped: {e}')

    _audit_log(uid, f'{item_type}_paid', f'{plan_key}/{period} ¥{order["amount_fen"]/100:.2f}')

    # ── 钩子: 订单支付成功 ──
    try:
        from plugin_manager.injectors import fire_hook
        fire_hook('order/paid', order_no=order_no, user_id=uid,
                   plan_key=plan_key, period=period,
                   amount_fen=order['amount_fen'])
    except Exception:
        pass

    return True


# ============================================================
# 用户自助管理
# ============================================================

@sub_bp.route('/cancel', methods=['POST'])
def cancel_subscription():
    """取消订阅：当前周期仍可用，到期不续"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']
    data = request.get_json() or {}
    reason = data.get('reason', '')
    feedback = data.get('feedback', '')

    sub = get_user_subscription(uid)
    if not sub:
        return api_err(_('No Active Subscription'))
    if sub['status'] not in ('active', 'trialing', 'past_due'):
        return api_err(_(_'Current status cannot be canceled: ') + sub['status'])

    with get_db() as conn:
        conn.execute(
            "UPDATE subscriptions SET status='canceled', canceled_at=NOW(), auto_renew=0, cancel_reason=%s, cancel_feedback=%s, updated_at=NOW() WHERE user_id=%s",
            (reason, feedback, uid))
        conn.commit()

    # 如果已签约，解约
    if sub.get('alipay_agreement_id'):
        from .gateway.alipay import unsign_agreement
        try: unsign_agreement(sub['alipay_agreement_id'])
        except Exception as e:
            import logging
            logging.warning(f"[Subscription] Failed to unsign Alipay agreement: {e}")
    if sub.get('wechat_contract_id'):
        from .gateway.wechat import unsign_contract
        try: unsign_contract(sub['wechat_contract_id'])
        except Exception as e:
            import logging
            logging.warning(f"[Subscription] Failed to unsign WeChat contract: {e}")

    _audit_log(uid, 'canceled', f_'Cancellation Reason: {reason}')

    # ── 钩子: 订阅取消 ──
    try:
        from plugin_manager.injectors import fire_hook
        fire_hook('sub/cancelled', user_id=uid, plan_key=plan_key,
                   reason=reason)
    except Exception:
        pass

    return api_res({'status': 'canceled', 'message': _'Cancelled, current benefits remain valid until the end of the cycle'})

@sub_bp.route('/reactivate', methods=['POST'])
def reactivate_subscription():
    """重新激活已取消的订阅"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']

    sub = get_user_subscription(uid)
    if not sub or sub['status'] != 'canceled':
        return api_err(_('Current status cannot reactivate'))

    with get_db() as conn:
        conn.execute(
            "UPDATE subscriptions SET auto_renew=1, canceled_at=NULL, cancel_reason='', updated_at=NOW() WHERE user_id=%s",
            (uid,))
        conn.commit()

    _audit_log(uid, 'reactivated', _'User Re-activate Subscription')
    return api_res({'message': _'Subscription reactivated'})

@sub_bp.route('/stub-confirm/<order_no>', methods=['POST'])
def stub_confirm(order_no):
    """开发模式：手动确认 stub 订单"""
    payload = _require_auth()
    if not payload:
        return api_err(_('Please log in first'), 401)
    if _fulfill_order(order_no):
        with get_db() as conn:
            row = conn.execute('SELECT * FROM subscription_orders WHERE order_no=%s', (order_no,)).fetchone()
        plan = get_plan(row['plan_key']) if row else None
        msg = f_'🎉 {plan["name"] if plan else ""} Subscription Successful!' if row and row['item_type'] == 'new' else _'Order completed'
        return api_res({'message': msg, 'order_no': order_no})
    return api_err(_('Order Processing Failed'))

@sub_bp.route('/orders', methods=['GET'])
def list_my_orders():
    """我的订单历史"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']
    limit = int(request.args.get('limit', 20))

    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM subscription_orders WHERE user_id=%s AND user_deleted=0 ORDER BY created_at DESC LIMIT %s',
            (uid, limit)).fetchall()
    return api_res({'orders': [dict(r) for r in rows]})


@sub_bp.route('/orders/<order_no>/delete', methods=['POST'])
def delete_my_order(order_no):
    """用户删除订单（软删，仅隐藏）"""
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']

    with get_db() as conn:
        order = conn.execute(
            'SELECT * FROM subscription_orders WHERE order_no=%s AND user_id=%s',
            (order_no, uid)).fetchone()
        if not order:
            return api_err(_('Order Not Found'), 404)

        # 仅允许删除：已取消、失败、待支付
        allowed = ('cancelled', 'failed', 'pending')
        if order['status'] not in allowed:
            return api_err(_('Current Status (') + order["status"] + _(') order cannot be deleted, only ') + ",".join(allowed) + _(' status can be deleted'))

        conn.execute(
            "UPDATE subscription_orders SET user_deleted=1, updated_at=NOW() WHERE order_no=%s",
            (order_no,))
        conn.commit()
    return api_res({'message': _'Order deleted'})


@sub_bp.route('/retry-payment', methods=['POST'])
def retry_payment():
    """
    缴费挽回：past_due 用户手动重试支付
    创建一个新续费订单并返回支付参数，用户支付后恢复订阅
    """
    payload = _require_auth()
    if not payload: return api_err(_('Please log in first'), 401)
    uid = payload['user_id']

    sub = get_user_subscription(uid)
    if not sub or sub['status'] != 'past_due':
        return api_err(_('Can only retry payment for past_due subscriptions') )

    plan_key = sub['plan_key']
    period = sub['period']
    payment_method = sub.get('payment_method', 'wechat')
    plan = get_plan(plan_key)
    if not plan:
        return api_err(_('Plan ') + plan_key + _(' not found, contact admin'))

    amount_fen = plan['price_year'] if period == 'year' else plan['price_month']
    brand = os.environ.get('DEPLOY_BRAND', '')
    desc = f_"{brand} {plan['name']}{'Annual Payment' if period=='year' else 'Monthly Payment'} Top-up"

    order_no = new_order_no('RET')
    with get_db() as conn:
        conn.execute(
            "INSERT INTO subscription_orders (order_no, user_id, amount_fen, item_type, plan_key, period, payment_method, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (order_no, uid, amount_fen, 'renew', plan_key, period, payment_method, 'pending'))
        conn.commit()

    pay_params = _generate_pay_params(order_no, desc, amount_fen, payment_method)
    _audit_log(uid, 'retry_payment', f_'Recover Payment: {plan_key}/{period} ¥{amount_fen/100:.2f}')

    return api_res({
        'order_no': order_no,
        'plan_name': plan['name'],
        'amount': f'¥{amount_fen/100:.2f}',
        'amount_fen': amount_fen,
        'pay_params': pay_params,
        'stub': pay_params.get('stub', False),
    })


# ============================================================
# ADMIN ROUTES
# ============================================================

@sub_bp.route('/portal', methods=['GET'])
def subscription_portal():
    """订阅自助门户 — 用户管理自己的订阅"""
    from services.brand_service import get_brand_settings
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    if not token:
        return redirect('/login%sredirect=/subscription/portal')
    try:
        brand = get_brand_settings()
    except:
        brand = None
    resp = make_response(render_template('subscribe_portal.html', token=token, brand=brand))
    if token and request.args.get('token'):
        resp.set_cookie('sso_token', token, path='/', max_age=604800, samesite='Lax', secure=True, httponly=True)
    return resp


@sub_bp.route('/admin/plans', methods=['GET'])
def admin_plan_list():
    admin, err = _require_admin()
    if err: return err
    plans = get_all_plans(active_only=False)
    return api_res({'plans': plans})

@sub_bp.route('/admin/plans', methods=['POST'])
def admin_plan_create():
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    pk = data.get('plan_key', '').strip()
    name = data.get('name', '').strip()
    if not pk or not name: return api_err(_('ID and name cannot be empty'))

    with get_db() as conn:
        try:
            conn.execute(
            'INSERT INTO subscription_plans (plan_key, name, description, price_month, price_quarter, price_semi_annual, price_year, trial_days, tier, features_json, sort_order) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (pk, name, data.get('description', ''),
             int(data.get('price_month', 0)), int(data.get('price_quarter', 0)),
             int(data.get('price_semi_annual', 0)), int(data.get('price_year', 0)),
             int(data.get('trial_days', 0)), data.get('tier', 'premium'),
             json.dumps(data.get('features', [])), int(data.get('sort_order', 0))))
            conn.commit()
        except Exception as e:
            return api_err(str(e))
    _audit_log(admin['user_id'], 'create_plan', f'{name} ({pk})', admin_id=admin['user_id'])
    return api_res({'message': _'Plan Created"'}, status=201)

@sub_bp.route('/admin/plans/<int:pid>', methods=['PUT'])
def admin_plan_update(pid):
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    fields = []
    values = []
    for key in ('plan_key', 'name', 'description', 'price_month', 'price_quarter', 'price_semi_annual', 'price_year', 'trial_days', 'tier', 'features_json', 'sort_order', 'is_active'):
        if key in data:
            fields.append(f'{key}=%s')
            values.append(data[key])
    if not fields: return api_err(_('No Fields to Update'))
    fields.append("updated_at=NOW()")
    values.append(pid)
    with get_db() as conn:
        conn.execute(f'UPDATE subscription_plans SET {", ".join(fields)} WHERE id=%s', values)
        conn.commit()
    _audit_log(admin['user_id'], 'update_plan', f'plan_id={pid}', admin_id=admin['user_id'])
    return api_res({'message': _'Updated'})

@sub_bp.route('/admin/plans/<int:pid>', methods=['DELETE'])
def admin_plan_delete(pid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute('DELETE FROM subscription_plans WHERE id=%s', (pid,))
        conn.commit()
    _audit_log(admin['user_id'], 'delete_plan', f'plan_id={pid}', admin_id=admin['user_id'])
    return api_res({'message': _'Deleted'})

@sub_bp.route('/admin/subscriptions', methods=['GET'])
def admin_subscription_list():
    admin, err = _require_admin()
    if err: return err
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    offset = (page - 1) * limit

    where = []
    params = []
    if status:
        where.append('s.status=%s')
        params.append(status)
    if search:
        where.append('(u.display_name LIKE %s OR u.phone LIKE %s)')
        s = f'%{search}%'
        params.extend([s, s])

    wsql = f'WHERE {" AND ".join(where)}' if where else ''
    with get_db() as conn:
        total = conn.execute(
            f'SELECT COUNT(*) as c FROM subscriptions s JOIN users u ON u.id=s.user_id {wsql}',
            params).fetchone()
        rows = conn.execute(
            f'SELECT s.*, u.display_name, u.phone, u.agent_id FROM subscriptions s JOIN users u ON u.id=s.user_id {wsql} ORDER BY s.created_at DESC LIMIT %s OFFSET %s',
            params + [limit, offset]).fetchall()
    return api_res({
        'total': total['c'],
        'page': page,
        'limit': limit,
        'subscriptions': [dict(r) for r in rows],
    })

@sub_bp.route('/admin/subscriptions/<int:sid>/manual-renew', methods=['POST'])
def admin_manual_renew(sid):
    """管理员手动续费订阅（延长一个周期）"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        sub = conn.execute('SELECT * FROM subscriptions WHERE id=%s', (sid,)).fetchone()
        if not sub: return api_err(_('Subscription Not Found'), 404)
        plan = conn.execute('SELECT * FROM subscription_plans WHERE plan_key=%s', (sub['plan_key'],)).fetchone()
        expire_days = 365 if sub['period'] == 'year' else 30
        conn.execute(
            "UPDATE subscriptions SET current_period_start=current_period_end, current_period_end=NOW() + (%s * INTERVAL '1 day'), updated_at=NOW() WHERE id=%s",
            (expire_days, sid))
        if plan:
            conn.execute("UPDATE app_authorizations SET tier=%s, tier_expire_at=current_period_end WHERE user_id=%s AND app_name='trademind'",
                         (plan['tier'], sub['user_id']))
        conn.commit()
    _audit_log(sub['user_id'], 'manual_renew', f_'Administrator manually renews subscription_id={sid}', admin_id=admin['user_id'])
    return api_res({'message': _'Manually renewed'})

@sub_bp.route('/admin/subscriptions/<int:sid>/force-cancel', methods=['POST'])
def admin_force_cancel(sid):
    """管理员强制取消订阅"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        sub = conn.execute('SELECT * FROM subscriptions WHERE id=%s', (sid,)).fetchone()
        if not sub: return api_err(_('Subscription Not Found'), 404)
        conn.execute(
            "UPDATE subscriptions SET status='expired', auto_renew=0, updated_at=NOW() WHERE id=%s",
            (sid,))
        conn.execute("UPDATE app_authorizations SET tier='free' WHERE user_id=%s AND app_name='trademind'",
                     (sub['user_id'],))
        conn.execute("UPDATE skill_keys SET tier='free' WHERE user_id=%s", (sub['user_id'],))
        conn.commit()
    _audit_log(sub['user_id'], 'force_cancel', f_'Administrator forced cancellation subscription_id={sid}', admin_id=admin['user_id'])
    return api_res({'message': _'Forcibly cancelled, user has been downgraded to free version'})

@sub_bp.route('/admin/orders', methods=['GET'])
def admin_order_list():
    admin, err = _require_admin()
    if err: return err
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    status = request.args.get('status', '').strip()
    offset = (page - 1) * limit
    with get_db() as conn:
        if status:
            total = conn.execute('SELECT COUNT(*) as c FROM subscription_orders WHERE status=%s', (status,)).fetchone()
            rows = conn.execute(
                'SELECT o.id, o.order_no, o.user_id, o.amount_fen, o.currency, o.item_type, o.plan_key, o.period, o.payment_method, o.status, o.paid_at, o.created_at, COALESCE(u.display_name, u.username) AS nickname, u.phone FROM subscription_orders o LEFT JOIN users u ON u.id=o.user_id WHERE o.status=%s ORDER BY o.created_at DESC LIMIT %s OFFSET %s',
                (status, limit, offset)).fetchall()
        else:
            total = conn.execute('SELECT COUNT(*) as c FROM subscription_orders').fetchone()
            rows = conn.execute(
                'SELECT o.id, o.order_no, o.user_id, o.amount_fen, o.currency, o.item_type, o.plan_key, o.period, o.payment_method, o.status, o.paid_at, o.created_at, COALESCE(u.display_name, u.username) AS nickname, u.phone FROM subscription_orders o LEFT JOIN users u ON u.id=o.user_id ORDER BY o.created_at DESC LIMIT %s OFFSET %s',
                (limit, offset)).fetchall()
    return api_res({'total': total['c'], 'page': page, 'orders': [dict(r) for r in rows]})

@sub_bp.route('/admin/orders/<order_no>/refund', methods=['POST'])
def admin_refund_order(order_no):
    """管理员：退款订阅订单"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM subscription_orders WHERE order_no=%s AND status='paid'",
            (order_no,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Order not found or already refunded'}), 404

        payment_method = row['payment_method'] or ''
        channel_order_id = row['channel_order_id'] or ''
        amount_fen = row['amount_fen']

    # 调用网关退款
    refund_result = {'success': False, 'refund_no': '', 'error': 'Unknown payment method'}
    if payment_method == 'alipay':
        from .gateway.alipay import refund_order as _alipay_refund
        refund_result = _alipay_refund(order_no, amount_fen)
    elif payment_method == 'wechat':
        from .gateway.wechat import refund_order as _wechat_refund
        refund_result = _wechat_refund(order_no, amount_fen)
    elif payment_method == 'stripe':
        from .gateway.stripe import refund_order as _stripe_refund
        refund_result = _stripe_refund(channel_order_id, amount_fen)
    elif payment_method == 'paypal':
        from .gateway.paypal import refund_order as _paypal_refund
        refund_result = _paypal_refund(channel_order_id, amount_fen)

    if not refund_result.get('success'):
        return jsonify({'success': False, 'error': refund_result.get('error', 'Refund failed')}), 400

    # 更新订单状态 + 取消订阅
    with get_db() as conn:
        conn.execute(
            "UPDATE subscription_orders SET status='refunded', updated_at=NOW() WHERE order_no=%s",
            (order_no,)
        )
        conn.execute(
            "UPDATE subscriptions SET status='canceled', updated_at=NOW() WHERE id=%s",
            (row['sub_id'],)
        )
        conn.commit()

    return jsonify({'success': True, 'message': 'Refunded'})

@sub_bp.route('/admin/stats', methods=['GET'])
def admin_stats():
    """数据看板：MRR、续费率、churn"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        # MRR
        mrr = conn.execute("""
            SELECT COALESCE(SUM(
                CASE WHEN s.period='year' THEN sp.price_year/12 ELSE sp.price_month END
            ),0) as mrr FROM subscriptions s
            JOIN subscription_plans sp ON sp.plan_key=s.plan_key
            WHERE s.status IN ('active','trialing')
        """).fetchone()
        # 本月新增（范围查询，避免 strftime 函数包裹索引列）
        new = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE created_at >= date_trunc('month', NOW())
              AND created_at < date_trunc('month', NOW()) + INTERVAL '1 month'
        """).fetchone()
        # 本月取消
        canceled = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE status='canceled'
              AND canceled_at >= date_trunc('month', NOW())
              AND canceled_at < date_trunc('month', NOW()) + INTERVAL '1 month'
        """).fetchone()
        # 总活跃
        active = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions WHERE status='active'
        """).fetchone()
        # 今日收入（范围查询，避免 date() 函数包裹索引列）
        today_revenue = conn.execute("""
            SELECT COALESCE(SUM(amount_fen),0) as rev FROM subscription_orders
            WHERE status='paid'
              AND paid_at >= date_trunc('day', NOW())
              AND paid_at < date_trunc('day', NOW()) + INTERVAL '1 day'
        """).fetchone()
        # 本月收入
        month_revenue = conn.execute("""
            SELECT COALESCE(SUM(amount_fen),0) as rev FROM subscription_orders
            WHERE status='paid'
              AND paid_at >= date_trunc('month', NOW())
              AND paid_at < date_trunc('month', NOW()) + INTERVAL '1 month'
        """).fetchone()
        # 各套餐分布
        dist = conn.execute("""
            SELECT s.plan_key, sp.name, COUNT(*) as c FROM subscriptions s
            JOIN subscription_plans sp ON sp.plan_key=s.plan_key
            WHERE s.status='active' GROUP BY s.plan_key
        """).fetchall()

    return api_res({
        'mrr': mrr['mrr'],
        'mrr_yuan': f'¥{mrr["mrr"]/100:.2f}',
        'active_subscriptions': active['c'],
        'new_this_month': new['c'],
        'canceled_this_month': canceled['c'],
        'today_revenue_fen': today_revenue['rev'],
        'month_revenue_fen': month_revenue['rev'],
        'distribution': [dict(r) for r in dist],
    })

# ============================================================
# Coupon Application (Helper) — 已迁移至 plugins/coupons/
# ============================================================
def _apply_coupon(code, user_id, plan_key, amount_fen):
    """走插件引擎验证优惠券，返回折扣金额（分）"""
    try:
        from plugins.coupons import get_engine
        engine = get_engine()
        if not engine:
            return 0
        result = engine.validate(code, amount_fen / 100.0,
                                  user_id=user_id, plan=plan_key)
        if not result.get('valid'):
            return 0
        return int(result['discount'] * 100)
    except Exception:
        return 0

@sub_bp.route('/admin/events', methods=['GET'])
def admin_payment_events():
    admin, err = _require_admin()
    if err: return err
    limit = int(request.args.get('limit', 50))
    with get_db() as conn:
        rows = conn.execute(
            'SELECT e.*, COALESCE(u.display_name, u.username) AS nickname FROM payment_events e LEFT JOIN users u ON u.id=e.user_id ORDER BY e.created_at DESC LIMIT %s',
            (limit,)).fetchall()
    return api_res({'events': [dict(r) for r in rows]})

@sub_bp.route('/admin/audit-log', methods=['GET'])
def admin_audit_log():
    admin, err = _require_admin()
    if err: return err
    limit = int(request.args.get('limit', 50))
    with get_db() as conn:
        rows = conn.execute(
            'SELECT l.*, COALESCE(u.display_name, u.username) AS nickname FROM subscription_audit_log l LEFT JOIN users u ON u.id=l.user_id ORDER BY l.created_at DESC LIMIT %s',
            (limit,)).fetchall()
    return api_res({'logs': [dict(r) for r in rows]})

# ============================================================
# Coupon Application (Helper)
# ============================================================
def _apply_coupon(code, user_id, plan_key, amount_fen):
    """应用优惠码，返回折扣金额（分）
    支持类型：fixed / percent / first_month_percent
    支持特征：首月特价、叠加规则、限时窗口
    """
    with get_db() as conn:
        coupon = conn.execute(
            'SELECT * FROM coupons WHERE code=%s AND is_active=1 AND (expires_at IS NULL OR expires_at > NOW())',
            (code,)).fetchone()
        if not coupon:
            return 0

        coupon = dict(coupon)

        # 限时窗口检查
        now_iso = datetime.now().isoformat()
        active_from = coupon.get('active_from', '')
        active_to = coupon.get('active_to', '')
        if active_from and now_iso < active_from:
            return 0  # 还未生效
        if active_to and now_iso > active_to:
            return 0  # 已过期

        # 检查使用次数
        if coupon['max_uses'] > 0 and coupon['used_count'] >= coupon['max_uses']:
            return 0
        # 检查每人使用次数
        user_uses = conn.execute(
            'SELECT COUNT(*) as c FROM coupon_redemptions WHERE coupon_id=%s AND user_id=%s',
            (coupon['id'], user_id)).fetchone()
        if user_uses['c'] >= coupon['max_per_user']:
            return 0
        # 检查适用套餐
        if coupon['applicable_plans']:
            allowed = coupon['applicable_plans'].split(',')
            if plan_key not in allowed:
                return 0
        # 检查最低消费
        if amount_fen < coupon['min_amount_fen']:
            return 0

        # 检查是否已应用了其他不可叠加的优惠券
        first_month_only = bool(coupon.get('first_month_only', 0))
        stackable = bool(coupon.get('stackable', 0))
        if not stackable:
            # 不可叠加：检查该用户是否已有其他不可叠加的优惠券应用于此订单
            existing_stacked = conn.execute(
                "SELECT COUNT(*) as c FROM coupon_redemptions WHERE user_id=%s AND order_no LIKE 'SUB%' AND created_at > NOW() - INTERVAL '1 hour'",
                (user_id,)).fetchone()
            if existing_stacked and existing_stacked['c'] > 0:
                return 0  # 已有其他优惠券，不可叠加

        # 计算折扣
        coupon_type = coupon.get('coupon_type') or coupon.get('type', 'fixed')
        discount_fen = 0

        if coupon_type == 'fixed':
            discount_fen = min(coupon['value'], amount_fen)
        elif coupon_type == 'percent':
            discount_fen = amount_fen * coupon['value'] // 100
        elif coupon_type == 'first_month_percent':
            # 首月特价：按百分比打折，仅限首月
            discount_fen = amount_fen * coupon['value'] // 100
            # 标记 order 的 note 以表示这是首月特价
        else:
            return 0

        # 记录使用
        conn.execute('UPDATE coupons SET used_count=used_count+1 WHERE id=%s', (coupon['id'],))
        conn.commit()

    return discount_fen
