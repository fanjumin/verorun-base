#!/usr/bin/env python3
"""Admin Routes -- site management panel"""
import sys, os, json, socket, time
from datetime import datetime, timedelta

# ═══ Cache stdlib platform BEFORE inserting project root into sys.path ═══
# Prevents project's platform/ directory from shadowing stdlib platform module
import platform as _stdlib_platform
_ = _stdlib_platform.system

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from flask import Blueprint, request, jsonify
from i18n import _
from models import get_db
from plugin_manager.hooks import get_hook_registry

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Dashboard 内存缓存（避免 SQLite 锁竞争导致 60s+ 超时）
_dash_cache = {'data': None, 'ts': 0, 'ttl': 30}
# 各查询组独立缓存（按 key 单独刷新，不互相影响）
_query_cache = {}
# 通用 GET 请求内存缓存（5 秒 TTL），消除重复点击同一模块的等待感
_get_cache = {}

def _cached_get(ttl=5):
    """装饰器：对 GET 请求做内存缓存"""
    from functools import wraps
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if request.method != 'GET':
                return fn(*a, **kw)
            key = request.path + '?' + request.query_string.decode()
            now = time.time()
            entry = _get_cache.get(key)
            if entry and (now - entry['ts']) < ttl:
                from flask import make_response
                return make_response((entry['body'], entry['status']))
            resp = fn(*a, **kw)
            # 提取状态码和 body，重建 Response 缓存
            if hasattr(resp, 'status_code') and resp.status_code == 200:
                _get_cache[key] = {'body': resp.get_data(as_text=True), 'status': 200, 'ts': now}
            elif isinstance(resp, tuple) and len(resp) == 2 and getattr(resp[0], 'status_code', None) == 200:
                _get_cache[key] = {'body': resp[0].get_data(as_text=True), 'status': 200, 'ts': now}
            return resp
        return wrapper
    return deco

def _require_admin():
    """鉴权守卫 — 与 agent_matrix/site_builder 版本对齐：
    1. 优先从 Authorization header 提取 token
    2. 无 header 时回退到 sso_token / tm_token cookie
    3. 使用 JWT is_admin 声明，不再冗余查询数据库
    """
    from services.jwt_service import validate_token
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': _('Requires management permissions')}), 401)
    return {'user_id': payload['user_id'], 'nickname': ''}, None


def _log(admin_id, action, target_type="", target_id="", detail=""):
    ip = request.remote_addr or ''
    with get_db() as conn:
        conn.execute(
            'INSERT INTO admin_logs (admin_id, action, target_type, target_id, detail, ip_address) VALUES (%s,%s,%s,%s,%s,%s)',
            (admin_id, action, target_type, target_id, detail, ip)
        )
        conn.commit()


@admin_bp.route('/logout', methods=['POST'])
def admin_logout():
    """管理员退出登录"""
    admin, err = _require_admin()
    if err:
        return err
    _log(admin['user_id'], 'logout', 'admin', '', chr(39)+chr(39))
    return jsonify({'success': True})


def _qcached(key, ttl=10):
    """查询级缓存装饰器（防重复计算，只缓存非 None/非 [] 的结果）"""
    def deco(fn):
        def wrapper(*a, **kw):
            now = time.time()
            entry = _query_cache.get(key)
            if entry and (now - entry['ts']) < ttl:
                return entry['val']
            val = fn(*a, **kw)
            if val is not None and val != []:
                _query_cache[key] = {'val': val, 'ts': now}
            return val
        return wrapper
    return deco

