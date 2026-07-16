#!/usr/bin/env python3
"""Shop Public — 前端商城API (platform service)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
from flask import Blueprint, jsonify, request, render_template, make_response, redirect
from models import get_db
from services.jwt_service import validate_token
from plugin_manager.event_bus import get_event_bus, EventName
import secrets
from datetime import datetime

shop_public_bp = Blueprint('shop_public', __name__, url_prefix='/shop')

# ── 内存限流 ──
import time as _time
_RATE_LIMIT = {}  # key: "user_id:endpoint"  val: [ts1, ts2, ...]


def _check_rate_limit(user_id, endpoint, max_requests=60, window=60):
    """每 user+endpoint 在 window 秒内最多 max_requests 次"""
    key = f'{user_id}:{endpoint}'
    now = _time.time()
    hits = _RATE_LIMIT.get(key, [])
    # 清除窗口外的记录
    hits = [t for t in hits if now - t < window]
    if len(hits) >= max_requests:
        return False
    hits.append(now)
    _RATE_LIMIT[key] = hits
    # 防内存泄漏：定期清理过期 key（每 100 次调用清理一次）
    if len(_RATE_LIMIT) > 10000:
        for k in list(_RATE_LIMIT.keys()):
            _RATE_LIMIT[k] = [t for t in _RATE_LIMIT[k] if now - t < window * 2]
            if not _RATE_LIMIT[k]:
                del _RATE_LIMIT[k]
    return True


def _safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _require_user():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    payload = validate_token(token) if token else None
    if not payload:
        return None, (jsonify({'success': False, 'error': _('Please log in first')}), 401)
    return payload, None


# =============================================
# 页面渲染
# =============================================
@shop_public_bp.route('', methods=['GET'])
@shop_public_bp.route('/', methods=['GET'])
def shop_page():
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    resp = make_response(render_template('shop.html', token=token))
    if token and request.args.get('token'):
        resp.set_cookie('sso_token', token, path='/', max_age=604800, samesite='Lax', secure=True, httponly=True)
    return resp


@shop_public_bp.route('/<int:pid>', methods=['GET'])
def shop_detail(pid):
    """商品详情页（普通用户访问）"""
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    resp = make_response(render_template('shop_detail.html', token=token))
    if token and request.args.get('token'):
        resp.set_cookie('sso_token', token, path='/', max_age=604800, samesite='Lax', secure=True, httponly=True)
    return resp


@shop_public_bp.route('/preview/<int:pid>', methods=['GET'])
def shop_preview(pid):
    """商品预览页（管理员预览，绕过下架检查）"""
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    resp = make_response(render_template('shop_detail.html', token=token, preview=True))
    if token and request.args.get('token'):
        resp.set_cookie('sso_token', token, path='/', max_age=604800, samesite='Lax', secure=True, httponly=True)
    return resp


@shop_public_bp.route('/cart', methods=['GET'])
def cart_page():
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    resp = make_response(render_template('cart.html', token=token))
    if token and request.args.get('token'):
        resp.set_cookie('sso_token', token, path='/', max_age=604800, samesite='Lax', secure=True, httponly=True)
    return resp


@shop_public_bp.route('/pay/<oid>', methods=['GET'])
def payment_page(oid):
    """支付页 — 展示订单信息，用户点击后调支付宝"""
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    resp = make_response(render_template('payment.html', order_id=oid, token=token))
    if token and request.args.get('token'):
        resp.set_cookie('sso_token', token, path='/', max_age=604800, samesite='Lax', secure=True, httponly=True)
    return resp


@shop_public_bp.route('/orders', methods=['GET'])
def orders_page():
    """订单列表页"""
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    resp = make_response(render_template('orders.html', token=token))
    if token and request.args.get('token'):
        resp.set_cookie('sso_token', token, path='/', max_age=604800, samesite='Lax', secure=True, httponly=True)
    return resp


# =============================================
# API: 当前登录用户信息
# =============================================
@shop_public_bp.route('/api/user/info', methods=['GET'])
def api_user_info():
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        user = conn.execute(
            'SELECT id, username, display_name, phone, email, avatar_url, is_admin, created_at '
            'FROM users WHERE id=%s', (uid,)
        ).fetchone()
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404
    d = dict(user)
    d['is_admin'] = bool(d['is_admin'])
    return jsonify({'success': True, 'data': d})


@shop_public_bp.route('/cloud', methods=['GET'])
def cloud_instances_page():
    from flask import session
    token = session.get('token', '')
    return render_template('cloud_instances.html', token=token)


# =============================================
# API: 商品列表
# =============================================
@shop_public_bp.route('/api/products', methods=['GET'])
def api_products():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    cat_id = request.args.get('category_id', type=int, default=0)
    with get_db() as conn:
        sql = '''SELECT p.*, c.name as category_name FROM products p
                 LEFT JOIN categories c ON p.category_id=c.id
                 WHERE p.is_active=1'''
        params = []
        if category:
            sql += ' AND p.category LIKE ?'
            params.append(f'%{category}%')
        if cat_id:
            sql += ' AND p.category_id=?'
            params.append(cat_id)
        if search:
            sql += ' AND (p.title LIKE ? OR p.subtitle LIKE ? OR p.description LIKE ?)'
            s = f'%{search}%'
            params.extend([s, s, s])
        sql += ' ORDER BY p.sort_order ASC, p.id DESC'
        rows = conn.execute(sql, params).fetchall()
    data = []
    for r in rows:
        d = dict(r)
        # 解析JSON字段
        for f in ['features', 'images', 'ai_config']:
            if isinstance(d.get(f), str):
                try:
                    d[f] = json.loads(d[f])
                except:
                    if f == 'images':
                        d[f] = []
                    elif f == 'ai_config':
                        d[f] = {}
                    elif f == 'features':
                        d[f] = []
        data.append(d)
    return jsonify({'success': True, 'data': data})


@shop_public_bp.route('/api/products/<int:pid>', methods=['GET'])
def api_product_detail(pid):
    with get_db() as conn:
        row = conn.execute(
            '''SELECT p.*, c.name as category_name FROM products p
               LEFT JOIN categories c ON p.category_id=c.id
               WHERE p.id=%s AND p.is_active=1''', (pid,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在或已下架'}), 404
        d = dict(row)
        for f in ['features', 'images', 'ai_config']:
            if isinstance(d.get(f), str):
                try:
                    d[f] = json.loads(d[f])
                except:
                    d[f] = [] if f in ['features', 'images'] else {}
    return jsonify({'success': True, 'data': d})


@shop_public_bp.route('/api/products/<int:pid>/skus', methods=['GET'])
def api_product_skus(pid):
    """获取商品SKU（公共）"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, sku_code, spec_path, price, stock FROM product_skus WHERE product_id=%s AND is_active=1',
            (pid,)
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