def _build_dashboard_data(conn):
    """执行所有 Dashboard SQL 查询，返回 data dict（可以被 API 和模板预渲染共用）"""
    data = {
        'monthly_revenue': 0,
        'pending_posts': 0,
        'pending_contacts': 0,
        'total_users': 0,
        'active_users': 0,
        'today_new_users': 0,
        'total_agents': 0,
        'active_agents': 0,
        'today_calls': 0,
        'total_calls': 0,
        'active_subscriptions': 0,
        'total_orders': 0,
        'pending_reviews': 0,
        'today_failed_tasks': 0,
        'total_products': 0,
        'pending_shipments': 0,
        'published_posts': 0,
        'draft_posts': 0,
        'open_tickets': 0,
        'urgent_tickets': 0,
        'pending_feedback': 0,
        'trend_30d': [],
        'revenue_trend_30d': [],
    }
    _query_cache_ctx = {}

    def _safe(sql, params=()):
        try: return conn.execute(sql, params).fetchone()
        except:
            try: conn._conn.rollback()
            except: pass
            return None

    def _safe_all(sql, params=()):
        try: return conn.execute(sql, params).fetchall()
        except:
            try: conn._conn.rollback()
            except: pass
            return []

    def _qcached(key, ttl=10):
        def deco(fn):
            def wrapper(*a, **kw):
                now = time.time()
                entry = _query_cache_ctx.get(key)
                if entry and (now - entry['ts']) < ttl:
                    return entry['val']
                val = fn(*a, **kw)
                if val is not None and val != []:
                    _query_cache_ctx[key] = {'val': val, 'ts': now}
                return val
            return wrapper
        return deco

    # --- Core metrics ---
    try:
        u = conn.execute("SELECT COUNT(*) as c, COALESCE(SUM(active),0) as a, COALESCE(SUM(CASE WHEN created_at>=CURRENT_DATE THEN 1 ELSE 0 END),0) as n FROM users").fetchone()
        data['total_users'] = u['c']; data['active_users'] = u['a']; data['today_new_users'] = u['n']
    except: pass
    try:
        ta = conn.execute('SELECT COUNT(*) as c FROM agent_matrix').fetchone()
        data['total_agents'] = ta['c'] if ta else 0
        aa = conn.execute("SELECT COUNT(*) as c FROM agent_matrix WHERE is_active=1").fetchone()
        data['active_agents'] = aa['c'] if aa else 0
    except: pass
    try:
        today = _safe("SELECT COUNT(*) as c FROM agent_token_logs WHERE created_at::date=CURRENT_DATE")
        data['today_calls'] = today['c'] if today else 0
        total = _safe('SELECT COUNT(*) as c FROM agent_token_logs')
        data['total_calls'] = total['c'] if total else 0
    except: pass
    try:
        sub = _safe("SELECT COUNT(*) as c FROM subscriptions WHERE status='active'")
        data['active_subscriptions'] = sub['c'] if sub else 0
    except: pass
    try:
        data['total_orders'] = conn.execute('SELECT COUNT(*) as c FROM billing_orders').fetchone()['c']
        mr = conn.execute("SELECT COALESCE(SUM(amount),0) as c FROM billing_orders WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'").fetchone()
        data['monthly_revenue'] = round(mr['c'], 2) if mr else 0
    except: pass
    # --- Action items ---
    try:
        data['pending_posts'] = conn.execute("SELECT COUNT(*) as c FROM agent_experiences WHERE status='pending' OR is_published=0").fetchone()['c']
    except: pass
    try:
        data['pending_reviews'] = (_safe("SELECT COUNT(*) as c FROM processed_contents WHERE status='review'") or {'c':0})['c']
    except: pass
    try:
        data['pending_contacts'] = conn.execute("SELECT COUNT(*) as c FROM contact_messages WHERE status='unread'").fetchone()['c']
    except: pass
    try:
        data['today_failed_tasks'] = (_safe("SELECT COUNT(*) as c FROM execution_logs WHERE status='failed' AND created_at>=CURRENT_DATE") or {'c':0})['c']
    except: pass
    # --- P0 missing data ---
    try:
        data['total_products'] = conn.execute("SELECT COUNT(*) as c FROM shop.products").fetchone()['c']
    except:
        try: conn._conn.rollback()
        except: pass
    try:
        data['pending_shipments'] = conn.execute("SELECT COUNT(*) as c FROM shop.order_items WHERE shipping_status='pending'").fetchone()['c']
    except:
        try: conn._conn.rollback()
        except: pass
    try:
        r = conn.execute("SELECT COUNT(*) as c FROM cms_posts WHERE is_published=true").fetchone()
        data['published_posts'] = r['c'] if r else 0
        r = conn.execute("SELECT COUNT(*) as c FROM cms_posts WHERE is_published=false").fetchone()
        data['draft_posts'] = r['c'] if r else 0
    except:
        try: conn._conn.rollback()
        except: pass
    try:
        data['open_tickets'] = conn.execute("SELECT COUNT(*) as c FROM user_tickets WHERE status='open'").fetchone()['c']
    except:
        try: conn._conn.rollback()
        except: pass
    try:
        data['urgent_tickets'] = conn.execute("SELECT COUNT(*) as c FROM user_tickets WHERE status='open' AND priority='high'").fetchone()['c']
    except:
        try: conn._conn.rollback()
        except: pass
    try:
        data['pending_feedback'] = conn.execute("SELECT COUNT(*) as c FROM user_feedback WHERE status='pending'").fetchone()['c']
    except:
        try: conn._conn.rollback()
        except: pass
    # --- Recent data ---
    try:
        data['recent_users'] = [dict(r) for r in conn.execute(
            "SELECT id, COALESCE(display_name, username, '') as nickname, phone, created_at FROM users ORDER BY created_at DESC LIMIT 5").fetchall()]
    except:
        try: conn._conn.rollback()
        except: pass
    try:
        data['recent_orders'] = [dict(r) for r in conn.execute(
            "SELECT id, user_id, item_desc, amount, status, paid_at FROM billing_orders ORDER BY created_at DESC LIMIT 5").fetchall()]
    except:
        try: conn._conn.rollback()
        except: pass

    # --- Service health (outside DB) ---
    import socket
    from concurrent.futures import ThreadPoolExecutor, as_completed
    services = [('Main',8081),('Platform',8083),('Admin',8084)]
    data['services'] = []
    def _check_service(name, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.15)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            return {'name': name, 'port': port, 'alive': result == 0}
        except: return {'name': name, 'port': port, 'alive': False}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_check_service, n, p): (n, p) for n, p in services}
        for f in as_completed(futures):
            data['services'].append(f.result())

    # --- 收集所有已激活插件注入的仪表盘数据 ---
    data = get_hook_registry().apply_filters('dashboard.data', data, conn=conn)

    return data