# =============================================
# API: 购物车
# =============================================
@shop_public_bp.route('/api/cart', methods=['GET'])
def api_get_cart():
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT c.*, p.title, p.subtitle, p.price, p.original_price, p.thumbnail, p.stock, p.is_active,
                      sk.sku_code, sk.spec_path, sk.price as sku_price
               FROM carts c
               JOIN products p ON c.product_id=p.id
               LEFT JOIN product_skus sk ON c.sku_id=sk.id
               WHERE c.user_id=%s ORDER BY c.created_at DESC''', (uid,)
        ).fetchall()
        items = []
        total = 0
        for r in rows:
            item = dict(r)
            item['subtotal'] = (item['sku_price'] or item['price']) * item['quantity']
            total += item['subtotal']
            items.append(item)
    return jsonify({'success': True, 'data': {'items': items, 'total': round(total, 2)}})


@shop_public_bp.route('/api/cart/add', methods=['POST'])
def api_add_to_cart():
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    if not _check_rate_limit(uid, 'cart', max_requests=60, window=60):
        return jsonify({'success': False, 'error': '操作太频繁'}), 429
    data = request.get_json() or {}
    pid = data.get('product_id')
    qty = _safe_int(data.get('quantity', 1))
    if not pid:
        return jsonify({'success': False, 'error': '缺少商品ID'}), 400
    if qty < 1:
        return jsonify({'success': False, 'error': '数量不能小于1'}), 400

    with get_db() as conn:
        prod = conn.execute('SELECT id, stock, is_active FROM products WHERE id=%s', (pid,)).fetchone()
        if not prod:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        if not prod['is_active']:
            return jsonify({'success': False, 'error': '商品已下架'}), 400

        sku_id = data.get('sku_id', 0)
        sku_info = None
        if sku_id:
            sku_info = conn.execute(
                'SELECT id, price, stock FROM product_skus WHERE id=%s AND product_id=%s AND is_active=1',
                (sku_id, pid)
            ).fetchone()
            if not sku_info:
                return jsonify({'success': False, 'error': 'SKU不存在'}), 400
            if sku_info['stock'] < qty:
                return jsonify({'success': False, 'error': 'SKU库存不足'}), 400
        elif prod['stock'] is not None and prod['stock'] <= 0:
            return jsonify({'success': False, 'error': '商品已售罄'}), 400

        existing = conn.execute(
            'SELECT id, quantity FROM carts WHERE user_id=%s AND product_id=%s AND sku_id=%s',
            (uid, pid, sku_id)
        ).fetchone()
        if existing:
            new_qty = existing['quantity'] + qty
            conn.execute('UPDATE carts SET quantity=%s WHERE id=%s', (new_qty, existing['id']))
        else:
            conn.execute(
                'INSERT INTO carts (user_id, product_id, quantity, sku_id) VALUES (%s,%s,%s,%s)',
                (uid, pid, qty, sku_id)
            )
        conn.commit()
    return jsonify({'success': True, 'message': '已加入购物车'})


@shop_public_bp.route('/api/cart/update', methods=['POST'])
def api_update_cart():
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    data = request.get_json() or {}
    cid = data.get('cart_id')
    qty = _safe_int(data.get('quantity', 1))
    if qty < 1:
        return jsonify({'success': False, 'error': '数量不能小于1'}), 400
    with get_db() as conn:
        conn.execute('UPDATE carts SET quantity=%s WHERE id=%s AND user_id=%s', (qty, cid, uid))
        conn.commit()
    return jsonify({'success': True, 'message': '已更新'})


@shop_public_bp.route('/api/cart/remove', methods=['POST'])
def api_remove_from_cart():
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    data = request.get_json() or {}
    cid = data.get('cart_id')
    with get_db() as conn:
        conn.execute('DELETE FROM carts WHERE id=%s AND user_id=%s', (cid, uid))
        conn.commit()
    return jsonify({'success': True, 'message': '已移除'})


# =============================================
# API: 用户地址列表
# =============================================
@shop_public_bp.route('/api/addresses', methods=['GET'])
def api_addresses():
    """Return user's saved addresses (cn + intl)"""
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        cn_rows = conn.execute(
            'SELECT id, recipient_name, phone, province_code, city_code, district_code, street_code, street_address, postal_code, is_default FROM user_addresses WHERE user_id=%s AND status=1',
            (uid,)
        ).fetchall()
        intl_rows = conn.execute(
            'SELECT id, recipient_name, phone, country, state, city, address_line1, address_line2, postal_code, is_default FROM user_addresses_intl WHERE user_id=%s AND status=1',
            (uid,)
        ).fetchall()
    cn_list = []
    for r in cn_rows:
        parts = [r['province_code'], r['city_code'], r['district_code'], r['street_code'], r['street_address']]
        addr = ' '.join(p for p in parts if p)
        cn_list.append({'id': r['id'], 'type': 'cn', 'recipient_name': r['recipient_name'], 'phone': r['phone'], 'address': addr, 'is_default': bool(r['is_default'])})
    intl_list = []
    for r in intl_rows:
        parts = [r['country'], r['state'], r['city'], r['address_line1'], r['address_line2']]
        addr = ', '.join(p for p in parts if p)
        intl_list.append({'id': r['id'], 'type': 'intl', 'recipient_name': r['recipient_name'], 'phone': r['phone'], 'address': addr, 'is_default': bool(r['is_default'])})
    all_addrs = cn_list + intl_list
    default = None
    for a in all_addrs:
        if a['is_default']:
            default = a
            break
    return jsonify({'success': True, 'data': {'addresses': all_addrs, 'default': default}})


# =============================================
# API: 下单
# =============================================
@shop_public_bp.route('/api/checkout', methods=['POST'])
def api_checkout():
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    if not _check_rate_limit(uid, 'checkout', max_requests=10, window=60):
        return jsonify({'success': False, 'error': '操作太频繁，请稍后再试'}), 429
    data = request.get_json() or {}
    idempotency_key = (data.get('idempotency_key', '') or '').strip()

    # 幂等检查
    if idempotency_key:
        with get_db() as conn:
            existing = conn.execute(
                'SELECT order_id, total, status FROM order_items WHERE idempotency_key=%s LIMIT 1',
                (idempotency_key,)
            ).fetchone()
            if existing:
                return jsonify({
                    'success': True,
                    'data': {
                        'order_id': existing['order_id'],
                        'total': existing['total'],
                        'duplicate': True,
                        'note': '此订单已存在，返回已有结果'
                    }
                })

    # 用户只能传 product_id + quantity（不允许传 price）
    raw_items = data.get('items', [])
    coupon_code = data.get('coupon_code', '').strip().upper()

    # ── Resolve shipping address ──
    address_id = data.get('address_id')
    address_type = data.get('address_type', 'cn')  # 'cn' or 'intl'
    receiver_name = ''
    receiver_phone = ''
    receiver_address = ''

    if address_id:
        with get_db() as conn:
            if address_type == 'intl':
                addr = conn.execute(
                    'SELECT * FROM user_addresses_intl WHERE id=%s AND user_id=%s',
                    (address_id, uid)
                ).fetchone()
                if addr:
                    receiver_name = addr['recipient_name']
                    receiver_phone = addr['phone']
                    parts = [addr['country'], addr['state'], addr['city'],
                             addr['address_line1'], addr.get('address_line2', '')]
                    receiver_address = ', '.join(p for p in parts if p)
            else:
                addr = conn.execute(
                    'SELECT * FROM user_addresses WHERE id=%s AND user_id=%s',
                    (address_id, uid)
                ).fetchone()
                if addr:
                    receiver_name = addr['recipient_name']
                    receiver_phone = addr['phone']
                    parts = [addr.get('province_code',''), addr.get('city_code',''),
                             addr.get('district_code',''), addr.get('street_code',''),
                             addr['street_address']]
                    receiver_address = ' '.join(p for p in parts if p)

    items = []

    with get_db() as conn:
        if not raw_items:
            # 从购物车取
            cart_rows = conn.execute(
                '''SELECT c.product_id, c.quantity, p.title, p.price, p.stock, p.is_active
                   FROM carts c JOIN products p ON c.product_id=p.id
                   WHERE c.user_id=%s''', (uid,)
            ).fetchall()
            if not cart_rows:
                return jsonify({'success': False, 'error': '购物车为空'}), 400
            for r in cart_rows:
                if not r['is_active']:
                    continue
                items.append({'product_id': r['product_id'], 'quantity': r['quantity'],
                              'title': r['title'], 'price': r['price']})
        else:
            # 从用户传入 — 价格必须从数据库查，不接受客户端价格
            for item in raw_items:
                pid = item.get('product_id')
                qty = _safe_int(item.get('quantity', 1))
                if qty < 1:
                    return jsonify({'success': False, 'error': '数量不能小于1'}), 400
                prod = conn.execute(
                    'SELECT id, title, price, stock, is_active FROM products WHERE id=%s', (pid,)
                ).fetchone()
                if not prod or not prod['is_active']:
                    return jsonify({'success': False, 'error': f'商品不存在或已下架: {pid}'}), 400
                items.append({'product_id': prod['id'], 'quantity': qty,
                              'title': prod['title'], 'price': prod['price']})

    if not items:
        return jsonify({'success': False, 'error': '无有效商品'}), 400

    # 计算总价 — 价格全部来自数据库
    subtotal = sum(float(item['price']) * int(item['quantity']) for item in items)
    total = round(subtotal, 2)
    order_id = 'SP' + datetime.now().strftime('%Y%m%d%H%M%S') + secrets.token_hex(4).upper()

    # ── 单事务：优惠券验证 + 订单创建 + 使用计数 + 清空购物车 ──
    with get_db() as conn:
        discount = 0
        coupon_id = None

        if coupon_code:
            cpn = conn.execute(
                'SELECT * FROM coupons WHERE code=%s AND is_active=1', (coupon_code,)
            ).fetchone()
            if not cpn:
                return jsonify({'success': False, 'error': '优惠券无效'}), 400
            if cpn['usage_limit'] and cpn['used_count'] >= cpn['usage_limit']:
                return jsonify({'success': False, 'error': '优惠券已用完'}), 400
            if subtotal < cpn['min_amount']:
                return jsonify({'success': False, 'error': f'未达到最低消费 ¥{cpn["min_amount"]}'}), 400
            if cpn['expire_at'] and cpn['expire_at'] < datetime.now().isoformat():
                return jsonify({'success': False, 'error': '优惠券已过期'}), 400
            coupon_id = cpn['id']
            if cpn['coupon_type'] == 'fixed':
                discount = min(cpn['value'], subtotal)
            else:
                discount = round(subtotal * cpn['value'] / 100, 2)
            # ← used_count+1 在事务内，下行插入后提交
            conn.execute('UPDATE coupons SET used_count=used_count+1 WHERE id=%s', (coupon_id,))

        total = round(subtotal - discount, 2)

        for item in items:
            conn.execute(
                '''INSERT INTO order_items (order_id, user_id, product_id, product_title,
                   quantity, unit_price, subtotal, coupon_id, discount, status, idempotency_key, created_at,
                   receiver_name, receiver_phone, receiver_address)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s,%s)''',
                (order_id, uid, item['product_id'], (item.get('title', '') or '')[:200],
                 int(item.get('quantity', 1)), float(item.get('price', 0)),
                 round(float(item.get('price', 0)) * int(item.get('quantity', 1)), 2),
                 coupon_id, round(discount / max(len(items), 1), 2) if coupon_id else 0,
                 'pending', idempotency_key,
                 receiver_name, receiver_phone, receiver_address)
            )
            # 增加销量 + 扣减库存
            conn.execute('UPDATE products SET sales_count=sales_count+%s, stock=MAX(0,stock-%s) WHERE id=%s',
                         (int(item.get('quantity', 1)), int(item.get('quantity', 1)), item['product_id']))
        # 优惠券使用计数 — 与订单创建在同一事务中
        if coupon_id:
            conn.execute('UPDATE coupons SET used_count=used_count+1 WHERE id=%s', (coupon_id,))
        # 清空购物车
        if not data.get('keep_cart'):
            conn.execute('DELETE FROM carts WHERE user_id=%s', (uid,))
        conn.commit()

    # 触发事件：订单创建
    get_event_bus().emit(EventName.ORDER_CREATED, order_id=order_id, user_id=uid,
                         total=total, items=items)

    return jsonify({
        'success': True,
        'data': {
            'order_id': order_id,
            'total': total,
            'subtotal': subtotal,
            'discount': discount,
            'items_count': len(items),
            'stub': True,
            'payment_required': True,
            'note': '订单已创建，请前往订单页完成支付'
        }
    })


# =============================================
# API: 订单查询
# =============================================
@shop_public_bp.route('/api/orders', methods=['GET'])
def api_orders():
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT * FROM order_items WHERE user_id=%s AND user_deleted=0
               ORDER BY created_at DESC LIMIT 50''', (uid,)
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@shop_public_bp.route('/api/orders/<oid>/delete', methods=['POST'])
def api_delete_order(oid):
    """用户删除订单（软删，仅隐藏无效订单）"""
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        order = conn.execute(
            'SELECT * FROM order_items WHERE order_id=%s AND user_id=%s',
            (oid, uid)).fetchone()
        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        allowed = ('cancelled', 'pending', 'refunded')
        if order['status'] not in allowed:
            return jsonify({'success': False, 'error': f'当前状态({order["status"]})的订单不可删除'}), 400
        conn.execute(
            'UPDATE order_items SET user_deleted=1 WHERE order_id=%s AND user_id=%s',
            (oid, uid))
        conn.commit()
    return jsonify({'success': True, 'message': '已删除'})


@shop_public_bp.route('/api/orders/<oid>/cancel', methods=['POST'])
def api_cancel_order(oid):
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM order_items WHERE order_id=%s AND user_id=%s', (oid, uid)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] != 'pending':
            return jsonify({'success': False, 'error': '只能取消待支付订单'}), 400
        conn.execute("UPDATE order_items SET status='cancelled' WHERE order_id=%s", (oid,))
        conn.commit()
    get_event_bus().emit(EventName.ORDER_CANCELLED, order_id=oid, user_id=uid)
    return jsonify({'success': True, 'message': _('Cancelled')})


@shop_public_bp.route('/api/orders/<oid>/confirm-receipt', methods=['POST'])
def api_confirm_receipt(oid):
    """用户确认收货 → 标记为已完成"""
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    from datetime import datetime
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM order_items WHERE order_id=%s AND user_id=%s', (oid, uid)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] != 'paid':
            return jsonify({'success': False, 'error': '只能对已支付订单确认收货'}), 400
        if row['shipping_status'] != 'shipped':
            return jsonify({'success': False, 'error': '订单尚未发货'}), 400
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE order_items SET status='completed', completed_at=%s WHERE order_id=%s",
            (now, oid)
        )
        conn.commit()
    get_event_bus().emit('order.completed', order_id=oid, user_id=uid)
    return jsonify({'success': True, 'message': '已确认收货'})