@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    admin, err = _require_admin()
    if err:
        return err

    now = time.time()
    if _dash_cache['data'] is not None and (now - _dash_cache['ts']) < _dash_cache['ttl']:
        return jsonify({"success": True, "data": _dash_cache['data']})

    try:
        with get_db() as conn:
            data = _build_dashboard_data(conn)
        if not any(k in data for k in ('total_users','total_agents','active_subscriptions')):
            raise Exception('Core metrics all failed')
        _dash_cache['data'] = data
        _dash_cache['ts'] = time.time()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# 收入看板
# ════════════════════════════════════════════════════════════════

@admin_bp.route('/revenue/dashboard', methods=['GET'])
def revenue_dashboard():
    """收入看板 — 综合收入统计"""
    admin, err = _require_admin()
    if err:
        return err

    try:
        return _revenue_dashboard_data()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Revenue dashboard unavailable: {e}"}), 500


def _revenue_dashboard_data():
    with get_db() as conn:
        # ── 收入汇总 ──
        today = float(conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND date(paid_at)=CURRENT_DATE
        """).fetchone()['rev'] or 0)
        today += float(conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND date(paid_at)=CURRENT_DATE
        """).fetchone()['rev'] or 0)
        today += float(conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND date(paid_at)=CURRENT_DATE
        """).fetchone()['rev'] or 0)

        this_month = float(conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['rev'] or 0)
        this_month += float(conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['rev'] or 0)
        this_month += float(conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['rev'] or 0)

        this_year = float(conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND EXTRACT(YEAR FROM paid_at)=EXTRACT(YEAR FROM NOW())
        """).fetchone()['rev'] or 0)
        this_year += float(conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND EXTRACT(YEAR FROM paid_at)=EXTRACT(YEAR FROM NOW())
        """).fetchone()['rev'] or 0)
        this_year += float(conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND EXTRACT(YEAR FROM paid_at)=EXTRACT(YEAR FROM NOW())
        """).fetchone()['rev'] or 0)

        # ── 上月收入（环比） ──
        last_month = float(conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
        """).fetchone()['rev'] or 0)
        last_month += float(conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
        """).fetchone()['rev'] or 0)
        last_month += float(conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
        """).fetchone()['rev'] or 0)

        # ── 近30天每日收入趋势 ──
        trend = conn.execute("""
            SELECT date(paid_at) as day, SUM(amount) as rev FROM billing_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'
            GROUP BY date(paid_at) ORDER BY day
        """).fetchall()
        trend_map = {r['day']: float(r['rev']) for r in trend}
        # Add subscription orders
        sub_trend = conn.execute("""
            SELECT date(paid_at) as day, COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'
            GROUP BY date(paid_at) ORDER BY day
        """).fetchall()
        for r in sub_trend:
            trend_map[r['day']] = trend_map.get(r['day'], 0.0) + float(r['rev'])
        # Add shop orders
        shop_trend = conn.execute("""
            SELECT date(paid_at) as day, COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'
            GROUP BY date(paid_at) ORDER BY day
        """).fetchall()
        for r in shop_trend:
            trend_map[r['day']] = trend_map.get(r['day'], 0.0) + float(r['rev'])

        # ── 近12月月度收入 ──
        monthly = conn.execute("""
            SELECT TO_CHAR(paid_at, 'YYYY-MM') as ym, SUM(amount) as rev FROM billing_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '12 months'
            GROUP BY ym ORDER BY ym
        """).fetchall()
        monthly_map = {r['ym']: float(r['rev']) for r in monthly}
        sub_monthly = conn.execute("""
            SELECT TO_CHAR(paid_at, 'YYYY-MM') as ym, COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '12 months'
            GROUP BY ym ORDER BY ym
        """).fetchall()
        for r in sub_monthly:
            monthly_map[r['ym']] = monthly_map.get(r['ym'], 0.0) + float(r['rev'])
        shop_monthly = conn.execute("""
            SELECT TO_CHAR(paid_at, 'YYYY-MM') as ym, COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '12 months'
            GROUP BY ym ORDER BY ym
        """).fetchall()
        for r in shop_monthly:
            monthly_map[r['ym']] = monthly_map.get(r['ym'], 0.0) + float(r['rev'])

        # ── 收入按类型分类 ──
        by_type = {}
        raw = conn.execute("""
            SELECT item_type, COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' GROUP BY item_type
        """).fetchall()
        for r in raw:
            by_type[r['item_type']] = by_type.get(r['item_type'], 0) + r['rev']
        sub_raw = conn.execute("""
            SELECT item_type, COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' GROUP BY item_type
        """).fetchall()
        for r in sub_raw:
            by_type[r['item_type']] = by_type.get(r['item_type'], 0) + r['rev']
        shop_raw = conn.execute("""
            SELECT 'shop' as item_type, COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid'
        """).fetchall()
        for r in shop_raw:
            if r['rev'] > 0:
                by_type['shop'] = by_type.get('shop', 0) + r['rev']

        # ── 支付方式分布 ──
        pay_methods = {}
        pm = conn.execute("""
            SELECT payment_method, COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND payment_method!='' GROUP BY payment_method
        """).fetchall()
        for r in pm:
            pay_methods[r['payment_method']] = pay_methods.get(r['payment_method'], 0) + r['rev']

        # ── 订阅数据 (MRR) ──
        mrr = conn.execute("""
            SELECT COALESCE(SUM(
                CASE WHEN s.period='year' THEN sp.price_year/12 ELSE sp.price_month END
            ),0) as mrr FROM subscriptions s
            JOIN subscription_plans sp ON sp.plan_key=s.plan_key
            WHERE s.status IN ('active','trialing')
        """).fetchone()['mrr']
        active_subs = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions WHERE status='active'
        """).fetchone()['c']

        # ── 总付费用户数 ──
        total_paid_users = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as c FROM subscriptions WHERE status='active'
        """).fetchone()['c']

        # ── 总交易额 ──
        total_revenue = conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders WHERE status='paid'
        """).fetchone()['rev']
        total_revenue += (conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders WHERE status='paid'
        """).fetchone()['rev'] or 0)
        total_revenue += (conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items WHERE status='paid'
        """).fetchone()['rev'] or 0)

        # ── 待处理退款 ──
        pending_refunds = conn.execute("""
            SELECT COUNT(*) as c FROM billing_orders
            WHERE status='refund_pending'
        """).fetchone()['c']

        # ── 流失率计算 ──
        # 本月流失率 = 本月取消数 / 月初活跃数
        # 本月取消数
        canceled = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE status='canceled'
              AND TO_CHAR(canceled_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()
        active_start_month = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE status IN ('active','trialing')
              AND (canceled_at IS NULL OR canceled_at >= DATE_TRUNC('month', CURRENT_DATE)::DATE)
              AND created_at < DATE_TRUNC('month', CURRENT_DATE)::DATE
        """).fetchone()['c'] or 1
        churn_rate = round((canceled['c'] / active_start_month) * 100, 2) if active_start_month > 0 else 0

        # 上月流失率
        last_month_canceled = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE status='canceled'
              AND TO_CHAR(canceled_at, 'YYYY-MM')=TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
        """).fetchone()['c']
        last_month_active_start = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE status IN ('active','trialing')
              AND canceled_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')::DATE
              AND created_at < DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')::DATE
        """).fetchone()['c'] or 1
        last_churn_rate = round((last_month_canceled / last_month_active_start) * 100, 2) if last_month_active_start > 0 else 0

        # ── 近12月月度流失率趋势 ──
        churn_trend = []
        for i in range(11, -1, -1):
            ym_start = f"DATE_TRUNC('month', CURRENT_DATE - INTERVAL '{i} months')::DATE"
            ym_end = f"DATE_TRUNC('month', CURRENT_DATE - INTERVAL '{i-1} months')::DATE"
            m_canceled = conn.execute(f"""
                SELECT COUNT(*) as c FROM subscriptions
                WHERE status='canceled'
                  AND canceled_at >= {ym_start} AND canceled_at < {ym_end}
            """).fetchone()['c']
            m_active_start = conn.execute(f"""
                SELECT COUNT(*) as c FROM subscriptions
                WHERE status IN ('active','trialing')
                  AND (canceled_at IS NULL OR canceled_at >= {ym_start})
                  AND created_at < {ym_start}
            """).fetchone()['c'] or 1
            m_churn = round((m_canceled / m_active_start) * 100, 2)
            ym_label = (datetime.now().replace(day=1) - timedelta(days=30*i)).strftime('%Y-%m')
            churn_trend.append({'ym': ym_label, 'churn_rate': m_churn, 'canceled': m_canceled, 'active_start': m_active_start})

        # ── 近30天活跃订阅趋势 ──
        sub_trend_30d = []
        for i in range(29, -1, -1):
            day = (datetime.now() - timedelta(days=i)).date().isoformat()
            active_count = conn.execute(f"""
                SELECT COUNT(*) as c FROM subscriptions
                WHERE status IN ('active','trialing')
                  AND date(created_at) <= %s
                  AND (canceled_at IS NULL OR date(canceled_at) > %s)
            """, (day, day)).fetchone()['c']
            sub_trend_30d.append({'day': day, 'active_count': active_count})

        # 本月新增订阅（含 trialing 和 past_due 中本月创建的）
        new_this_month = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE TO_CHAR(created_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['c'] + conn.execute("""
            SELECT COUNT(*) as c FROM subscription_orders
            WHERE TO_CHAR(created_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM') AND item_type='new' AND status='paid'
        """).fetchone()['c']

        # 本月已过期
        expired_this_month = conn.execute("""
            SELECT COUNT(*) as c FROM subscriptions
            WHERE status='expired'
              AND TO_CHAR(updated_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['c']

    return jsonify({"success": True, "data": {
        'summary': {
            'today_revenue': round(today, 2),
            'this_month': round(this_month, 2),
            'last_month': round(last_month, 2),
            'this_year': round(this_year, 2),
            'total_revenue': round(total_revenue, 2),
            'month_change': round(this_month - last_month, 2),
            'month_change_pct': round(((this_month - last_month) / last_month * 100) if last_month > 0 else 0, 1),
        },
        'subscriptions': {
            'mrr': round(float(mrr) / 100, 2),
            'active': active_subs,
            'total_paid_users': total_paid_users,
            'new_this_month': new_this_month,
            'canceled_this_month': canceled['c'],
            'expired_this_month': expired_this_month,
            'churn_rate': churn_rate,
            'last_churn_rate': last_churn_rate,
            'churn_trend_12m': churn_trend,
            'active_trend_30d': sub_trend_30d,
        },
        'pending_refunds': pending_refunds,
        'trend_30d': [{'day': k, 'revenue': round(v, 2)} for k, v in sorted(trend_map.items())],
        'monthly_12m': [{'ym': k, 'revenue': round(v, 2)} for k, v in sorted(monthly_map.items())],
        'by_type': [{'type': k, 'revenue': round(v, 2)} for k, v in sorted(by_type.items(), key=lambda x: -x[1])],
        'pay_methods': [{'method': k, 'revenue': round(v, 2)} for k, v in sorted(pay_methods.items(), key=lambda x: -x[1])],
    }})



# Import split route modules to register all routes on admin_bp
from . import admin_users, admin_content, admin_system  # noqa: E402,F401