@shop_public_bp.route('/api/orders/<oid>/request-refund', methods=['POST'])
def api_request_refund(oid):
    """用户申请退款"""
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    data = request.get_json() or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
        return jsonify({'success': False, 'error': '请填写退款原因'}), 400
    from datetime import datetime
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM order_items WHERE order_id=%s AND user_id=%s', (oid, uid)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] not in ('paid',):
            return jsonify({'success': False, 'error': '当前订单状态不允许申请退款'}), 400
        if row['refund_reason']:
            return jsonify({'success': False, 'error': '已申请退款，请等待处理'}), 400
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE order_items SET status='refunding', refund_reason=%s, refund_requested_at=%s WHERE order_id=%s",
            (reason, now, oid)
        )
        conn.commit()
    get_event_bus().emit(EventName.ORDER_REFUNDED, order_id=oid, user_id=uid, reason=reason)
    return jsonify({'success': True, 'message': '退款申请已提交'})


@shop_public_bp.route('/orders/<int:oid>/track-user', methods=['GET'])
def track_order_user(oid):
    """用户端查询物流轨迹"""
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        row = conn.execute(
            'SELECT oi.*, ec.kdniao_code FROM order_items oi '
            'LEFT JOIN express_companies ec ON oi.tracking_company=ec.code '
            'WHERE oi.id=%s AND oi.user_id=%s', (oid, uid)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if not row.get('tracking_number'):
            return jsonify({'success': True, 'data': {
                'tracking_company': '', 'tracking_number': '',
                'shipped_at': '', 'shipping_status': row.get('shipping_status', ''),
                'traces': [],
            }})
        shipper_code = row['kdniao_code'] or row['tracking_company']
        logistic_code = row['tracking_number']

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
    success, data, err_msg = False, {}, '物流插件未启用'
    _pm = __import__('flask').current_app.extensions.get('plugin_manager')
    _logistics = _pm.get_instance('logistics') if (_pm and _pm.is_enabled('logistics')) else None
    if _logistics:
        success, data, err_msg = _logistics.query_track(shipper_code, logistic_code)
    return jsonify({
        'success': True,
        'data': {
            'tracking_company': row['tracking_company'],
            'tracking_number': row['tracking_number'],
            'shipped_at': row.get('shipped_at', ''),
            'shipping_status': row.get('shipping_status', ''),
            'traces': data.get('traces', []) if success else [],
            'state_text': data.get('state_text', '') if success else '',
            'track_error': err_msg if not success else '',
        }
    })


# =============================================
# API: 发起支付
# =============================================
@shop_public_bp.route('/api/pay/<oid>', methods=['POST'])
def api_pay_order(oid):
    """为订单创建支付（支持支付宝/微信）"""
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    with get_db() as conn:
        items = conn.execute(
            'SELECT * FROM order_items WHERE order_id=%s AND user_id=%s',
            (oid, uid)
        ).fetchall()
        if not items:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if items[0]['status'] != 'pending':
            return jsonify({'success': False, 'error': '当前订单状态不允许支付'}), 400
        total = round(sum(
            (float(r['subtotal']) or 0) - (float(r['discount']) or 0)
            for r in items
        ), 2)
        subject = items[0]['product_title'][:64] if items else '商城订单'

    method = (request.get_json() or {}).get('method', 'alipay')

    if method == 'wechat':
        # ── 微信支付 ──
        from routes.subscription.gateway.wechat import call_native_pay
        notify_base = os.environ.get('NOTIFY_BASE', '')
        if not notify_base:
            try:
                with get_db() as pgconn:
                    row = pgconn.execute(
                        "SELECT value FROM system_config WHERE key=%s",
                        ('payment.notify_base',)
                    ).fetchone()
                    if row:
                        notify_base = row[0]
            except Exception:
                pass
        shop_notify_url = notify_base.rstrip('/') + '/shop/api/pay/wechat-notify' if notify_base else ''
        result = call_native_pay(oid, subject, int(round(total * 100)), notify_url=shop_notify_url)
        return jsonify({'success': result.get('stub', False) or not result.get('error'),
                        'data': {'method': 'wechat', **result}})

    # ── 支付宝（默认） ──
    try:
        # Try PaymentPlugin first
        _pm = __import__('flask').current_app.extensions.get('plugin_manager')
        _payment = _pm.get_instance('payment') if (_pm and _pm.is_enabled('payment')) else None
        if _payment:
            result = _payment.create_shop_payment(oid, total, subject)
        else:
            _auth_center = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
            if _auth_center not in sys.path:
                sys.path.insert(0, _auth_center)
            from services.payment_service import create_shop_payment
            result = create_shop_payment(oid, total, subject)
    except ImportError:
        return jsonify({'success': False, 'error': '支付服务未就绪'}), 500

    # 获取用户 token，写入 cookie 确保支付后跳回时登录态保持
    auth = request.headers.get('Authorization', '')
    user_token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not user_token:
        user_token = request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''

    result = create_shop_payment(oid, total, subject)
    resp = jsonify({'success': result.get('success', False), 'data': {'method': 'alipay', **result}})
    if user_token:
        resp.set_cookie('sso_token', user_token, path='/', max_age=604800,
                        samesite='Lax', secure=True, httponly=True)
    return resp


# =============================================
# API: 桩模式确认支付（开发/测试用）
# =============================================
@shop_public_bp.route('/api/pay/<oid>/stub-confirm', methods=['POST'])
def api_stub_confirm(oid):
    """开发模式：直接确认订单已支付，不经过支付宝"""
    payload, err = _require_user()
    if err:
        return err
    uid = payload['user_id']
    # Try PaymentPlugin first
    _pm = __import__('flask').current_app.extensions.get('plugin_manager')
    _payment = _pm.get_instance('payment') if (_pm and _pm.is_enabled('payment')) else None
    if _payment:
        success, msg = _payment.confirm_shop_order(oid)
    else:
        from services.payment_service import confirm_shop_order
        success, msg = confirm_shop_order(oid, f'STUB_{oid}', 'stub')
    with get_db() as conn:
        row = conn.execute(
            'SELECT status FROM order_items WHERE order_id=%s AND user_id=%s', (oid, uid)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] == 'paid':
            return jsonify({'success': True, 'message': '订单已支付'})
        if row['status'] != 'pending':
            return jsonify({'success': False, 'error': '订单状态不允许支付'}), 400
    success, msg = confirm_shop_order(oid, f'STUB_{oid}', 'stub')
    return jsonify({'success': success, 'message': msg})


# =============================================
# API: 支付回调（微信异步通知）
# =============================================
@shop_public_bp.route('/api/pay/wechat-notify', methods=['POST'])
def api_wechat_notify():
    """微信支付异步通知回调 — 商城订单"""
    from routes.subscription.gateway.wechat import _verify_wechat_sign, _decrypt_wechat_resource
    # Try PaymentPlugin first
    _pm = __import__('flask').current_app.extensions.get('plugin_manager')
    _payment = _pm.get_instance('payment') if (_pm and _pm.is_enabled('payment')) else None
    if _payment:
        confirm_fn = _payment.confirm_shop_order
        verify_fn = _payment.verify_notify
    else:
        from services.payment_service import confirm_shop_order as confirm_fn, verify_notify as verify_fn

    body = request.get_data(as_text=True)
    headers = request.headers

    # 验签
    if not _verify_wechat_sign(headers, body):
        return 'FAIL', 400

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return 'FAIL', 400

    resource = data.get('resource', {})
    resource_plain = _decrypt_wechat_resource(resource)
    if not resource_plain:
        import logging
        logging.error("微信支付回调（商城）解密失败")
        return 'FAIL', 400

    trade_state = resource_plain.get('trade_state', '')
    if trade_state != 'SUCCESS':
        return 'FAIL', 400

    order_id = resource_plain.get('out_trade_no', '')
    transaction_id = resource_plain.get('transaction_id', '')

    if not order_id:
        return 'FAIL', 400

    success, msg = confirm_fn(order_id, transaction_id, 'wechat')
    return 'SUCCESS' if success else 'FAIL', 200 if success else 400


# =============================================
# API: 支付回调（支付宝异步通知）
# =============================================
@shop_public_bp.route('/api/pay/notify', methods=['POST'])
def api_pay_notify():
    """支付宝异步通知回调"""
    try:
        _pm = __import__('flask').current_app.extensions.get('plugin_manager')
        _payment = _pm.get_instance('payment') if (_pm and _pm.is_enabled('payment')) else None
        if _payment:
            verify_fn = _payment.verify_notify
            confirm_fn = _payment.confirm_shop_order
        else:
            raise RuntimeError('plugin not available')
    except Exception:
        from services.payment_service import verify_notify as verify_fn, confirm_shop_order as confirm_fn
    data = request.form.to_dict()
    trade_status = data.get('trade_status', '')
    order_id = data.get('out_trade_no', '')
    trade_no = data.get('trade_no', '')
    if trade_status != 'TRADE_SUCCESS':
        return 'failure'
    if not verify_fn(data):
        return 'failure'
    success, msg = confirm_fn(order_id, trade_no)
    return 'success' if success else 'failure'


# =============================================
# API: 查询支付状态
# =============================================
@shop_public_bp.route('/api/pay/status/<oid>', methods=['GET'])
def api_pay_status(oid):
    """查询订单支付状态"""
    payload, err = _require_user()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute(
            'SELECT status, paid_at, payment_method, payment_trade_no FROM order_items WHERE order_id=%s',
            (oid,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
    return jsonify({
        'success': True,
        'data': {
            'status': row['status'],
            'paid_at': row.get('paid_at', ''),
            'payment_method': row.get('payment_method', ''),
        }
    })


# =============================================
# API: 优惠券验证（已迁移至插件: plugins/coupons/）
# =============================================
@shop_public_bp.route('/api/coupon/validate', methods=['POST'])
def api_validate_coupon():
    """桥接到插件引擎"""
    try:
        from plugins.coupons import get_engine
        engine = get_engine()
        if engine:
            payload, err = _require_user()
            if err:
                return err
            uid = payload['user_id']
            if not _check_rate_limit(uid, 'coupon', max_requests=30, window=60):
                return jsonify({'success': False, 'error': '操作太频繁'}), 429
            data = request.get_json() or {}
            result = engine.validate(
                code=data.get('code', '').strip().upper(),
                amount=_safe_float(data.get('amount', 0)),
                user_id=uid,
                quantity=_safe_int(data.get('quantity', 0)),
                product_id=data.get('product_id'),
            )
            if not result['valid']:
                return jsonify({'success': False, 'error': result['error']}), 400
            cpn = result['coupon']
            return jsonify({
                'success': True,
                'data': {
                    'id': cpn['id'],
                    'code': cpn['code'],
                    'name': cpn.get('name', cpn['code']),
                    'coupon_type': cpn['coupon_type'],
                    'coupon_category': cpn.get('coupon_category', 'general'),
                    'value': cpn['value'],
                    'discount': result['discount']
                }
            })
    except Exception:
        pass
    return jsonify({'success': False, 'error': '优惠券服务不可用'}), 503
