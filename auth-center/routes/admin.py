#!/usr/bin/env python3
"""Admin Routes -- site management panel"""
import sys, os, json, socket, time
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from flask import Blueprint, request, jsonify
from i18n import _
from models import get_db

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
        return None, (jsonify({'success': False, 'error': _('需要管理权限')}), 401)
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
    }
    _query_cache_ctx = {}

    def _safe(sql, params=()):
        try: return conn.execute(sql, params).fetchone()
        except: return None

    def _safe_all(sql, params=()):
        try: return conn.execute(sql, params).fetchall()
        except: return []

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
        ta = conn.execute('SELECT COUNT(*) as c FROM user_agents').fetchone()
        data['total_agents'] = ta['c'] if ta else 0
        aa = conn.execute("SELECT COUNT(*) as c FROM user_agents WHERE status='active'").fetchone()
        data['active_agents'] = aa['c'] if aa else 0
    except: pass
    try:
        tdc_old = _safe("SELECT COALESCE(SUM(calls_today),0) as c FROM api_keys WHERE last_reset=CURRENT_DATE")
        tdc_new = _safe("SELECT COALESCE(SUM(calls_today),0) as c FROM agent_api_keys WHERE last_reset=CURRENT_DATE")
        data['today_calls'] = (tdc_old['c'] if tdc_old else 0) + (tdc_new['c'] if tdc_new else 0)
        tc_old = _safe('SELECT COALESCE(SUM(calls_total),0) as c FROM api_keys')
        tc_new = _safe('SELECT COALESCE(SUM(calls_total),0) as c FROM agent_api_keys')
        data['total_calls'] = (tc_old['c'] if tc_old else 0) + (tc_new['c'] if tc_new else 0)
    except: pass
    try:
        sub = _safe("SELECT COUNT(*) as c FROM subscriptions WHERE status='active'")
        data['active_subscriptions'] = sub['c'] if sub else 0
    except: pass
    try:
        data['total_orders'] = conn.execute('SELECT COUNT(*) as c FROM billing_orders').fetchone()['c']
        mr = conn.execute("SELECT COALESCE(SUM(amount),0) as c FROM billing_orders WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'").fetchone()
        data['monthly_revenue'] = mr['c'] if mr else 0
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
    # --- Recent data ---
    try:
        data['recent_users'] = [dict(r) for r in conn.execute(
            "SELECT id, COALESCE(display_name, username, '') as nickname, phone, created_at FROM users ORDER BY created_at DESC LIMIT 5").fetchall()]
    except: pass
    try:
        data['recent_orders'] = [dict(r) for r in conn.execute(
            "SELECT id, user_id, item_desc, amount, status, paid_at FROM billing_orders ORDER BY created_at DESC LIMIT 5").fetchall()]
    except: pass
    # --- Analytics snapshot ---
    @_qcached('dash_pvuv', ttl=10)
    def _qpvuv(): return _safe("SELECT pv, uv FROM analytics_daily_stats WHERE date=CURRENT_DATE")
    pvuv = _qpvuv()
    data['today_pv'] = pvuv['pv'] if pvuv else 0
    data['today_uv'] = pvuv['uv'] if pvuv else 0
    @_qcached('dash_online', ttl=5)
    def _qonline(): return _safe("SELECT COUNT(DISTINCT visitor_hash) as c FROM analytics_visitor_sessions WHERE last_active_at>=NOW() - INTERVAL '5 minutes'")
    online = _qonline()
    data['online_now'] = online['c'] if online else 0
    @_qcached('dash_toppages', ttl=10)
    def _qpages(): return _safe_all("SELECT path, pv FROM analytics_page_stats WHERE date=CURRENT_DATE ORDER BY pv DESC LIMIT 3")
    data['top_pages'] = [{'path': r['path'], 'pv': r['pv']} for r in _qpages()]
    # --- Token 用量 ---
    @_qcached('dash_tokens', ttl=15)
    def _qtokens():
        r = _safe("SELECT COALESCE(SUM(total_tokens),0) as c FROM agent_token_daily WHERE stat_date=CURRENT_DATE")
        return r['c'] if r else 0
    data['today_tokens'] = _qtokens()
    @_qcached('dash_topagents', ttl=15)
    def _qtopagents():
        return [dict(r) for r in _safe_all(
            "SELECT t.agent_id, t.agent_name, t.total_tokens as total "
            "FROM agent_token_daily t WHERE t.stat_date=CURRENT_DATE ORDER BY t.total_tokens DESC LIMIT 3")]
    data['top_token_agents'] = _qtopagents()

    # --- Service health (outside DB) ---
    import socket
    from concurrent.futures import ThreadPoolExecutor, as_completed
    services = [('Platform',8081),('Platform',8083),('Admin',8084)]
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
        today = conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND date(paid_at)=CURRENT_DATE
        """).fetchone()['rev']
        today += (conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND date(paid_at)=CURRENT_DATE
        """).fetchone()['rev'] or 0)
        today += (conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND date(paid_at)=CURRENT_DATE
        """).fetchone()['rev'] or 0)

        this_month = conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['rev']
        this_month += (conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['rev'] or 0)
        this_month += (conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW(), 'YYYY-MM')
        """).fetchone()['rev'] or 0)

        this_year = conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND EXTRACT(YEAR FROM paid_at)=EXTRACT(YEAR FROM NOW())
        """).fetchone()['rev']
        this_year += (conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND EXTRACT(YEAR FROM paid_at)=EXTRACT(YEAR FROM NOW())
        """).fetchone()['rev'] or 0)
        this_year += (conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND EXTRACT(YEAR FROM paid_at)=EXTRACT(YEAR FROM NOW())
        """).fetchone()['rev'] or 0)

        # ── 上月收入（环比） ──
        last_month = conn.execute("""
            SELECT COALESCE(SUM(amount),0) as rev FROM billing_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
        """).fetchone()['rev']
        last_month += (conn.execute("""
            SELECT COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
        """).fetchone()['rev'] or 0)
        last_month += (conn.execute("""
            SELECT COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND TO_CHAR(paid_at, 'YYYY-MM')=TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')
        """).fetchone()['rev'] or 0)

        # ── 近30天每日收入趋势 ──
        trend = conn.execute("""
            SELECT date(paid_at) as day, SUM(amount) as rev FROM billing_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'
            GROUP BY date(paid_at) ORDER BY day
        """).fetchall()
        trend_map = {r['day']: r['rev'] for r in trend}
        # Add subscription orders
        sub_trend = conn.execute("""
            SELECT date(paid_at) as day, COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'
            GROUP BY date(paid_at) ORDER BY day
        """).fetchall()
        for r in sub_trend:
            trend_map[r['day']] = trend_map.get(r['day'], 0) + r['rev']
        # Add shop orders
        shop_trend = conn.execute("""
            SELECT date(paid_at) as day, COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '30 days'
            GROUP BY date(paid_at) ORDER BY day
        """).fetchall()
        for r in shop_trend:
            trend_map[r['day']] = trend_map.get(r['day'], 0) + r['rev']

        # ── 近12月月度收入 ──
        monthly = conn.execute("""
            SELECT TO_CHAR(paid_at, 'YYYY-MM') as ym, SUM(amount) as rev FROM billing_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '12 months'
            GROUP BY ym ORDER BY ym
        """).fetchall()
        monthly_map = {r['ym']: r['rev'] for r in monthly}
        sub_monthly = conn.execute("""
            SELECT TO_CHAR(paid_at, 'YYYY-MM') as ym, COALESCE(SUM(amount_fen)/100.0,0) as rev FROM subscription_orders
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '12 months'
            GROUP BY ym ORDER BY ym
        """).fetchall()
        for r in sub_monthly:
            monthly_map[r['ym']] = monthly_map.get(r['ym'], 0) + r['rev']
        shop_monthly = conn.execute("""
            SELECT TO_CHAR(paid_at, 'YYYY-MM') as ym, COALESCE(SUM(subtotal),0) as rev FROM order_items
            WHERE status='paid' AND paid_at>=NOW() - INTERVAL '12 months'
            GROUP BY ym ORDER BY ym
        """).fetchall()
        for r in shop_monthly:
            monthly_map[r['ym']] = monthly_map.get(r['ym'], 0) + r['rev']

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


@admin_bp.route('/users', methods=['GET'])
@_cached_get(ttl=3)
def user_list():
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("search", "").strip()
    tier_filter = request.args.get("tier", "").strip()
    industry = request.args.get("industry", "").strip()
    occupation = request.args.get("occupation", "").strip()
    region = request.args.get("region", "").strip()
    offset = (page - 1) * limit
    where = []
    params = []
    if search:
        where.append("(u.phone LIKE %s OR COALESCE(u.display_name, u.username) LIKE %s OR u.email LIKE %s)")
        s = '%' + search + '%'
        params.extend([s, s, s])
    if tier_filter:
        where.append('a.tier=%s')
        params.append(tier_filter)
    if industry:
        where.append("p.industry LIKE %s")
        params.append('%' + industry + '%')
    if occupation:
        where.append("p.occupation LIKE %s")
        params.append('%' + occupation + '%')
    if region:
        where.append("(p.province LIKE %s OR p.city LIKE %s OR p.district LIKE %s)")
        r = '%' + region + '%'
        params.extend([r, r, r])
    wsql = 'WHERE ' + ' AND '.join(where) if where else ''
    from_sql = ("FROM users u "
                "LEFT JOIN user_profiles p ON u.id=p.user_id "
                "LEFT JOIN user_addresses pa ON u.id=pa.user_id AND pa.is_default=1 AND pa.status=1")
    if industry or occupation or region:
        # If filtering, only join profiles (address join for region)
        pass
    sql = ("SELECT u.id, u.phone, COALESCE(u.display_name, u.username) as nickname, u.email, u.wechat_nickname, "
           "COALESCE((SELECT COUNT(*) FROM user_agents WHERE user_id=u.id),0) as agent_count, "
           "'' as agent_nickname, u.is_admin, u.active, u.created_at, u.last_login, "
           "'' as tier, '' as tier_expire_at, "
           "u.verified_by, u.verified_at, "
           "COALESCE(p.industry,'') as industry, COALESCE(p.occupation,'') as occupation "
           + from_sql + ' ' + wsql + ' GROUP BY u.id ORDER BY u.created_at DESC LIMIT %s OFFSET %s')
    csql = 'SELECT COUNT(DISTINCT u.id) as c ' + from_sql + ' ' + wsql
    with get_db() as conn:
        total = conn.execute(csql, params).fetchone()
        rows = conn.execute(sql, params + [limit, offset]).fetchall()
    return jsonify({"success": True, "data": {
        'total': total['c'], 'page': page, 'limit': limit,
        'users': [dict(r) for r in rows],
    }})


@admin_bp.route('/users/<int:uid>', methods=['GET'])
def user_detail(uid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        user = conn.execute("SELECT id, username, phone, phone_verified, email, COALESCE(display_name, username, '') as nickname, "
                            "wechat_nickname, avatar_url, "
                            "verified_by, verified_at, display_name, "
                            "'' as agent_id, '' as agent_nickname, '' as agent_avatar_url, "
                            "is_admin, active, created_at, last_login "
                            "FROM users WHERE id=%s", (uid,)).fetchone()
        if not user:
            return jsonify({'success': False, 'error': _('用户不存在')}), 404
        auths = conn.execute('SELECT app_name, tier, tier_expire_at, calls_today, calls_total FROM app_authorizations WHERE user_id=%s', (uid,)).fetchall()
        orders = conn.execute('SELECT id, order_no, amount, item_type, item_desc, status, created_at FROM billing_orders WHERE user_id=%s ORDER BY created_at DESC LIMIT 10', (uid,)).fetchall()
    return jsonify({'success': True, 'data': {'user': dict(user), 'authorizations': [dict(a) for a in auths], 'orders': [dict(o) for o in orders]}})

@admin_bp.route('/users/<int:uid>/status', methods=['PUT'])
def user_status(uid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    active = data.get('active', 1)
    with get_db() as conn:
        conn.execute('UPDATE users SET active=%s WHERE id=%s', (1 if active else 0, uid))
        conn.commit()
    _log(admin['user_id'], 'ban_user' if not active else 'activate_user', 'user', str(uid))
    return jsonify({'success': True, 'message': _('状态已更新')})

# PUT /admin/users/<int:uid>/verify — 管理员手动标记用户为已实名（合规v2：不存储身份证号）
@admin_bp.route('/users/<int:uid>/verify', methods=['PUT'])
def admin_verify_user(uid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    real_name = (data.get('real_name') or '').strip()
    if not real_name:
        return jsonify({'success': False, 'error': _('姓名不能为空')}), 400
    with get_db() as conn:
        user = conn.execute('SELECT id, is_real_name_verified FROM users WHERE id=%s', (uid,)).fetchone()
        if not user:
            return jsonify({'success': False, 'error': _('用户不存在')}), 404
        if user['is_real_name_verified']:
            return jsonify({'success': False, 'error': _('用户已完成实名认证')}), 400
        # 合规v2：只写 display_name + 认证标记，不存储身份证号
        conn.execute(
            'UPDATE users SET display_name=%s, verified_by=%s, verified_at=%s, is_real_name_verified=1, real_name_verified_at=%s WHERE id=%s',
            (real_name, 'manual', now_iso(), now_iso(), uid)
        )
        conn.commit()
    _log(admin['user_id'], 'verify_user', 'user', str(uid))
    return jsonify({'success': True, 'message': _('实名认证完成（手动标记，未存储身份证信息）')})


# GET /admin/users/<int:uid>/profile — admin查看用户扩展资料+收货地址
@admin_bp.route('/users/<int:uid>/profile', methods=['GET'])
def user_profile_admin(uid):
    admin, err = _require_admin()
    if err:
        return err
    import json as _json
    with get_db() as conn:
        prof = conn.execute('''
            SELECT up.*, ind.name AS industry_name, co.name AS career_name
            FROM user_profiles up
            LEFT JOIN industries ind ON up.industry_id = ind.id
            LEFT JOIN career_options co ON up.career_id = co.id
            WHERE up.user_id=%s
        ''', (uid,)).fetchone()
        addrs = conn.execute('''
            SELECT ua.*,
                p.name as province_name,
                c.name as city_name,
                d.name as district_name,
                s.name as street_name
            FROM user_addresses ua
            LEFT JOIN regions p ON ua.province_code = p.code
            LEFT JOIN regions c ON ua.city_code = c.code
            LEFT JOIN regions d ON ua.district_code = d.code
            LEFT JOIN regions s ON ua.street_code = s.code
            WHERE ua.user_id=%s AND ua.status=1
            ORDER BY ua.is_default DESC, ua.created_at DESC
        ''', (uid,)).fetchall()

    if prof:
        p = dict(prof)
        try:
            p['interests'] = _json.loads(p.get('interests', '[]'))
        except Exception:
            p['interests'] = []
        # 兼容admin.html前端字段名
        p.setdefault('industry_id', None)
        p.setdefault('career_id', None)
        p.setdefault('industry_name', '')
        p.setdefault('career_name', '')
    else:
        p = {
            'user_id': uid, 'gender': '', 'birth_date': None,
            'age_group': '', 'occupation': '', 'industry': '',
            'industry_id': None, 'career_id': None,
            'industry_name': '', 'career_name': '',
            'interests': [], 'bio': '', 'created_at': '', 'updated_at': ''
        }

    # 转换地址列表为前端需要的字段名（province/city/district -> province_name等）
    addr_list = []
    for a in addrs:
        ad = dict(a)
        ad['province'] = ad.pop('province_name', '') or ''
        ad['city'] = ad.pop('city_name', '') or ''
        ad['district'] = ad.pop('district_name', '') or ''
        addr_list.append(ad)

    return jsonify({'success': True, 'data': {
        'profile': p, 'addresses': addr_list
    }})


# GET /admin/users/export — 脱敏导出用户列表
@admin_bp.route('/agents', methods=['GET'])
@_cached_get(ttl=3)
def agent_list():
    """Legacy endpoint — delegates to new user_agents query (2026-05-10)"""
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', chr(39)+chr(39)).strip()
    offset = (page - 1) * limit
    w = ''
    params = []
    if search:
        w = "WHERE (ua.agent_name LIKE %s OR COALESCE(u.display_name, u.username) LIKE %s)"
        s = '%' + search + '%'
        params.extend([s, s])
    with get_db() as conn:
        total = conn.execute(
            'SELECT COUNT(*) as c FROM user_agents ua LEFT JOIN users u ON ua.user_id=u.id ' + w,
            params
        ).fetchone()
        rows = conn.execute(
            'SELECT ua.id, ua.agent_name, ua.agent_type, ua.status, ua.created_at, '
            "u.id as user_id, COALESCE(u.display_name, u.username) as user_name, u.phone "
            'FROM user_agents ua LEFT JOIN users u ON ua.user_id=u.id ' +
            w + ' ORDER BY ua.created_at DESC LIMIT %s OFFSET %s',
            params + [limit, offset]
        ).fetchall()
    return jsonify({'success': True, 'data': {'total': total['c'], 'page': page, 'limit': limit, 'agents': [dict(r) for r in rows]}})


@admin_bp.route('/posts', methods=['GET'])
@_cached_get(ttl=3)
def post_list():
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    sf = request.args.get('status', chr(39)+chr(39)).strip()
    offset = (page - 1) * limit
    w = []
    p = []
    if sf:
        w.append('e.status=%s')
        p.append(sf)
    wsql = ('WHERE ' + ' AND '.join(w)) if w else ''
    sql = 'SELECT e.id, e.title, e.category, e.status, e.is_published, e.like_count, e.view_count, e.created_at, e.agent_id, COALESCE(u.display_name, u.username) as user_name FROM agent_experiences e LEFT JOIN users u ON e.user_id=u.id ' + wsql + ' ORDER BY e.created_at DESC LIMIT %s OFFSET %s'
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM agent_experiences e ' + wsql, p).fetchone()
        rows = conn.execute(sql, p + [limit, offset]).fetchall()
    return jsonify({'success': True, 'data': {'total': total['c'], 'page': page, 'limit': limit, 'posts': [dict(r) for r in rows]}})


@admin_bp.route('/posts/<int:pid>/review', methods=['PUT'])
def review_post(pid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    status = data.get('status', 'approved')
    pub = 1 if status == 'approved' else 0
    with get_db() as conn:
        conn.execute("UPDATE agent_experiences SET status=%s, is_published=%s, updated_at=NOW() WHERE id=%s", (status, pub, pid))
        conn.commit()
    _log(admin['user_id'], 'review_post', 'post', str(pid), 'Status: ' + status)
    return jsonify({'success': True, 'message': _('审核完成')})


@admin_bp.route('/contacts', methods=['GET'])
@_cached_get(ttl=3)
def contact_list():
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM contact_messages').fetchone()
        rows = conn.execute("SELECT id, name, email, subject, message, status, created_at FROM contact_messages ORDER BY CASE status WHEN 'unread' THEN 0 ELSE 1 END, created_at DESC LIMIT %s OFFSET %s", (limit, offset)).fetchall()
    return jsonify({'success': True, 'data': {'total': total['c'], 'page': page, 'limit': limit, 'contacts': [dict(r) for r in rows]}})


@admin_bp.route('/api-keys', methods=['GET'])
@_cached_get(ttl=3)
def api_key_list():
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM api_keys').fetchone()
        rows = conn.execute("SELECT k.id, k.name, k.key_prefix, k.calls_today, k.calls_total, k.active, k.created_at, COALESCE(u.display_name, u.username, '') as user_name, u.id as user_id FROM api_keys k LEFT JOIN users u ON k.user_id=u.id ORDER BY k.created_at DESC LIMIT %s OFFSET %s", (limit, offset)).fetchall()
    return jsonify({'success': True, 'data': {'total': total['c'], 'page': page, 'limit': limit, 'keys': [dict(r) for r in rows]}})


@admin_bp.route('/api-keys/<int:kid>', methods=['DELETE'])
def revoke_key(kid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('UPDATE api_keys SET active=0 WHERE id=%s', (kid,))
        conn.commit()
    _log(admin['user_id'], 'revoke_api_key', 'api_key', str(kid))
    return jsonify({'success': True, 'message': _('密钥已吊销')})


@admin_bp.route('/logs', methods=['GET'])
@_cached_get(ttl=3)
def admin_logs():
    admin, err = _require_admin()
    if err:
        return err
    limit = request.args.get('limit', 50, type=int)
    with get_db() as conn:
        rows = conn.execute('SELECT l.id, l.action, l.target_type, l.target_id, l.detail, l.ip_address, l.created_at, COALESCE(u.display_name, u.username) as admin_name FROM admin_logs l LEFT JOIN users u ON l.admin_id=u.id ORDER BY l.created_at DESC LIMIT %s', (limit,)).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})



# =============================================
# Agent Matrix management
# =============================================
@admin_bp.route('/agent-matrix', methods=['GET'])
def agent_matrix_list():
    admin, err = _require_admin()
    if err:
        return err
    type_filter = request.args.get('type', chr(39)+chr(39))
    with get_db() as conn:
        if type_filter:
            rows = conn.execute('SELECT * FROM agents WHERE type=%s ORDER BY type, id', (type_filter,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM agents ORDER BY type, id').fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/agent-matrix', methods=['POST'])
def agent_matrix_create():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    alias = (data.get('alias', chr(39)+chr(39)) or '')[:12]
    mission = (data.get('mission', chr(39)+chr(39)) or '')[:64]
    prompt = (data.get('system_prompt', chr(39)+chr(39)) or '')[:3000]
    model_provider_id = data.get('provider_model_id')  # new field name
    if model_provider_id is None:
        model_provider_id = data.get('model_provider_id')  # backward compat
    with get_db() as conn:
        row = conn.execute(
            "INSERT INTO agents (type, alias, mission, system_prompt, provider_model_id) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (data.get('type', 'child'), alias, mission, prompt, model_provider_id)
        ).fetchone()
        conn.commit()
        aid = row['id']
    _log(admin['user_id'], 'create_agent', 'agent', str(aid), alias)
    return jsonify({'success': True, 'message': _('Agent 已创建'), 'id': aid})


@admin_bp.route('/agent-matrix/<int:aid>', methods=['PUT'])
def agent_matrix_update(aid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    fields = []
    values = []
    for key in ['type', 'alias', 'mission', 'system_prompt', 'provider_model_id', 'is_active']:
        if key in data:
            fields.append(key + '=%s')
            values.append(data[key])
    if not fields:
        return jsonify({'success': False, 'error': _('没有要更新的字段')}), 400
    fields.append("updated_at=NOW()")
    values.append(aid)
    with get_db() as conn:
        conn.execute('UPDATE agents SET ' + ','.join(fields) + ' WHERE id=%s', values)
        conn.commit()
    _log(admin['user_id'], 'update_agent', 'agent', str(aid))
    return jsonify({'success': True, 'message': _('Agent 已更新')})


@admin_bp.route('/agent-matrix/<int:aid>', methods=['DELETE'])
def agent_matrix_delete(aid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('DELETE FROM agents WHERE id=%s', (aid,))
        conn.commit()
    _log(admin['user_id'], 'delete_agent', 'agent', str(aid))
    return jsonify({'success': True, 'message': _('Agent 已删除')})


@admin_bp.route('/agent-matrix/<int:aid>/test', methods=['POST'])
def agent_matrix_test(aid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    query = data.get('query', chr(39)+chr(39))
    if not query:
        return jsonify({'success': False, 'error': _('请先输入测试消息（不能为空）')}), 400
    with get_db() as conn:
        row = conn.execute('SELECT * FROM agents WHERE id=%s', (aid,)).fetchone()
    if not row:
        return jsonify({'success': False, 'error': _('Agent 不存在')}), 404
    from services.agent_engine import UniversalAgentEngine
    engine = UniversalAgentEngine(dict(row))
    result = engine.ask(query)
    return jsonify({'success': True, 'data': {'response': result}})


# =============================================
# Email management — 已迁移至 plugins/email/routes.py
# 路由前缀 /admin/email/* 由 EmailPlugin 插件注册
# =============================================


# =============================================
# SMS Template Management — 已迁移至 SmsPlugin（插件）
# 插件路由注册于 /admin/sms/templates
# =============================================




# =============================================
# 管理员配置 — Admin Profiles (2026-05-10)
# =============================================

def _require_super_admin():
    """验证当前用户是 super_admin"""
    admin, err = _require_admin()
    if err:
        return None, err
    with get_db() as conn:
        row = conn.execute('SELECT role FROM admin_profiles WHERE user_id=%s', (admin['user_id'],)).fetchone()
    if not row or row['role'] != 'super_admin':
        return None, (jsonify({'success': False, 'error': _('仅超级管理员可执行此操作')}), 403)
    return admin, None


@admin_bp.route('/admins', methods=['GET'])
def admin_list():
    """列出所有管理员（带完整 profile），仅 super_admin 可见"""
    admin, err = _require_super_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute('''
            SELECT u.id, u.phone, COALESCE(u.display_name, u.username), u.email, u.avatar_url, u.active, 
                   u.last_login, u.created_at as registered_at,
                   p.role, p.permissions, p.real_name, p.internal_phone, 
                   p.internal_email, p.notes, p.last_login_ip
            FROM users u 
            JOIN admin_profiles p ON u.id = p.user_id
            WHERE u.is_admin = 1
            ORDER BY p.role, u.id
        ''').fetchall()
    admins = []
    for r in rows:
        d = dict(r)
        try:
            d['permissions'] = __import__('json').loads(d['permissions'] or '[]')
        except Exception:
            d['permissions'] = []
        admins.append(d)
    return jsonify({'success': True, 'data': admins})


@admin_bp.route('/admins/me', methods=['GET'])
def admin_me():
    """当前管理员的个人信息"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('''
            SELECT u.id, u.phone, COALESCE(u.display_name, u.username), u.email, u.avatar_url,
                   p.role, p.permissions, p.real_name, p.internal_phone,
                   p.internal_email, p.notes, p.last_login_ip, p.last_login_at,
                   p.created_at as admin_since
            FROM users u 
            JOIN admin_profiles p ON u.id = p.user_id
            WHERE u.id = %s
        ''', (admin['user_id'],)).fetchone()
    if not row:
        return jsonify({'success': False, 'error': _('管理员配置不存在')}), 404
    d = dict(row)
    try:
        d['permissions'] = __import__('json').loads(d['permissions'] or '[]')
    except Exception:
        d['permissions'] = []
    return jsonify({'success': True, 'data': d})


@admin_bp.route('/admins/me', methods=['PUT'])
def admin_me_update():
    """当前管理员更新自己的个人信息（真实姓名、内部联系方式、备注）"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    fields = []
    params = []
    for key in ('real_name', 'internal_phone', 'internal_email', 'notes'):
        if key in data:
            fields.append(f'{key}=%s')
            params.append(data.get(key, chr(39)+chr(39)).strip())
    if not fields:
        return jsonify({'success': False, 'error': _('没有要更新的字段')}), 400
    params.append(admin['user_id'])
    with get_db() as conn:
        conn.execute(f'UPDATE admin_profiles SET {", ".join(fields)}, updated_at=NOW() WHERE user_id=%s', params)
        conn.commit()
        _log(admin['user_id'], 'update_self', 'admin_profile', str(admin['user_id']))
    return jsonify({'success': True, 'message': _('已更新')})


@admin_bp.route('/admins/me/phone', methods=['PUT'])
def admin_me_phone():
    """当前管理员修改登录手机号 — 需新手机验证码"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    new_phone = data.get('phone', chr(39)+chr(39)).strip()
    code = data.get('code', chr(39)+chr(39)).strip()
    if not new_phone or not code:
        return jsonify({'success': False, 'error': _('手机号和验证码不能为空')}), 400
    from models import get_db
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM sms_codes WHERE phone=%s AND code=%s AND purpose=%s AND used=0 AND expires_at>NOW() ORDER BY id DESC LIMIT 1',
            (new_phone, code, 'change_phone')
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('验证码无效或已过期')}), 400
        # 检查新手机号是否已占用
        existing = conn.execute('SELECT id FROM users WHERE phone=%s AND id!=%s', (new_phone, admin['user_id'])).fetchone()
        if existing:
            return jsonify({'success': False, 'error': _('该手机号已被其他用户绑定')}), 400
        conn.execute('UPDATE sms_codes SET used=1 WHERE id=%s', (row['id'],))
        conn.execute('UPDATE users SET phone=%s, phone_verified=1 WHERE id=%s', (new_phone, admin['user_id']))
        conn.commit()
        _log(admin['user_id'], 'change_phone', 'admin_profile', str(admin['user_id']), _('新手机: {phone}', phone=new_phone))
    return jsonify({'success': True, 'message': _('手机号已更新')})


@admin_bp.route('/admins/<int:uid>', methods=['GET'])
def admin_detail(uid):
    """查看指定管理员详情（super_admin only）"""
    admin, err = _require_super_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('''
            SELECT u.id, u.phone, COALESCE(u.display_name, u.username), u.email, u.avatar_url, u.active, u.last_login,
                   p.role, p.permissions, p.real_name, p.internal_phone,
                   p.internal_email, p.notes, p.last_login_ip, p.last_login_at,
                   p.created_at as admin_since, p.updated_at
            FROM users u 
            JOIN admin_profiles p ON u.id = p.user_id
            WHERE u.id=%s AND u.is_admin=1
        ''', (uid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('管理员不存在')}), 404
        d = dict(row)
        try:
            d['permissions'] = __import__('json').loads(d['permissions'] or '[]')
        except Exception:
            d['permissions'] = []
        # 审计日志
        logs = conn.execute(
            'SELECT id, action, target_type, target_id, detail, ip_address, created_at FROM admin_logs WHERE admin_id=%s ORDER BY created_at DESC LIMIT 30',
            (uid,)
        ).fetchall()
        d['recent_logs'] = [dict(l) for l in logs]
    return jsonify({'success': True, 'data': d})


@admin_bp.route('/admins', methods=['POST'])
def admin_create():
    """将用户提升为管理员（super_admin only）"
    """
    admin, err = _require_super_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    phone = data.get('phone', chr(39)+chr(39)).strip()
    uid = data.get('user_id', 0)
    role = data.get('role', 'admin').strip()
    permissions = data.get('permissions', [])
    real_name = data.get('real_name', chr(39)+chr(39)).strip()[:32]
    notes = data.get('notes', chr(39)+chr(39)).strip()[:256]
    
    if not phone and not uid:
        return jsonify({'success': False, 'error': _('请提供手机号或用户ID')}), 400
    
    with get_db() as conn:
        if uid:
            user = conn.execute('SELECT id, phone, display_name FROM users WHERE id=%s', (uid,)).fetchone()
        else:
            user = conn.execute('SELECT id, phone, display_name FROM users WHERE phone=%s', (phone,)).fetchone()
        
        if not user:
            return jsonify({'success': False, 'error': _('用户不存在')}), 404
        
        if user['id'] == admin['user_id']:
            return jsonify({'success': False, 'error': _('不能提升自己，你已经是管理员')}), 400
        
        existing = conn.execute('SELECT id FROM admin_profiles WHERE user_id=%s', (user['id'],)).fetchone()
        if existing:
            return jsonify({'success': False, 'error': _('{name} 已经是管理员', name=user["display_name"] or user["phone"])}), 400
        
        import json as _json
        permissions_str = _json.dumps(permissions if permissions else [])
        
        conn.execute('UPDATE users SET is_admin=1 WHERE id=%s', (user['id'],))
        conn.execute('''
            INSERT INTO admin_profiles (user_id, role, permissions, real_name, notes, created_by) 
            VALUES (%s,%s,%s,%s,%s,%s)
        ''', (user['id'], role, permissions_str, real_name, notes, admin['user_id']))
        conn.commit()
        _log(admin['user_id'], 'create_admin', 'admin', str(user['id']), f'{user["display_name"] or user["phone"]} ({role})')
    
    return jsonify({'success': True, 'message': _('已将 {name} 提升为管理员', name=user["display_name"] or user["phone"])})


@admin_bp.route('/admins/<int:uid>', methods=['PUT'])
def admin_update(uid):
    """更新管理员信息（super_admin only）"""
    admin, err = _require_super_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    
    # 更新 admin_profiles 表
    pf_fields = []
    pf_params = []
    for key in ('role', 'real_name', 'internal_phone', 'internal_email', 'notes'):
        if key in data:
            pf_fields.append(f'{key}=%s')
            pf_params.append(data.get(key, chr(39)+chr(39)).strip())
    
    # 处理 permissions（JSON数组）
    if 'permissions' in data:
        import json as _json
        pf_fields.append('permissions=%s')
        pf_params.append(_json.dumps(data['permissions']))
    
    # 处理密码（单独字段，不走 profile）—— 仅短信验证码验证
    password = data.get('password', '').strip()
    code = data.get('code', '').strip()
    
    with get_db() as conn:
        # 验证目标确实是管理员
        target = conn.execute('SELECT id, phone, COALESCE(display_name, username) as nickname FROM users WHERE id=%s AND is_admin=1', (uid,)).fetchone()
        if not target:
            return jsonify({'success': False, 'error': _('管理员不存在')}), 404
        
        if uid == admin['user_id'] and 'role' in data and data['role'] != 'super_admin':
            return jsonify({'success': False, 'error': _('不能将自己降级为非超级管理员')}), 400
        
        if pf_fields:
            pf_fields.append("updated_at=NOW()")
            pf_params.append(uid)
            conn.execute(f'UPDATE admin_profiles SET {", ".join(pf_fields)} WHERE user_id=%s', pf_params)
        
        # 修改密码：仅短信验证码验证
        if password:
            if not code:
                return jsonify({'success': False, 'error': _('请输入短信验证码')}), 400
            # 验证 SMS 验证码
            row = conn.execute(
                'SELECT * FROM sms_codes WHERE phone=%s AND code=%s AND purpose=%s AND used=0 AND expires_at>NOW() ORDER BY id DESC LIMIT 1',
                (target['phone'], code, 'modify_password')
            ).fetchone()
            if not row:
                return jsonify({'success': False, 'error': _('验证码无效或已过期')}), 400
            conn.execute('UPDATE sms_codes SET used=1 WHERE id=%s', (row['id'],))
            
            import hashlib, secrets
            salt = secrets.token_hex(8)
            pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            stored = f'pbkdf2:sha256:100000:{salt}:{pw_hash}'
            conn.execute('UPDATE users SET password_hash=%s WHERE id=%s', (stored, uid))
        
        conn.commit()
        _log(admin['user_id'], 'update_admin', 'admin', str(uid), f'role={data.get("role","")}')
    
    return jsonify({'success': True, 'message': _('管理员信息已更新')})


@admin_bp.route('/admins/<int:uid>', methods=['DELETE'])
def admin_delete(uid):
    """将管理员降级为普通用户（super_admin only）"""
    admin, err = _require_super_admin()
    if err:
        return err
    if uid == admin['user_id']:
        return jsonify({'success': False, 'error': _('不能移除自己，请先转移超管权限')}), 400
    with get_db() as conn:
        target = conn.execute('SELECT id, display_name, phone FROM users WHERE id=%s AND is_admin=1', (uid,)).fetchone()
        if not target:
            return jsonify({'success': False, 'error': _('管理员不存在')}), 404
        conn.execute('DELETE FROM admin_profiles WHERE user_id=%s', (uid,))
        conn.execute('UPDATE users SET is_admin=0 WHERE id=%s', (uid,))
        conn.commit()
        _log(admin['user_id'], 'remove_admin', 'admin', str(uid), f'{target["display_name"] or target["phone"]}')
    return jsonify({'success': True, 'message': _('已将 {name} 降为普通用户', name=target["display_name"] or target["phone"])})


@admin_bp.route('/admins/me/avatar', methods=['POST'])
def admin_me_avatar():
    """上传管理员头像 — 800x800 max, 1MB max"""
    admin, err = _require_admin()
    if err:
        return err
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': _('未选择文件')}), 400
    file = request.files['avatar']
    if not file.filename:
        return jsonify({'success': False, 'error': _('文件名为空')}), 400
    
    import os
    # 验证文件大小
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 1024 * 1024:
        return jsonify({'success': False, 'error': _('图片大小不能超过 1MB')}), 400
    
    # 验证图片尺寸
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(file.read()))
        w, h = img.size
        if w > 800 or h > 800:
            return jsonify({'success': False, 'error': _('图片尺寸不能超过 800×800（当前 {w}×{h}）', w=w, h=h)}), 400
        file.seek(0)
    except Exception:
        return jsonify({'success': False, 'error': _('无法解析图片文件，请上传 JPG/PNG 格式')}), 400
    
    # 保存文件
    import uuid
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        ext = '.jpg'
    filename = f'avatar_{admin["user_id"]}_{uuid.uuid4().hex[:8]}{ext}'
    save_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'admin', 'static', 'avatars')
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, filename))
    
    avatar_url = f'/static/avatars/{filename}'
    from models import get_db
    with get_db() as conn:
        conn.execute('UPDATE users SET avatar_url=%s WHERE id=%s', (avatar_url, admin['user_id']))
        conn.commit()
    _log(admin['user_id'], 'update_avatar', 'admin_profile', str(admin['user_id']))
    return jsonify({'success': True, 'data': {'avatar_url': avatar_url}})


# =============================================
# 用户头像管理 (普通用户 + Agent)
# =============================================

@admin_bp.route('/users/<int:uid>/avatar', methods=['POST'])
def user_avatar_upload(uid):
    """上传用户头像 — 512x512 max, 512KB max"""
    admin, err = _require_admin()
    if err:
        return err
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': _('未选择文件')}), 400
    file = request.files['avatar']
    if not file.filename:
        return jsonify({'success': False, 'error': _('文件名为空')}), 400

    # 验证用户存在
    with get_db() as conn:
        user = conn.execute('SELECT id, COALESCE(display_name, username) as nickname FROM users WHERE id=%s', (uid,)).fetchone()
    if not user:
        return jsonify({'success': False, 'error': _('用户不存在')}), 404

    import os
    # 文件大小验证 (512KB)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 512 * 1024:
        return jsonify({'success': False, 'error': _('图片大小不能超过 512KB')}), 400

    # 图片尺寸验证 (512x512)
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(file.read()))
        w, h = img.size
        if w > 512 or h > 512:
            return jsonify({'success': False, 'error': _('图片尺寸不能超过 512×512（当前 {w}×{h}）', w=w, h=h)}), 400
        file.seek(0)
    except Exception:
        return jsonify({'success': False, 'error': _('无法解析图片文件，请上传 JPG/PNG/SVG 格式')}), 400

    # 保存文件
    import uuid
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'):
        ext = '.jpg'
    filename = f'user_{uid}_avatar_{uuid.uuid4().hex[:8]}{ext}'
    save_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'admin', 'static', 'avatars')
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, filename))

    avatar_url = f'/static/avatars/{filename}'
    with get_db() as conn:
        conn.execute('UPDATE users SET avatar_url=%s WHERE id=%s', (avatar_url, uid))
        conn.commit()
    _log(admin['user_id'], 'set_user_avatar', 'user', str(uid))
    return jsonify({'success': True, 'data': {'avatar_url': avatar_url}})


@admin_bp.route('/users/<int:uid>/avatar/default', methods=['PUT'])
def user_avatar_default(uid):
    """为用户设置默认头像 (from library)"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    default_name = data.get('default', chr(39)+chr(39))
    if not default_name:
        return jsonify({'success': False, 'error': _('请指定默认头像文件名')}), 400
    avatar_url = f'/static/avatars/default/users/{default_name}'
    with get_db() as conn:
        conn.execute('UPDATE users SET avatar_url=%s WHERE id=%s', (avatar_url, uid))
        conn.commit()
    _log(admin['user_id'], 'set_user_default_avatar', 'user', str(uid), default_name)
    return jsonify({'success': True, 'data': {'avatar_url': avatar_url}})


@admin_bp.route('/users/<int:uid>/agent-avatar', methods=['POST'])
def user_agent_avatar_upload(uid):
    """上传Agent头像 — 512x512 max, 512KB max"""
    admin, err = _require_admin()
    if err:
        return err
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': _('未选择文件')}), 400
    file = request.files['avatar']
    if not file.filename:
        return jsonify({'success': False, 'error': _('文件名为空')}), 400

    with get_db() as conn:
        user = conn.execute('SELECT id, COALESCE(display_name, username) as nickname FROM users WHERE id=%s', (uid,)).fetchone()
    if not user:
        return jsonify({'success': False, 'error': _('用户不存在')}), 404

    import os
    # 文件大小验证 (512KB)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 512 * 1024:
        return jsonify({'success': False, 'error': _('图片大小不能超过 512KB')}), 400

    # 图片尺寸验证 (512x512)
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(file.read()))
        w, h = img.size
        if w > 512 or h > 512:
            return jsonify({'success': False, 'error': _('图片尺寸不能超过 512×512（当前 {w}×{h}）', w=w, h=h)}), 400
        file.seek(0)
    except Exception:
        return jsonify({'success': False, 'error': _('无法解析图片文件，请上传 JPG/PNG/SVG 格式')}), 400

    # 保存文件
    import uuid
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'):
        ext = '.jpg'
    filename = f'agent_{uid}_avatar_{uuid.uuid4().hex[:8]}{ext}'
    save_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'admin', 'static', 'avatars')
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, filename))

    agent_avatar_url = f'/static/avatars/{filename}'
    with get_db() as conn:
        conn.execute('UPDATE users SET agent_avatar_url=%s WHERE id=%s', (agent_avatar_url, uid))
        conn.commit()
    _log(admin['user_id'], 'set_agent_avatar', 'user', str(uid))
    return jsonify({'success': True, 'data': {'agent_avatar_url': agent_avatar_url}})


@admin_bp.route('/users/<int:uid>/agent-avatar/default', methods=['PUT'])
def user_agent_avatar_default(uid):
    """为Agent设置默认头像 (from library)"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    default_name = data.get('default', chr(39)+chr(39))
    if not default_name:
        return jsonify({'success': False, 'error': _('请指定默认头像文件名')}), 400
    agent_avatar_url = f'/static/avatars/default/agents/{default_name}'
    with get_db() as conn:
        conn.execute('UPDATE users SET agent_avatar_url=%s WHERE id=%s', (agent_avatar_url, uid))
        conn.commit()
    _log(admin['user_id'], 'set_agent_default_avatar', 'user', str(uid), default_name)
    return jsonify({'success': True, 'data': {'agent_avatar_url': agent_avatar_url}})


@admin_bp.route('/users/<int:uid>/avatar/clear', methods=['POST'])
def user_avatar_clear(uid):
    """清除用户头像"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('UPDATE users SET avatar_url=\'\' WHERE id=%s', (uid,))
        conn.commit()
    _log(admin['user_id'], 'clear_user_avatar', 'user', str(uid))
    return jsonify({'success': True})


@admin_bp.route('/users/<int:uid>/agent-avatar/clear', methods=['POST'])
def user_agent_avatar_clear(uid):
    """清除Agent头像"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('UPDATE users SET agent_avatar_url=\'\' WHERE id=%s', (uid,))
        conn.commit()
    _log(admin['user_id'], 'clear_agent_avatar', 'user', str(uid))
    return jsonify({'success': True})


@admin_bp.route('/avatars/defaults', methods=['GET'])
def default_avatars_list():
    """列出所有可用的默认头像"""
    admin, err = _require_admin()
    if err:
        return err
    import os as _os
    base = _os.path.join(_os.path.dirname(__file__), '..', '..', 'admin', 'static', 'avatars', 'default')
    result = {'users': [], 'agents': []}
    users_dir = _os.path.join(base, 'users')
    agents_dir = _os.path.join(base, 'agents')
    if _os.path.isdir(users_dir):
        for f in sorted(_os.listdir(users_dir)):
            if f.lower().endswith(('.svg', '.png', '.jpg', '.jpeg')):
                result['users'].append({
                    'filename': f,
                    'url': f'/static/avatars/default/users/{f}',
                })
    if _os.path.isdir(agents_dir):
        for f in sorted(_os.listdir(agents_dir)):
            if f.lower().endswith(('.svg', '.png', '.jpg', '.jpeg')):
                result['agents'].append({
                    'filename': f,
                    'url': f'/static/avatars/default/agents/{f}',
                })
    return jsonify({'success': True, 'data': result})


# 可用的权限列表
ALL_PERMISSIONS = [
    {'key': 'users', 'label': _('用户管理'), 'desc': _('查看/管理普通用户')},
    {'key': 'content', 'label': _('内容管理'), 'desc': _('CMS/社区内容/评论审核')},
    {'key': 'finance', 'label': _('财务管理'), 'desc': _('套餐/订阅/订单/收入')},
    {'key': 'system', 'label': _('系统设置'), 'desc': _('社区板块/系统配置/操作日志')},
    {'key': 'matrix', 'label': _('Agent矩阵'), 'desc': _('管理Agent矩阵/自动化调度')},
    {'key': 'admins', 'label': _('管理员管理'), 'desc': _('管理其他管理员（仅super_admin）')},
]

@admin_bp.route('/admins/permissions-list', methods=['GET'])
def admin_permissions_list():
    """返回所有可用的权限定义（给前端勾选用）"""
    return jsonify({'success': True, 'data': ALL_PERMISSIONS})




# =============================================
# RBAC: Permission-based middleware
# =============================================

def _require_permission(perm):
    """Verify the admin has a specific permission.
       Usage: wrap around route logic after _require_admin().
    """
    def decorator(f):
        import functools
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            admin, err = _require_admin()
            if err:
                return err
            with get_db() as conn:
                prof = conn.execute(
                    'SELECT permissions, role FROM admin_profiles WHERE user_id=%s',
                    (admin['user_id'],)
                ).fetchone()
            if not prof:
                return jsonify({'success': False, 'error': _('管理员配置不存在')}), 403
            if prof['role'] == 'super_admin':
                # super_admin has all permissions
                return f(*args, **kwargs)
            try:
                perms = __import__('json').loads(prof['permissions'] or '[]')
            except Exception:
                perms = []
            if perm not in perms:
                return jsonify({'success': False, 'error': _('没有"{perm}"权限', perm=perm)}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# =============================================
# User Agent Management (admin)
# =============================================

@admin_bp.route('/user-agents', methods=['GET'])
def admin_user_agents_list():
    """列出所有用户 Agent（含所属用户信息）"""
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', chr(39)+chr(39)).strip()
    status_filter = request.args.get('status', chr(39)+chr(39)).strip()
    offset = (page - 1) * limit
    
    where = []
    params = []
    if search:
        where.append('(ua.agent_name LIKE %s OR COALESCE(u.display_name, u.username) LIKE %s OR u.phone LIKE %s)')
        s = '%' + search + '%'
        params.extend([s, s, s])
    if status_filter:
        where.append('ua.status=%s')
        params.append(status_filter)
    wsql = 'WHERE ' + ' AND '.join(where) if where else ''
    
    with get_db() as conn:
        total = conn.execute(
            'SELECT COUNT(*) as c FROM user_agents ua LEFT JOIN users u ON ua.user_id=u.id ' + wsql,
            params
        ).fetchone()
        rows = conn.execute(
            "SELECT ua.id, ua.agent_name, ua.agent_type, ua.status, ua.last_active_at, "
            "       ua.created_at, ua.user_id, COALESCE(u.display_name, u.username) as user_name, u.phone as user_phone "
            "FROM user_agents ua LEFT JOIN users u ON ua.user_id=u.id " +
            wsql + " ORDER BY ua.created_at DESC LIMIT %s OFFSET %s",
            params + [limit, offset]
        ).fetchall()
    
    return jsonify({'success': True, 'data': {
        'total': total['c'],
        'page': page,
        'limit': limit,
        'agents': [dict(r) for r in rows],
    }})


@admin_bp.route('/users/<int:uid>/user-agents', methods=['GET'])
def admin_user_agent_list(uid):
    """查看指定用户的所有 Agent"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        user = conn.execute('SELECT id, COALESCE(display_name, username) as nickname, phone FROM users WHERE id=%s', (uid,)).fetchone()
        if not user:
            return jsonify({'success': False, 'error': _('用户不存在')}), 404
        rows = conn.execute(
            "SELECT ua.id, ua.agent_name, ua.agent_type, ua.avatar_url, ua.status, "
            "       ua.default_scopes, ua.last_active_ip, ua.last_active_at, ua.created_at, ua.updated_at "
            "FROM user_agents ua WHERE ua.user_id=%s ORDER BY ua.created_at DESC",
            (uid,)
        ).fetchall()
        
        agents = []
        for r in rows:
            d = dict(r)
            try:
                d['default_scopes'] = __import__('json').loads(d['default_scopes'] or '[]')
            except Exception:
                d['default_scopes'] = []
            # Count active keys
            kc = conn.execute(
                "SELECT COUNT(*) as c FROM agent_api_keys WHERE agent_id=%s AND status='active'",
                (r['id'],)
            ).fetchone()
            d['active_keys'] = kc['c'] if kc else 0
            agents.append(d)
    
    return jsonify({'success': True, 'data': {
        'user': dict(user),
        'agents': agents,
    }})


@admin_bp.route('/user-agents/<int:aid>/status', methods=['PUT'])
def admin_user_agent_status(aid):
    """管理Agent状态（suspend/activate）"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    status = data.get('status', chr(39)+chr(39)).strip()
    if status not in ('active', 'inactive', 'suspended'):
        return jsonify({'success': False, 'error': _('无效的状态值')}), 400
    
    with get_db() as conn:
        row = conn.execute(
            'SELECT ua.id, ua.agent_name, u.id as uid FROM user_agents ua JOIN users u ON ua.user_id=u.id WHERE ua.id=%s',
            (aid,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('Agent不存在')}), 404
        conn.execute('UPDATE user_agents SET status=%s, updated_at=NOW() WHERE id=%s', (status, aid))
        conn.commit()
        _log(admin['user_id'], 'set_agent_status', 'user_agent', str(aid),
             _('Agent "{agent_name}" → {status}', agent_name=row['agent_name'], status=status))
    
    return jsonify({'success': True, 'message': _('Agent 状态已更新为 {status}', status=status)})


@admin_bp.route('/users/<int:uid>/user-agents', methods=['POST'])
def admin_user_agent_create(uid):
    """管理员为用户创建 Agent"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    agent_name = data.get('agent_name', chr(39)+chr(39)).strip()
    if not agent_name:
        return jsonify({'success': False, 'error': _('Agent名称不能为空')}), 400
    
    with get_db() as conn:
        user = conn.execute('SELECT id, display_name FROM users WHERE id=%s', (uid,)).fetchone()
        if not user:
            return jsonify({'success': False, 'error': _('用户不存在')}), 404
        existing = conn.execute(
            'SELECT id FROM user_agents WHERE user_id=%s AND agent_name=%s',
            (uid, agent_name)
        ).fetchone()
        if existing:
            return jsonify({'success': False, 'error': _('该用户已存在同名Agent')}), 400
        aid = conn.execute(
            'INSERT INTO user_agents (user_id, agent_name) VALUES (%s,%s) RETURNING id',
            (uid, agent_name)
        ).fetchone()['id']
        conn.commit()
        _log(admin['user_id'], 'create_user_agent', 'user_agent', str(aid),
             _('为 {user} 创建 Agent "{agent_name}"', user=user['display_name'] or uid, agent_name=agent_name))
    
    return jsonify({'success': True, 'data': {'id': aid, 'agent_name': agent_name}})


# =============================================
# social_links CRUD — 后台社媒图标管理
# =============================================
@admin_bp.route('/admin/social-links', methods=['GET'])
def get_social_links():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM social_links ORDER BY sort_order ASC, id ASC').fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})

@admin_bp.route('/admin/social-links', methods=['POST'])
def create_social_link():
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    name = (data.get('name') or '').strip()
    url = (data.get('url') or '#').strip()
    icon_url = (data.get('icon_url') or '').strip()
    platform = (data.get('platform') or '').strip()
    is_active = 1 if data.get('is_active', 1) else 0
    if not name:
        return jsonify({'success': False, 'error': _('名称不能为空')}), 400
    with get_db() as conn:
        max_sort = conn.execute('SELECT COALESCE(MAX(sort_order), -1) + 1 AS max_sort FROM social_links').fetchone()['max_sort']
        lid = conn.execute(
            'INSERT INTO social_links (name, url, icon_url, platform, sort_order, is_active) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
            (name, url, icon_url, platform, max_sort, is_active)
        ).fetchone()['id']
        conn.commit()
        _log(admin['user_id'], 'create', 'social_link', str(lid), _('新增社媒图标: {name}', name=name))
    return jsonify({'success': True, 'data': {'id': lid}})

@admin_bp.route('/admin/social-links/<int:lid>', methods=['PUT'])
def update_social_link(lid):
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    name = (data.get('name') or '').strip()
    url = (data.get('url') or '').strip()
    icon_url = (data.get('icon_url') or '').strip()
    platform = (data.get('platform') or '').strip()
    is_active = data.get('is_active')
    with get_db() as conn:
        row = conn.execute('SELECT * FROM social_links WHERE id=%s', (lid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        name = name or row['name']
        if not url: url = '#'
        platform = platform or row.get('platform', '')
        if is_active is not None:
            conn.execute('UPDATE social_links SET name=%s, url=%s, icon_url=%s, platform=%s, is_active=%s, updated_at=NOW() WHERE id=%s',
                         (name, url, icon_url, platform, 1 if is_active else 0, lid))
        else:
            conn.execute('UPDATE social_links SET name=%s, url=%s, icon_url=%s, platform=%s, updated_at=NOW() WHERE id=%s',
                         (name, url, icon_url, platform, lid))
        conn.commit()
        _log(admin['user_id'], 'update', 'social_link', str(lid), _('更新社媒图标: {name}', name=name))
    return jsonify({'success': True})

@admin_bp.route('/admin/social-links/<int:lid>', methods=['DELETE'])
def delete_social_link(lid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        row = conn.execute('SELECT name FROM social_links WHERE id=%s', (lid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        conn.execute('DELETE FROM social_links WHERE id=%s', (lid,))
        conn.commit()
        _log(admin['user_id'], 'delete', 'social_link', str(lid), _('删除社媒图标: {name}', name=row['name']))
    return jsonify({'success': True})

@admin_bp.route('/admin/social-links/reorder', methods=['PUT'])
def reorder_social_links():
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    ids = data.get('ids', [])
    with get_db() as conn:
        for idx, lid in enumerate(ids):
            conn.execute('UPDATE social_links SET sort_order=%s WHERE id=%s', (idx, lid))
        conn.commit()
    return jsonify({'success': True})

# ════════════════════════════════════════════════════════════════
# 频道管理（IM Gateway）已迁移至 plugins/im_gateway/
#   - REST 路由：plugins/im_gateway/routes.py（/admin/channels/*）
#   - 第三方逻辑：plugins/im_gateway/adapters/*
#   - 独立数据库：plugins/im_gateway/im_gateway.db
# ════════════════════════════════════════════════════════════════

# =============================================
# GET /admin/users/export — 脱敏导出用户列表
# =============================================
@admin_bp.route('/users/export', methods=['GET'])
def user_export():
    admin, err = _require_admin()
    if err:
        return err
    industry = request.args.get('industry', '').strip()
    occupation = request.args.get('occupation', '').strip()
    region = request.args.get('region', '').strip()

    where = []
    params = []
    if industry:
        where.append('p.industry LIKE %s')
        params.append('%' + industry + '%')
    if occupation:
        where.append('p.occupation LIKE %s')
        params.append('%' + occupation + '%')
    if region:
        where.append('(pa.province LIKE %s OR pa.city LIKE %s OR pa.district LIKE %s)')
        r = '%' + region + '%'
        params.extend([r, r, r])
    wsql = 'WHERE ' + ' AND '.join(where) if where else ''

    sql = (
        "SELECT u.id, u.phone, COALESCE(u.display_name, u.username) as nickname, "
        "COALESCE(p.industry,'') as industry, COALESCE(p.occupation,'') as occupation, "
        "COALESCE(pa.province_code,'') as province, COALESCE(pa.city_code,'') as city, "
        "COALESCE(pa.district_code,'') as district, "
        "'' as tier, u.created_at "
        "FROM users u "
        "LEFT JOIN user_profiles p ON u.id=p.user_id "
        "LEFT JOIN user_addresses pa ON u.id=pa.user_id AND pa.is_default=1 AND pa.status=1 "
        + wsql + ' ORDER BY u.id'
    )

    def _mask_phone(phone):
        s = str(phone or '')
        if len(s) >= 7:
            return s[:3] + '****' + s[-4:]
        return s

    def _mask_address(prov, city, dist):
        parts = [p for p in [prov, city, dist] if p]
        if parts:
            return ''.join(parts) + '***'
        return ''

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    lines = []
    lines.append(_('ID,手机号(脱敏),昵称,行业,职业,区域(脱敏),套餐,注册时间'))
    for r in rows:
        phone_m = _mask_phone(r['phone'])
        addr_m = _mask_address(r['province'], r['city'], r['district'])
        nickname = (r['nickname'] or '').replace(',', ' ')
        industry_v = (r['industry'] or '').replace(',', ' ')
        occupation_v = (r['occupation'] or '').replace(',', ' ')
        tier = r['tier'] or 'free'
        created = r['created_at'] or ''
        lines.append(f"{r['id']},{phone_m},{nickname},{industry_v},{occupation_v},{addr_m},{tier},{created}")

    csv_content = '\n'.join(lines)
    from flask import Response
    return Response(
        csv_content,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=users_export.csv'}
    )


# =============================================
# Brand Settings — global site branding
# =============================================
@admin_bp.route('/brand-settings', methods=['GET'])
def get_brand_settings():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        row = conn.execute('SELECT * FROM brand_settings WHERE id=1').fetchone()
    if row:
        return jsonify({'success': True, 'data': dict(row)})
    return jsonify({'success': True, 'data': None})


@admin_bp.route('/brand-settings', methods=['PUT'])
def update_brand_settings():
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    allowed = ['company_name', 'site_name_cn', 'site_name_en', 'slogan', 'tagline',
               'description', 'copyright', 'seo_title', 'seo_desc', 'logo_full_url',
               'logo_icon_url', 'icp_number', 'security_number', 'contact_email']
    updates = {k: data[k] for k in allowed if k in data}
    if not updates:
        return jsonify({'success': False, 'error': _('无有效更新字段')}), 400
    sets = ', '.join(f'{k}=%s' for k in updates)
    vals = list(updates.values()) + [1]
    with get_db() as conn:
        conn.execute(f'UPDATE brand_settings SET {sets}, updated_at=NOW() WHERE id=%s', vals)
        conn.commit()
    _log(admin['user_id'], 'update_brand', detail=str(list(updates.keys())))
    return jsonify({'success': True})


def _save_brand_image(subdir, file_key):
    """Save uploaded image to admin/static/brand/<subdir>/ AND sync to all services' static dirs."""
    import time
    file = request.files.get(file_key)
    if not file or not file.filename:
        return None, _('未选择文件')
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
    if ext not in ('png', 'jpg', 'jpeg', 'svg', 'ico'):
        return None, _('仅支持 PNG/JPG/SVG/ICO 格式')
    # Read + size check
    data = file.read()
    max_size = 500 * 1024  # 500KB
    if len(data) > max_size:
        return None, _('文件过大 ({size}KB)，限制 {max}KB', size=len(data)//1024, max=max_size//1024)
    # Safe filename
    ts = int(time.time() * 1000)
    fname = f'{subdir}_{ts}.{ext}'
    # Save to admin/static/brand/
    base = os.path.join(os.path.dirname(__file__), '..', '..')
    admin_dir = os.path.join(base, 'admin', 'static', 'brand')
    os.makedirs(admin_dir, exist_ok=True)
    with open(os.path.join(admin_dir, fname), 'wb') as f:
        f.write(data)
    # Sync to all other services that might serve brand images
    for svc in ('platform',):
        svc_dir = os.path.join(base, svc, 'static', 'brand')
        os.makedirs(svc_dir, exist_ok=True)
        with open(os.path.join(svc_dir, fname), 'wb') as f:
            f.write(data)
    return f'/static/brand/{fname}', None


@admin_bp.route('/brand-settings/logo', methods=['POST'])
def upload_brand_logo():
    admin, err = _require_admin()
    if err: return err
    url, error = _save_brand_image('logo', 'logo')
    if error:
        return jsonify({'success': False, 'error': error}), 400
    with get_db() as conn:
        conn.execute("UPDATE brand_settings SET logo_url=%s, logo_full_url=%s, updated_at=NOW() WHERE id=1", (url, url))
        conn.commit()
    _log(admin['user_id'], 'upload_brand_logo', detail=url)
    return jsonify({'success': True, 'logo_url': url})


@admin_bp.route('/brand-settings/logo', methods=['DELETE'])
def delete_brand_logo():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute("UPDATE brand_settings SET logo_url='', logo_full_url='', updated_at=NOW() WHERE id=1")
        conn.commit()
    _log(admin['user_id'], 'delete_brand_logo')
    return jsonify({'success': True})


@admin_bp.route('/brand-settings/favicon', methods=['POST'])
def upload_brand_favicon():
    admin, err = _require_admin()
    if err: return err
    url, error = _save_brand_image('favicon', 'favicon')
    if error:
        return jsonify({'success': False, 'error': error}), 400
    with get_db() as conn:
        conn.execute("UPDATE brand_settings SET favicon_url=%s, updated_at=NOW() WHERE id=1", (url,))
        conn.commit()
    _log(admin['user_id'], 'upload_brand_favicon', detail=url)
    return jsonify({'success': True, 'favicon_url': url})


@admin_bp.route('/brand-settings/favicon', methods=['DELETE'])
def delete_brand_favicon():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute("UPDATE brand_settings SET favicon_url='', updated_at=NOW() WHERE id=1")
        conn.commit()
    _log(admin['user_id'], 'delete_brand_favicon')
    return jsonify({'success': True})



@admin_bp.route('/brand-settings/logo-icon', methods=['POST'])
def upload_brand_logo_icon():
    """上传纯图标 Logo（用于 Favicon、Admin 侧栏等小尺寸场景）"""
    admin, err = _require_admin()
    if err: return err
    url, error = _save_brand_image('logo', 'logo_icon')
    if error:
        return jsonify({'success': False, 'error': error}), 400
    with get_db() as conn:
        conn.execute("UPDATE brand_settings SET logo_icon_url=%s, updated_at=NOW() WHERE id=1", (url,))
        conn.commit()
    _log(admin['user_id'], 'upload_brand_logo_icon', detail=url)
    return jsonify({'success': True, 'logo_icon_url': url})


@admin_bp.route('/brand-settings/logo-icon', methods=['DELETE'])
def delete_brand_logo_icon():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute("UPDATE brand_settings SET logo_icon_url='', updated_at=NOW() WHERE id=1")
        conn.commit()
    _log(admin['user_id'], 'delete_brand_logo_icon')
    return jsonify({'success': True})


# ══════════════════════════════════════════════
# 子域名管理 API
# ══════════════════════════════════════════════

_PLAN_DOMAIN_LIMITS = {
    'deploy_basic': 20,
    'deploy_pro': 20,
    'deploy_enterprise': 20,
}

_NGINX_CONF_DIR = os.environ.get(
    'NGINX_SNIPPETS_DIR'
) or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'nginx-domains', 'sites-enabled'
)
_SSL_CERT_DIR = '/etc/letsencrypt/live/easykai.cn-0001'


def _generate_domain_nginx_config(subdomain, full_domain, port):
    """生成本地 Nginx server block 配置文件"""
    if not port:
        return None
    os.makedirs(_NGINX_CONF_DIR, exist_ok=True)
    conf = f"""# Auto-generated by easykai site_domains — {datetime.now().strftime('%Y-%m-%d %H:%M')}
# subdomain={subdomain}  port={port}

server {{
    listen 443 ssl http2;
    server_name {full_domain};

    ssl_certificate     {_SSL_CERT_DIR}/fullchain.pem;
    ssl_certificate_key {_SSL_CERT_DIR}/privkey.pem;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    filepath = os.path.join(_NGINX_CONF_DIR, f'{full_domain}.conf')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(conf)
    return filepath


def _remove_domain_nginx_config(full_domain):
    """删除本地 Nginx 配置文件"""
    filepath = os.path.join(_NGINX_CONF_DIR, f'{full_domain}.conf')
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def _reload_nginx():
    """生产环境：reload Nginx 使配置生效"""
    if 'NGINX_SNIPPETS_DIR' not in os.environ:
        return  # 本地开发不执行
    import subprocess
    try:
        subprocess.run(['sudo', '/usr/sbin/nginx', '-s', 'reload'], check=True,
                       capture_output=True, timeout=10)
    except Exception as e:
        print(f'[Nginx Reload Warning] {e}', flush=True)


def _check_domain_quota(user_id):
    """检查用户是否还能添加子域名"""
    with get_db() as conn:
        sub = conn.execute(
            "SELECT plan_key FROM subscriptions WHERE user_id=%s AND status='active'",
            (user_id,)
        ).fetchone()
        if not sub:
            limit = 20  # 无订阅时给默认限额
        else:
            limit = _PLAN_DOMAIN_LIMITS.get(sub['plan_key'], 20)
        used = conn.execute(
            "SELECT COUNT(*) as c FROM site_domains"
        ).fetchone()['c']
        allowed = max(limit - used, 0)
        return {
            'allowed': allowed,
            'used': used,
            'limit': limit,
            'can_add': allowed > 0,
        }


@admin_bp.route('/domains', methods=['GET'])
def admin_domains_page():
    admin, err = _require_admin()
    if err:
        return err
    return jsonify({'success': True, 'page': 'domains'})


@admin_bp.route('/api/domains', methods=['GET'])
def admin_list_domains():
    admin, err = _require_admin()
    if err:
        return err
    quota = _check_domain_quota(admin['user_id'])
    with get_db() as conn:
        rows = conn.execute(
            "SELECT sd.*, sc.name as site_name, sc.theme_color, sc.accent_color "
            "FROM site_domains sd "
            "JOIN site_configs sc ON sc.id = sd.site_config_id "
            "ORDER BY sd.sort_order, sd.id"
        ).fetchall()
    return jsonify({
        'success': True,
        'data': [dict(r) for r in rows],
        'quota': quota,
    })


@admin_bp.route('/api/domains', methods=['POST'])
def admin_create_domain():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    subdomain = data.get('subdomain', '').strip().lower()
    display_name = data.get('display_name', '').strip()
    template = data.get('template', 'default')
    service_port = data.get('service_port')

    if not subdomain or not display_name:
        return jsonify({'success': False, 'error': _('子域名和显示名不能为空')}), 400

    # 校验子域名格式（只允许字母数字连字符）
    import re
    if not re.match(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$', subdomain):
        return jsonify({'success': False, 'error': _('子域名格式无效：仅允许字母、数字和连字符')}), 400

    # 校验配额
    quota = _check_domain_quota(admin['user_id'])
    if not quota['can_add']:
        return jsonify({'success': False, 'error': _('配额已用完（{used}/{limit}）', used=quota["used"], limit=quota["limit"])}), 400

    deploy_domain = os.environ.get('DEPLOY_DOMAIN', 'localhost')
    full_domain = f'{subdomain}.{deploy_domain}'

    with get_db() as conn:
        # 检查是否已存在
        exists = conn.execute(
            "SELECT id FROM site_domains WHERE full_domain=%s", (full_domain,)
        ).fetchone()
        if exists:
            return jsonify({'success': False, 'error': _('子域名 {domain} 已存在', domain=full_domain)}), 400

        conn.execute(
            "INSERT INTO site_domains (site_config_id, subdomain, full_domain, display_name, template, service_port) "
            "VALUES (1, %s, %s, %s, %s, %s)",
            (subdomain, full_domain, display_name, template, service_port)
        )
        conn.commit()

    # 独立服务 → 生成 Nginx 配置
    nginx_path = _generate_domain_nginx_config(subdomain, full_domain, service_port)
    _reload_nginx()

    _log(admin['user_id'], 'create_domain', detail=_('{domain} ({display_name}) port={port}', domain=full_domain, display_name=display_name, port=service_port or 'content'))
    msg = _('子域名 {domain} 已创建', domain=full_domain)
    if nginx_path:
        msg += _('，Nginx 配置已生成')
    return jsonify({'success': True, 'message': msg, 'nginx_config_path': nginx_path})


@admin_bp.route('/api/domains/<int:did>', methods=['PUT'])
def admin_update_domain(did):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    allowed = ['display_name', 'template', 'is_published', 'page_keys_json', 'sort_order', 'service_port']
    updates = {k: data[k] for k in allowed if k in data}
    if not updates:
        return jsonify({'success': False, 'error': _('无有效更新字段')}), 400

    # 先读取旧 full_domain
    with get_db() as conn:
        old_row = conn.execute("SELECT full_domain, subdomain FROM site_domains WHERE id=%s", (did,)).fetchone()

    sets = ', '.join(f'{k}=%s' for k in updates)
    vals = list(updates.values()) + [did]
    with get_db() as conn:
        conn.execute(
            f'UPDATE site_domains SET {sets}, updated_at=NOW() WHERE id=%s',
            vals
        )
        conn.commit()

    # 更新 Nginx 配置
    if old_row:
        old_domain = old_row['full_domain']
        subdomain = old_row['subdomain']
        new_port = data.get('service_port')
        if new_port is not None:
            _generate_domain_nginx_config(subdomain, old_domain, new_port)
        else:
            _remove_domain_nginx_config(old_domain)
        _reload_nginx()

    _log(admin['user_id'], 'update_domain', detail=f'domain_id={did}')
    return jsonify({'success': True, 'message': _('已更新')})


@admin_bp.route('/api/domains/<int:did>', methods=['DELETE'])
def admin_delete_domain(did):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute(
            "SELECT full_domain, service_port FROM site_domains WHERE id=%s", (did,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('子域名不存在')}), 404
        full_domain = row['full_domain']
        conn.execute("DELETE FROM site_domains WHERE id=%s", (did,))
        conn.commit()
    # 删除 Nginx 配置文件
    _remove_domain_nginx_config(full_domain)
    _reload_nginx()
    _log(admin['user_id'], 'delete_domain', detail=full_domain)
    return jsonify({'success': True, 'message': _('{domain} 已删除', domain=full_domain)})


@admin_bp.route('/api/domains/quota', methods=['GET'])
def admin_domain_quota():
    admin, err = _require_admin()
    if err:
        return err
    return jsonify({'success': True, 'data': _check_domain_quota(admin['user_id'])})


@admin_bp.route('/api/domains/<int:did>/nginx-config', methods=['GET'])
def admin_domain_nginx_config(did):
    """返回子域名对应的 Nginx 配置文本"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute(
            "SELECT full_domain, subdomain, service_port FROM site_domains WHERE id=%s", (did,)
        ).fetchone()
    if not row:
        return jsonify({'success': False, 'error': _('子域名不存在')}), 404
    if not row['service_port']:
        return jsonify({'success': False, 'error': _('内容站点无需 Nginx 配置')}), 400
    config_path = os.path.join(_NGINX_CONF_DIR, f'{row["full_domain"]}.conf')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config_text = f.read()
    else:
        # 动态生成（文件不存在时）
        config_text = _generate_domain_nginx_config(
            row['subdomain'], row['full_domain'], row['service_port']
        )
        if config_text:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_text = f.read()
    return jsonify({
        'success': True,
        'data': {
            'full_domain': row['full_domain'],
            'service_port': row['service_port'],
            'config_text': config_text,
            'server_path': f'/etc/nginx/snippets/easykai-domains/{row["full_domain"]}.conf',
        }
    })


# ══════════════════════════════════════════════
# 通知系统 — 管理端 API
# ══════════════════════════════════════════════

@admin_bp.route('/notifications/templates', methods=['GET'])
def admin_notif_templates_list():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM notification_templates ORDER BY sort_order, id'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/notifications/templates', methods=['POST'])
def admin_notif_templates_create():
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    event_type = (data.get('event_type') or '').strip()
    title_tmpl = (data.get('title_template') or '').strip()
    content_tmpl = (data.get('content_template') or '').strip()
    link_url_tmpl = (data.get('link_url_template') or '').strip()
    ntype = data.get('type', 'system')
    if not event_type or not title_tmpl or not content_tmpl:
        return jsonify({'success': False, 'error': _('event_type, title_template, content_template 为必填')}), 400
    with get_db() as conn:
        try:
            tid = conn.execute(
                'INSERT INTO notification_templates (event_type, title_template, content_template, link_url_template, type) VALUES (%s,%s,%s,%s,%s) RETURNING id',
                (event_type, title_tmpl, content_tmpl, link_url_tmpl, ntype)
            ).fetchone()['id']
            conn.commit()
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    _log(admin['user_id'], 'create_notif_template', detail=f'{event_type}')
    return jsonify({'success': True, 'id': tid})


@admin_bp.route('/notifications/templates/<int:tid>', methods=['PUT'])
def admin_notif_templates_update(tid):
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    fields = []
    vals = []
    for key in ('event_type', 'title_template', 'content_template', 'link_url_template', 'type', 'is_active'):
        if key in data:
            fields.append(f'{key}=%s')
            vals.append(data[key])
    if not fields:
        return jsonify({'success': False, 'error': _('无更新字段')}), 400
    vals.append(tid)
    with get_db() as conn:
        conn.execute(f'UPDATE notification_templates SET {", ".join(fields)}, updated_at=NOW() WHERE id=%s', vals)
        conn.commit()
    _log(admin['user_id'], 'update_notif_template', detail=f'{tid}')
    return jsonify({'success': True})


@admin_bp.route('/notifications/templates/<int:tid>', methods=['DELETE'])
def admin_notif_templates_delete(tid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute('DELETE FROM notification_templates WHERE id=%s', (tid,))
        conn.commit()
    _log(admin['user_id'], 'delete_notif_template', detail=f'{tid}')
    return jsonify({'success': True})


@admin_bp.route('/notifications/send', methods=['POST'])
def admin_notif_send():
    """手动推送通知。支持：全体用户 / 指定用户ID列表 / 用户类型筛选"""
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    target_type = data.get('target_type', 'all')  # all / user_ids
    user_ids = data.get('user_ids', [])
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    link_url = (data.get('link_url') or '').strip()
    ntype = data.get('type', 'system')
    schedule_at = data.get('schedule_at', '')  # ISO timestamp or empty = immediate

    if not title:
        return jsonify({'success': False, 'error': _('标题不能为空')}), 400
    if not content:
        return jsonify({'success': False, 'error': _('内容不能为空')}), 400

    target_users = []
    with get_db() as conn:
        if target_type == 'all':
            rows = conn.execute('SELECT id FROM users WHERE active=1 ORDER BY id').fetchall()
            target_users = [r['id'] for r in rows]
        elif target_type == 'user_ids' and user_ids:
            target_users = [int(uid) for uid in user_ids]
        else:
            return jsonify({'success': False, 'error': _('无效的目标类型')}), 400

    from services.notification_service import create_notification
    sent = 0
    errors = []
    for uid in target_users:
        try:
            nid = create_notification(uid, ntype, title, content, link_url)
            if nid:
                sent += 1
        except Exception as e:
            errors.append(str(e))

    _log(admin['user_id'], 'notif_send', detail=f'target={target_type} count={sent}')
    return jsonify({'success': True, 'sent': sent, 'total': len(target_users), 'errors': errors[:5]})


@admin_bp.route('/notifications/test', methods=['POST'])
def admin_notif_test():
    """发送测试通知给当前管理员"""
    admin, err = _require_admin()
    if err: return err
    from services.notification_service import create_notification
    nid = create_notification(
        admin['user_id'], 'system',
        _('这是测试通知'),
        _('通知系统运行正常。这是一条测试消息，确认系统已就绪。'),
        link_url=''
    )
    if nid:
        return jsonify({'success': True, 'notification_id': nid})
    return jsonify({'success': False, 'error': _('发送失败')}), 500


# ══════════════════════════════════════════════
# 用户工单管理 — 管理端 API
# ══════════════════════════════════════════════

@admin_bp.route('/tickets', methods=['GET'])
def admin_tickets_list():
    """管理员查看工单列表，支持 %sstatus=open&type=complaint 多维筛选"""
    admin, err = _require_admin()
    if err: return err
    status = request.args.get('status', '').strip()
    ttype = request.args.get('type', '').strip()
    with get_db() as conn:
        # 构建查询条件
        where = []
        params = []
        if status:
            where.append("t.status=%s")
            params.append(status)
        if ttype and ttype in ("presale","aftersale","complaint","suggestion"):
            where.append("t.type=%s")
            params.append(ttype)
        where_clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = conn.execute(
            f'SELECT t.*, u.username, u.phone FROM user_tickets t LEFT JOIN users u ON t.user_id=u.id {where_clause} ORDER BY CASE t.status WHEN \'open\' THEN 0 WHEN \'replied\' THEN 1 ELSE 2 END, t.updated_at DESC',
            tuple(params)
        ).fetchall() if params else conn.execute(
            f'SELECT t.*, u.username, u.phone FROM user_tickets t LEFT JOIN users u ON t.user_id=u.id {where_clause} ORDER BY CASE t.status WHEN \'open\' THEN 0 WHEN \'replied\' THEN 1 ELSE 2 END, t.updated_at DESC'
        ).fetchall()
        total = conn.execute('SELECT COUNT(*) as c FROM user_tickets').fetchone()['c']
        open_count = conn.execute('SELECT COUNT(*) as c FROM user_tickets WHERE status=\'open\'').fetchone()['c']
        replied_count = conn.execute('SELECT COUNT(*) as c FROM user_tickets WHERE status=\'replied\'').fetchone()['c']
        # 各类型计数
        cnt_presale = conn.execute("SELECT COUNT(*) as c FROM user_tickets WHERE type='presale'").fetchone()['c']
        cnt_aftersale = conn.execute("SELECT COUNT(*) as c FROM user_tickets WHERE type='aftersale'").fetchone()['c']
        cnt_complaint = conn.execute("SELECT COUNT(*) as c FROM user_tickets WHERE type='complaint'").fetchone()['c']
        cnt_suggestion = conn.execute("SELECT COUNT(*) as c FROM user_tickets WHERE type='suggestion'").fetchone()['c']
    return jsonify({
        'success': True, 'data': [dict(r) for r in rows],
        'total': total, 'open': open_count, 'replied': replied_count,
        'cnt_presale': cnt_presale, 'cnt_aftersale': cnt_aftersale,
        'cnt_complaint': cnt_complaint, 'cnt_suggestion': cnt_suggestion
    })


@admin_bp.route('/tickets/<int:tid>', methods=['PUT'])
def admin_tickets_update(tid):
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    action = data.get('action', 'reply')  # reply / close / reopen
    with get_db() as conn:
        if action == 'reply':
            reply = (data.get('admin_reply') or '').strip()
            if not reply:
                return jsonify({'success': False, 'error': _('回复内容不能为空')}), 400
            conn.execute(
                "UPDATE user_tickets SET admin_reply=%s, status='replied', replied_at=NOW(), updated_at=NOW() WHERE id=%s",
                (reply, tid)
            )
        elif action == 'close':
            conn.execute(
                "UPDATE user_tickets SET status='closed', updated_at=NOW() WHERE id=%s",
                (tid,)
            )
        elif action == 'reopen':
            conn.execute(
                "UPDATE user_tickets SET status='open', updated_at=NOW() WHERE id=%s",
                (tid,)
            )
        conn.commit()
    _log(admin['user_id'], 'ticket_update', detail=f'ticket={tid} action={action}')
    return jsonify({'success': True})


# 投诉/建议路由已合并到工单路由


# ══════════════════════════════════════════════
# 完成度奖励规则 CRUD
# ══════════════════════════════════════════════

@admin_bp.route('/reward-rules', methods=['GET'])
def admin_reward_rules_list():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM reward_rules ORDER BY sort_order, id').fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/reward-rules', methods=['POST'])
def admin_reward_rules_create():
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': _('规则名称不能为空')}), 400
    with get_db() as conn:
        rid = conn.execute(
            'INSERT INTO reward_rules (name, condition_key, condition_value, reward_type, reward_id, reward_name, sort_order, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',
            (name, data.get('condition_key', ''), data.get('condition_value', ''),
             data.get('reward_type', 'coupon'), data.get('reward_id'), data.get('reward_name', ''),
             data.get('sort_order', 0), 1 if data.get('is_active', True) else 0)
        ).fetchone()['id']
    _log(admin['user_id'], 'create_reward_rule', detail=name)
    return jsonify({'success': True, 'data': {'id': rid}})


@admin_bp.route('/reward-rules/<int:rid>', methods=['PUT'])
def admin_reward_rules_update(rid):
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    allowed = ['name', 'condition_key', 'condition_value', 'reward_type', 'reward_id', 'reward_name', 'sort_order', 'is_active']
    updates = {}
    for k in allowed:
        if k in data:
            updates[k] = data[k]
    if not updates:
        return jsonify({'success': False, 'error': _('没有可更新的字段')}), 400
    sets = ', '.join(f'{k}=%s' for k in updates.keys())
    vals = list(updates.values()) + [rid]
    with get_db() as conn:
        conn.execute(f'UPDATE reward_rules SET {sets} WHERE id=%s', vals)
        conn.commit()
    _log(admin['user_id'], 'update_reward_rule', detail=f'id={rid}')
    return jsonify({'success': True})


@admin_bp.route('/reward-rules/<int:rid>', methods=['DELETE'])
def admin_reward_rules_delete(rid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute('DELETE FROM reward_rules WHERE id=%s', (rid,))
        conn.execute('DELETE FROM reward_claims WHERE rule_id=%s', (rid,))
        conn.commit()
    _log(admin['user_id'], 'delete_reward_rule', detail=f'id={rid}')
    return jsonify({'success': True})


@admin_bp.route('/reward-claims', methods=['GET'])
def admin_reward_claims_list():
    admin, err = _require_admin()
    if err: return err
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 50, type=int)
    offset = (page - 1) * page_size
    with get_db() as conn:
        rows = conn.execute("""
            SELECT rc.*, r.name AS rule_name, u.display_name AS user_name
            FROM reward_claims rc
            LEFT JOIN reward_rules r ON rc.rule_id = r.id
            LEFT JOIN users u ON rc.user_id = u.id
            ORDER BY rc.id DESC LIMIT %s OFFSET %s
        """, (page_size, offset)).fetchall()
        total = conn.execute('SELECT COUNT(*) as c FROM reward_claims').fetchone()['c']
    return jsonify({'success': True, 'data': [dict(r) for r in rows], 'total': total})


# ── Interests management ──

@admin_bp.route('/interests', methods=['GET'])
def admin_interests_list():
    admin, err = _require_admin()
    if err: return err
    category = request.args.get('category', '').strip()
    with get_db() as conn:
        if category:
            rows = conn.execute(
                'SELECT * FROM interests WHERE category=%s ORDER BY sort_order, id', (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM interests ORDER BY category, sort_order, id'
            ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/interests', methods=['POST'])
def admin_interests_create():
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip()
    if not name or not category:
        return jsonify({'success': False, 'error': _('名称和分类不能为空')}), 400
    with get_db() as conn:
        existing = conn.execute('SELECT id FROM interests WHERE name=%s', (name,)).fetchone()
        if existing:
            return jsonify({'success': False, 'error': _('标签"{name}"已存在', name=name)}), 409
        new_id = conn.execute(
            'INSERT INTO interests (name, category, sort_order, is_hot, is_active) VALUES (%s,%s,%s,%s,%s) RETURNING id',
            (name, category, data.get('sort_order', 0), data.get('is_hot', 0), data.get('is_active', 1))
        ).fetchone()['id']
        conn.commit()
    _log(admin['user_id'], 'create_interest', detail=f'{name} ({category})')
    return jsonify({'success': True, 'data': {'id': new_id}})


@admin_bp.route('/interests/<int:iid>', methods=['PUT'])
def admin_interests_update(iid):
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    updates = {}
    for k in ['name', 'category', 'sort_order', 'is_hot', 'is_active']:
        if k in data:
            updates[k] = data[k]
    if not updates:
        return jsonify({'success': False, 'error': _('没有可更新的字段')}), 400
    sets = ', '.join(f'{k}=%s' for k in updates)
    vals = list(updates.values()) + [iid]
    with get_db() as conn:
        conn.execute(f'UPDATE interests SET {sets} WHERE id=%s', vals)
        conn.commit()
    _log(admin['user_id'], 'update_interest', detail=f'id={iid}')
    return jsonify({'success': True})


@admin_bp.route('/interests/<int:iid>', methods=['DELETE'])
def admin_interests_delete(iid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute('DELETE FROM interests WHERE id=%s', (iid,))
        conn.execute('DELETE FROM user_interests WHERE interest_id=%s', (iid,))
        conn.commit()
    _log(admin['user_id'], 'delete_interest', detail=f'id={iid}')
    return jsonify({'success': True})


# ── Public interests API (grouped by category) ──

@admin_bp.route('/interests/public', methods=['GET'])
def public_interests():
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM interests WHERE is_active=1 AND is_hot=1 ORDER BY category, sort_order, id'
        ).fetchall()
    grouped = {}
    for r in rows:
        d = dict(r)
        cat = d['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(d)
    return jsonify({'success': True, 'data': grouped})

# =============================================
# 下载管理 — Downloads CRUD (2026-05-21)
# =============================================

@admin_bp.route('/downloads', methods=['GET'])
@_cached_get(ttl=3)
def admin_downloads_list():
    admin, err = _require_admin()
    if err:
        return err
    from models.cms import get_all_downloads
    items = get_all_downloads()
    return jsonify({'success': True, 'data': items})


@admin_bp.route('/downloads', methods=['POST'])
def admin_downloads_create():
    admin, err = _require_admin()
    if err:
        return err
    # Support both JSON and multipart form
    if request.is_json:
        data = request.get_json(force=True) or {}
    else:
        data = {}
        for k in ('name','slug','tagline','category','version','download_url','repo_url',
                  'file_size','license','requirements','docs_url','changelog_url','icon'):
            data[k] = request.form.get(k, '').strip()
        try:
            data['tags'] = json.loads(request.form.get('tags', '[]'))
        except Exception:
            data['tags'] = []
        try:
            data['sort_order'] = int(request.form.get('sort_order', 0))
        except Exception:
            data['sort_order'] = 0
        data['is_published'] = int(request.form.get('is_published', 1))
    slug = data.get('slug', '').strip()
    name = data.get('name', '').strip()
    if not slug or not name:
        return jsonify({'success': False, 'error': _('slug 和名称不能为空')}), 400
    # Handle file upload
    uploaded_file = request.files.get('file') if not request.is_json else None
    if uploaded_file and uploaded_file.filename:
        import os
        dl_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'downloads')
        os.makedirs(dl_dir, exist_ok=True)
        ext = os.path.splitext(uploaded_file.filename)[1]
        safe_name = slug + ext
        filepath = os.path.join(dl_dir, safe_name)
        uploaded_file.save(filepath)
        data['download_url'] = '/static/downloads/' + safe_name
        if not data.get('file_size'):
            fsize = os.path.getsize(filepath)
            if fsize < 1048576:
                data['file_size'] = f'{fsize/1024:.1f} KB'
            else:
                data['file_size'] = f'{fsize/1048576:.1f} MB'
    from models.cms import upsert_download
    item = upsert_download(data)
    _log(admin['user_id'], 'create_download', 'download', str(item.get('id')), f'{name} ({slug})')
    return jsonify({'success': True, 'data': item})


@admin_bp.route('/downloads/<int:dl_id>', methods=['POST','PUT'])
def admin_downloads_update(dl_id):
    admin, err = _require_admin()
    if err:
        return err
    if request.is_json:
        data = request.get_json(force=True) or {}
    else:
        data = {}
        for k in ('name','slug','tagline','category','version','download_url','repo_url',
                  'file_size','license','requirements','docs_url','changelog_url','icon'):
            data[k] = request.form.get(k, '').strip()
        try:
            data['tags'] = json.loads(request.form.get('tags', '[]'))
        except Exception:
            data['tags'] = []
        try:
            data['sort_order'] = int(request.form.get('sort_order', 0))
        except Exception:
            data['sort_order'] = 0
        data['is_published'] = int(request.form.get('is_published', 1))
    data['id'] = dl_id
    # Handle file upload
    uploaded_file = request.files.get('file') if not request.is_json else None
    if uploaded_file and uploaded_file.filename:
        import os
        dl_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'downloads')
        os.makedirs(dl_dir, exist_ok=True)
        slug = data.get('slug', '') or str(dl_id)
        ext = os.path.splitext(uploaded_file.filename)[1]
        safe_name = slug + ext
        filepath = os.path.join(dl_dir, safe_name)
        uploaded_file.save(filepath)
        data['download_url'] = '/static/downloads/' + safe_name
        if not data.get('file_size'):
            fsize = os.path.getsize(filepath)
            if fsize < 1048576:
                data['file_size'] = f'{fsize/1024:.1f} KB'
            else:
                data['file_size'] = f'{fsize/1048576:.1f} MB'
    from models.cms import upsert_download
    item = upsert_download(data)
    _log(admin['user_id'], 'update_download', 'download', str(dl_id))
    return jsonify({'success': True, 'data': item})


@admin_bp.route('/downloads/<int:dl_id>', methods=['DELETE'])
def admin_downloads_delete(dl_id):
    admin, err = _require_admin()
    if err:
        return err
    from models.cms import delete_download
    delete_download(dl_id)
    _log(admin['user_id'], 'delete_download', 'download', str(dl_id))
    return jsonify({'success': True})


@admin_bp.route('/downloads/<int:dl_id>', methods=['GET'])
def admin_downloads_get(dl_id):
    """获取单个下载项（替代全量加载）"""
    admin, err = _require_admin()
    if err:
        return err
    from models.cms import get_download
    item = get_download(dl_id)
    if not item:
        return jsonify({'success': False, 'error': _('不存在')}), 404
    return jsonify({'success': True, 'data': item})


@admin_bp.route('/downloads/reorder', methods=['POST'])
def admin_downloads_reorder():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'success': False, 'error': _('ids 不能为空')}), 400
    from models.cms import reorder_downloads
    reorder_downloads(ids)
    return jsonify({'success': True})

# ════════════════════════════════════════════════════════════════
# 模型维护 — Providers + Provider Models CRUD
# ════════════════════════════════════════════════════════════════

@admin_bp.route('/providers', methods=['GET'])
def list_providers():
    """列出所有提供商（含模型列表）"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        providers = [dict(r) for r in conn.execute(
            'SELECT * FROM providers ORDER BY id'
        ).fetchall()]
        for p in providers:
            p['models'] = [dict(r) for r in conn.execute(
                'SELECT * FROM provider_models WHERE provider_id=%s ORDER BY sort_order, id',
                (p['id'],)
            ).fetchall()]
    return jsonify({'success': True, 'data': providers})


@admin_bp.route('/providers/<int:pid>', methods=['PUT'])
def update_provider(pid):
    """更新提供商"""
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    with get_db() as conn:
        row = conn.execute('SELECT * FROM providers WHERE id=%s', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        name = (data.get('name') or row['name']).strip()
        desc = data.get('description', row['description'])
        is_active = data.get('is_active', row['is_active'])
        conn.execute(
            "UPDATE providers SET name=%s, description=%s, is_active=%s, updated_at=NOW() WHERE id=%s",
            (name, desc, int(is_active) if is_active is not None else 1, pid))
        conn.commit()
        _log(admin['user_id'], 'update', 'provider', str(pid), _('更新提供商: {name}', name=name))
    return jsonify({'success': True})


# ── Provider Models CRUD ──

@admin_bp.route('/provider-models', methods=['GET'])
def list_provider_models():
    """列出所有模型（可按 provider_id 筛选）"""
    admin, err = _require_admin()
    if err: return err
    pid = request.args.get('provider_id')
    with get_db() as conn:
        if pid:
            rows = conn.execute(
                'SELECT pm.*, p.name as provider_name, p.slug as provider_slug FROM provider_models pm JOIN providers p ON p.id=pm.provider_id WHERE pm.provider_id=%s ORDER BY pm.sort_order, pm.id',
                (pid,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT pm.*, p.name as provider_name, p.slug as provider_slug FROM provider_models pm JOIN providers p ON p.id=pm.provider_id ORDER BY p.id, pm.sort_order, pm.id'
            ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/provider-models', methods=['POST'])
def create_provider_model():
    """新增模型"""
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    name = (data.get('name') or '').strip()
    provider_id = data.get('provider_id')
    model_name = (data.get('model_name') or '').strip()
    endpoint_url = (data.get('endpoint_url') or '').strip()
    api_key_ref = (data.get('api_key_ref') or '').strip()
    capabilities = (data.get('capabilities') or 'text').strip()
    if not name or not provider_id:
        return jsonify({'success': False, 'error': _('名称和提供商不能为空')}), 400
    with get_db() as conn:
        mid = conn.execute(
            'INSERT INTO provider_models (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
            (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities)).fetchone()['id']
        conn.commit()
        _log(admin['user_id'], 'create', 'provider_model', str(mid), _('新增模型: {name}', name=name))
    return jsonify({'success': True, 'data': {'id': mid}})


@admin_bp.route('/provider-models/<int:mid>', methods=['PUT'])
def update_provider_model(mid):
    """更新模型"""
    admin, err = _require_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    with get_db() as conn:
        row = conn.execute('SELECT * FROM provider_models WHERE id=%s', (mid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        name = (data.get('name') or row['name']).strip()
        provider_id = data.get('provider_id', row['provider_id'])
        model_name = data.get('model_name', row['model_name'])
        endpoint_url = data.get('endpoint_url', row['endpoint_url'])
        api_key_ref = data.get('api_key_ref', row['api_key_ref'])
        capabilities = data.get('capabilities', row['capabilities'])
        is_active = data.get('is_active', row['is_active'])
        sort_order = data.get('sort_order', row['sort_order'])
        conn.execute(
            '''UPDATE provider_models SET provider_id=%s, name=%s, model_name=%s, endpoint_url=%s,
               api_key_ref=%s, capabilities=%s, is_active=%s, sort_order=%s,
               updated_at=NOW() WHERE id=%s''',
            (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities,
             int(is_active) if is_active is not None else 1, sort_order, mid))
        conn.commit()
        _log(admin['user_id'], 'update', 'provider_model', str(mid), _('更新模型: {name}', name=name))
    return jsonify({'success': True})


@admin_bp.route('/provider-models/<int:mid>', methods=['DELETE'])
def delete_provider_model(mid):
    """删除模型"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        row = conn.execute('SELECT name FROM provider_models WHERE id=%s', (mid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        conn.execute('DELETE FROM provider_models WHERE id=%s', (mid,))
        conn.commit()
        _log(admin['user_id'], 'delete', 'provider_model', str(mid), _('删除模型: {name}', name=row['name']))
        return jsonify({'success': True})


# ============================================================
# 口播视频 — 声音克隆 & 数字人视频管理（Agent 矩阵集成）
# ============================================================

import os as _os_media
MEDIA_DIR = _os_media.path.join(_os_media.path.dirname(_os_media.path.abspath(__file__)),
                                 '..', '..', 'data', 'media', 'temp')


def _media_ensure_dir():
    _os_media.makedirs(MEDIA_DIR, exist_ok=True)
    _os_media.makedirs(_os_media.path.join(MEDIA_DIR, 'videos'), exist_ok=True)


# ── 声音模板管理 ──

@admin_bp.route('/media/voice/clone', methods=['POST'])
def media_voice_clone():
    """提交声音克隆任务（通过 Agent 矩阵 dispatch）"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True) or {}
    name = data.get('name', '').strip()
    audio_url = data.get('audio_url', '').strip()
    if not name or not audio_url:
        return jsonify({'success': False, 'error': _('名称和音频URL不能为空')}), 400

    # 写入数据库
    with get_db() as conn:
        vid = conn.execute(
            """INSERT INTO voice_templates (user_id, name, sample_url, provider, status)
               VALUES (%s,%s,%s,%s,'pending') RETURNING id""",
            (admin['user_id'], name, audio_url, 'volcengine')).fetchone()['id']
        conn.commit()

    # 通过 Agent 矩阵 dispatch 到 Media Agent
    try:
        import requests as _req
        token = request.headers.get('Authorization', '')
        resp = _req.post(
            f'http://127.0.0.1:8084/admin/agent-matrix/dispatch',
            json={
                'target_agent_id': _get_media_agent_id(),
                'action': 'voice_clone',
                'params': {'audio_url': audio_url, 'voice_name': name}
            },
            headers={'Authorization': token, 'Content-Type': 'application/json'},
            timeout=60
        )
        result = resp.json()
        if result.get('success'):
            voice_id = result.get('data', {}).get('voice_id', '')
            with get_db() as conn:
                conn.execute(
                    "UPDATE voice_templates SET external_voice_id=%s, status='ready', updated_at=NOW() WHERE id=%s",
                    (voice_id, vid))
                conn.commit()
            return jsonify({'success': True, 'data': {'id': vid, 'voice_id': voice_id, 'status': 'ready'}})
        else:
            with get_db() as conn:
                conn.execute(
                    "UPDATE voice_templates SET status='failed', error_msg=%s, updated_at=NOW() WHERE id=%s",
                    (result.get('data', {}).get('error', result.get('error', _('未知错误'))), vid))
                conn.commit()
            return jsonify({'success': False, 'error': result.get('data', {}).get('error', result.get('error', ''))}), 500
    except Exception as e:
        with get_db() as conn:
            conn.execute(
                "UPDATE voice_templates SET status='failed', error_msg=%s, updated_at=NOW() WHERE id=%s",
                (str(e), vid))
            conn.commit()
        return jsonify({'success': False, 'error': _('Agent 调用失败: {error}', error=e)}), 500


@admin_bp.route('/media/voice/list', methods=['GET'])
def media_voice_list():
    """声音模板列表"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM voice_templates WHERE user_id=%s ORDER BY created_at DESC",
            (admin['user_id'],)
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/media/voice/<int:vid>', methods=['DELETE'])
def media_voice_delete(vid):
    """删除声音模板"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute("DELETE FROM voice_templates WHERE id=%s AND user_id=%s", (vid, admin['user_id']))
        conn.commit()
    return jsonify({'success': True})


# ── 视频任务管理 ──

@admin_bp.route('/media/video/create', methods=['POST'])
def media_video_create():
    """创建口播视频生成任务"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True) or {}
    title = data.get('title', '').strip()
    text = data.get('text', '').strip()
    voice_id = data.get('voice_id', '')
    image_url = data.get('image_url', data.get('avatar_url', ''))

    if not title or not text:
        return jsonify({'success': False, 'error': _('标题和文案不能为空')}), 400
    if not voice_id:
        return jsonify({'success': False, 'error': _('请先选择已克隆的声音')}), 400

    with get_db() as conn:
        tid = conn.execute(
            """INSERT INTO video_tasks (user_id, title, voice_template_id, text_content,
               avatar_image_url, provider, status) VALUES (%s,%s,%s,%s,%s,%s,'pending') RETURNING id""",
            (admin['user_id'], title, int(voice_id) if voice_id.isdigit() else 0,
             text, image_url, 'volcengine')).fetchone()['id']
        conn.commit()

    # 通过 Agent 矩阵 dispatch
    try:
        import requests as _req
        token = request.headers.get('Authorization', '')
        resp = _req.post(
            f'http://127.0.0.1:8084/admin/agent-matrix/dispatch',
            json={
                'target_agent_id': _get_media_agent_id(),
                'action': 'avatar_video',
                'params': {'text': text, 'voice_id': voice_id, 'image_url': image_url}
            },
            headers={'Authorization': token, 'Content-Type': 'application/json'},
            timeout=30
        )
        result = resp.json()
        if result.get('success'):
            ext_task_id = result.get('data', {}).get('task_id', '')
            with get_db() as conn:
                conn.execute(
                    "UPDATE video_tasks SET external_task_id=%s, status='processing', updated_at=NOW() WHERE id=%s",
                    (ext_task_id, tid))
                conn.commit()
            return jsonify({'success': True, 'data': {'id': tid, 'status': 'processing', 'external_task_id': ext_task_id}})
        else:
            with get_db() as conn:
                conn.execute(
                    "UPDATE video_tasks SET status='failed', error_msg=%s, updated_at=NOW() WHERE id=%s",
                    (result.get('data', {}).get('error', result.get('error', _('未知错误'))), tid))
                conn.commit()
            return jsonify({'success': False, 'error': result.get('data', {}).get('error', result.get('error', ''))}), 500
    except Exception as e:
        with get_db() as conn:
            conn.execute(
                "UPDATE video_tasks SET status='failed', error_msg=%s, updated_at=NOW() WHERE id=%s",
                (str(e), tid))
            conn.commit()
        return jsonify({'success': False, 'error': _('Agent 调用失败: {error}', error=e)}), 500


@admin_bp.route('/media/video/list', methods=['GET'])
def media_video_list():
    """视频任务列表 + 媒体库视频"""
    admin, err = _require_admin()
    if err: return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    with get_db() as conn:
        # AI 生成的视频
        ai_rows = conn.execute(
            """SELECT v.*, vt.name as voice_name, vt.external_voice_id
               FROM video_tasks v LEFT JOIN voice_templates vt ON vt.id=v.voice_template_id
               WHERE v.user_id=%s ORDER BY v.created_at DESC""",
            (admin['user_id'],)
        ).fetchall()
        # 媒体库视频
        lib_rows = conn.execute(
            "SELECT * FROM media_files WHERE mime_type LIKE 'video/%' ORDER BY created_at DESC"
        ).fetchall()

    # 合并：媒体库视频映射为 video_tasks 格式
    items = [dict(r) for r in ai_rows]
    for r in lib_rows:
        items.append({
            'id': r['id'] + 100000,
            'title': r['original_name'],
            'text_content': '',
            'output_url': r['file_path'],
            'avatar_image_url': '',
            'voice_name': _('📁 本地上传'),
            'external_voice_id': '',
            'status': 'done',
            'is_homepage': 0,
            'published_douyin': 0,
            'media_type': 'library',
            'created_at': r['created_at'],
            'user_id': admin['user_id'],
            'voice_template_id': None,
        })

    total = len(items)
    # 分页
    items = sorted(items, key=lambda x: x['created_at'] or '', reverse=True)
    paged = items[offset:offset + limit]

    return jsonify({'success': True, 'data': {'items': paged, 'total': total, 'page': page}})


@admin_bp.route('/media/video/<int:tid>/status', methods=['GET'])
def media_video_status(tid):
    """轮询视频任务状态"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        task = conn.execute("SELECT * FROM video_tasks WHERE id=%s AND user_id=%s", (tid, admin['user_id'])).fetchone()
        if not task:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        task = dict(task)

    # 如果还在 processing，查询火山引擎状态
    if task['status'] == 'processing' and task['external_task_id']:
        try:
            import requests as _req
            token = request.headers.get('Authorization', '')
            resp = _req.post(
                f'http://127.0.0.1:8084/admin/agent-matrix/dispatch',
                json={
                    'target_agent_id': _get_media_agent_id(),
                    'action': 'query',
                    'params': {'task_id': task['external_task_id']}
                },
                headers={'Authorization': token, 'Content-Type': 'application/json'},
                timeout=30
            )
            result = resp.json()
            if result.get('success'):
                qdata = result.get('data', {})
                if qdata.get('status') == 'done':
                    video_url = qdata.get('video_url', '')
                    # 下载视频到本地
                    _media_ensure_dir()
                    import urllib.request
                    local_path = _os_media.path.join(MEDIA_DIR, 'videos', f'{tid}.mp4')
                    try:
                        urllib.request.urlretrieve(video_url, local_path)
                        output_url = f'/admin/media/video/{tid}/download'
                    except Exception:
                        output_url = video_url
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE video_tasks SET status='done', output_url=%s, updated_at=NOW() WHERE id=%s",
                            (output_url, tid))
                        conn.commit()
                    task['status'] = 'done'
                    task['output_url'] = output_url
                elif qdata.get('status') == 'failed':
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE video_tasks SET status='failed', error_msg=%s, updated_at=NOW() WHERE id=%s",
                            (qdata.get('error', _('生成失败')), tid))
                        conn.commit()
                    task['status'] = 'failed'
                    task['error_msg'] = qdata.get('error', '')
        except Exception as e:
            logger.warning(_('查询视频任务状态失败: {error}', error=e))

    return jsonify({'success': True, 'data': task})


@admin_bp.route('/media/video/<int:tid>/download', methods=['GET'])
def media_video_download(tid):
    """下载视频文件"""
    admin, err = _require_admin()
    if err: return err
    # 媒体库视频（id > 100000）
    if tid > 100000:
        real_id = tid - 100000
        with get_db() as conn:
            row = conn.execute("SELECT * FROM media_files WHERE id=%s", (real_id,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('文件不存在')}), 404
        fp = os.path.join(MEDIA_LIB_DIR, row['filename'])
        if not os.path.exists(fp):
            return jsonify({'success': False, 'error': _('文件已删除')}), 404
        return _send_file_or_stream(fp, row['original_name'], row['mime_type'])
    # AI 生成视频
    local_path = _os_media.path.join(MEDIA_DIR, 'videos', f'{tid}.mp4')
    if not _os_media.path.exists(local_path):
        return jsonify({'success': False, 'error': _('文件不存在或已过期')}), 404
    from flask import send_file
    return send_file(local_path, as_attachment=True, download_name=f'video_{tid}.mp4', mimetype='video/mp4')


@admin_bp.route('/media/video/<int:tid>', methods=['DELETE'])
def media_video_delete(tid):
    """删除视频任务及文件"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute("DELETE FROM video_tasks WHERE id=%s AND user_id=%s", (tid, admin['user_id']))
        conn.commit()
    # 删除本地文件
    local_path = _os_media.path.join(MEDIA_DIR, 'videos', f'{tid}.mp4')
    if _os_media.path.exists(local_path):
        _os_media.remove(local_path)
    return jsonify({'success': True})


@admin_bp.route('/media/video/<int:tid>/retry', methods=['POST'])
def media_video_retry(tid):
    """重试失败任务"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        task = conn.execute("SELECT * FROM video_tasks WHERE id=%s AND user_id=%s", (tid, admin['user_id'])).fetchone()
        if not task:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        task = dict(task)
        conn.execute("UPDATE video_tasks SET status='pending', error_msg='', updated_at=NOW() WHERE id=%s", (tid,))
        conn.commit()

    # 重新 dispatch
    try:
        import requests as _req
        token = request.headers.get('Authorization', '')
        voice_id = task.get('voice_template_id', '')
        resp = _req.post(
            f'http://127.0.0.1:8084/admin/agent-matrix/dispatch',
            json={
                'target_agent_id': _get_media_agent_id(),
                'action': 'avatar_video',
                'params': {'text': task['text_content'], 'voice_id': str(voice_id),
                           'image_url': task.get('avatar_image_url', '')}
            },
            headers={'Authorization': token, 'Content-Type': 'application/json'},
            timeout=30
        )
        result = resp.json()
        if result.get('success'):
            ext_task_id = result.get('data', {}).get('task_id', '')
            with get_db() as conn:
                conn.execute(
                    "UPDATE video_tasks SET external_task_id=%s, status='processing', updated_at=NOW() WHERE id=%s",
                    (ext_task_id, tid))
                conn.commit()
            return jsonify({'success': True, 'data': {'id': tid, 'status': 'processing'}})
        else:
            with get_db() as conn:
                conn.execute(
                    "UPDATE video_tasks SET status='failed', error_msg=%s WHERE id=%s",
                    (result.get('data', {}).get('error', _('重试失败')), tid))
                conn.commit()
            return jsonify({'success': False, 'error': result.get('data', {}).get('error', '')}), 500
    except Exception as e:
        with get_db() as conn:
            conn.execute("UPDATE video_tasks SET status='failed', error_msg=%s WHERE id=%s", (str(e), tid))
            conn.commit()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/media/video/<int:tid>/toggle-homepage', methods=['POST'])
def media_video_toggle_homepage(tid):
    """切换首页展示状态"""
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        task = conn.execute("SELECT is_homepage FROM video_tasks WHERE id=%s", (tid,)).fetchone()
        if not task:
            return jsonify({'success': False, 'error': _('不存在')}), 404
        new_val = 0 if task['is_homepage'] else 1
        conn.execute("UPDATE video_tasks SET is_homepage=%s, updated_at=NOW() WHERE id=%s", (new_val, tid))
        conn.commit()
    return jsonify({'success': True, 'data': {'is_homepage': new_val}})


# ── 公开 API：首页视频窗口 ──

@admin_bp.route('/media/video/homepage', methods=['GET'])
def media_video_homepage():
    """获取首页展示的视频（公开接口）"""
    with get_db() as conn:
        task = conn.execute(
            "SELECT id, title, text_content, output_url, avatar_image_url, created_at "
            "FROM video_tasks WHERE is_homepage=1 AND status='done' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    return jsonify({'success': True, 'data': dict(task) if task else None})


# ═══════════════════════════════════════════════════════════
#  本地媒体库 API — 上传 / 列表 / 下载 / 删除 / 推送
# ═══════════════════════════════════════════════════════════

MEDIA_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', '..', 'admin', 'static', 'media')

def _media_lib_ensure_dir():
    os.makedirs(MEDIA_LIB_DIR, exist_ok=True)
    os.makedirs(os.path.join(MEDIA_LIB_DIR, 'thumbs'), exist_ok=True)

@admin_bp.route('/media-library/upload', methods=['POST'])
def media_library_upload():
    admin, err = _require_admin()
    if err:
        return err
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': _('未选择文件')}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'success': False, 'error': _('文件名为空')}), 400
    _media_lib_ensure_dir()
    import uuid as _uuid
    safe_name = _uuid.uuid4().hex + os.path.splitext(f.filename)[1].lower()
    save_path = os.path.join(MEDIA_LIB_DIR, safe_name)
    f.save(save_path)
    file_size = os.path.getsize(save_path)
    mime = f.content_type or 'application/octet-stream'
    # 兜底：浏览器可能不传正确 content_type，按扩展名补
    if mime == 'application/octet-stream' or not mime:
        ext = os.path.splitext(f.filename)[1].lower()
        ext_map = {'.mp4':'video/mp4','.mov':'video/quicktime','.avi':'video/x-msvideo',
                   '.webm':'video/webm','.mkv':'video/x-matroska','.flv':'video/x-flv','.m4v':'video/mp4',
                   '.mp3':'audio/mpeg','.wav':'audio/wav','.ogg':'audio/ogg','.flac':'audio/flac',
                   '.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.gif':'image/gif','.webp':'image/webp'}
        mime = ext_map.get(ext, mime)
    # 缩略图：视频缩略图由本地 FFmpeg 预生成后一并上传，服务器仅存储分发
    # 图片本身就是缩略图，不设 thumb_path，前端用 file_path 显示
    thumb_name = ''

    with get_db() as conn:
        new_id = conn.execute(
            "INSERT INTO media_files (filename, original_name, mime_type, file_size, file_path, thumb_path) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (safe_name, f.filename, mime, file_size, 'media/' + safe_name,
             'media/thumbs/' + thumb_name if thumb_name else '')
        ).fetchone()['id']
        conn.commit()
    return jsonify({
        'success': True,
        'data': {
            'id': new_id, 'filename': safe_name, 'original_name': f.filename,
            'mime_type': mime, 'file_size': file_size,
            'thumb_path': 'media/thumbs/' + thumb_name if thumb_name else ''
        }
    })

@admin_bp.route('/media-library/list', methods=['GET'])
def media_library_list():
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    if limit > 500: limit = 500
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM media_files").fetchone()['c']
        rows = conn.execute(
            "SELECT id, filename, original_name, mime_type, file_size, file_path, thumb_path, push_status, created_at FROM media_files ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows], 'total': total, 'page': page, 'limit': limit})

@admin_bp.route('/media-library/<int:fid>', methods=['DELETE'])
def media_library_delete(fid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute("SELECT * FROM media_files WHERE id=%s", (fid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('文件不存在')}), 404
        fp = os.path.join(MEDIA_LIB_DIR, row['filename'])
        if os.path.exists(fp):
            os.remove(fp)
        if row['thumb_path']:
            tp = os.path.join(MEDIA_LIB_DIR, '..', row['thumb_path'])
            if os.path.exists(tp):
                os.remove(tp)
        conn.execute("DELETE FROM media_files WHERE id=%s", (fid,))
        conn.commit()
    return jsonify({'success': True})

@admin_bp.route('/media-library/<int:fid>/download', methods=['GET'])
def media_library_download(fid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute("SELECT * FROM media_files WHERE id=%s", (fid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('文件不存在')}), 404
    fp = os.path.join(MEDIA_LIB_DIR, row['filename'])
    if not os.path.exists(fp):
        return jsonify({'success': False, 'error': _('文件已删除')}), 404
    return _send_file_or_stream(fp, row['original_name'], row['mime_type'])

@admin_bp.route('/media-library/<int:fid>/push', methods=['POST'])
def media_library_push(fid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    target = data.get('target', 'feishu')
    with get_db() as conn:
        row = conn.execute("SELECT * FROM media_files WHERE id=%s", (fid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('文件不存在')}), 404

    file_url = deploy.url("agent") + "/static/" + row["file_path"]
    filename = row['original_name']
    mime = row['mime_type']

    result = {'success': True, 'target': target}
    if target in ('feishu', 'wecom'):
        try:
            im = None
            import flask as _flask
            pm = _flask.current_app.extensions.get('plugin_manager') if hasattr(_flask.current_app, 'extensions') else None
            if pm and pm.is_enabled('im_gateway'):
                im = pm.get_instance('im_gateway')
            if im is None:
                result = {'success': False, 'error': _('IM 网关插件未启用，无法推送')}
            else:
                im.push_media(target, file_url, filename, mime)
        except Exception as e:
            result = {'success': False, 'error': _('{target} 推送失败: {error}', target=target, error=str(e))}

    if result['success']:
        with get_db() as conn:
            conn.execute(
                "UPDATE media_files SET push_status='done', push_target=%s, "
                "pushed_at=NOW(), updated_at=NOW() WHERE id=%s",
                (target, fid)
            )
            conn.commit()
    return jsonify(result)


# NOTE: 媒体推送函数（_push_media_to_feishu / _push_media_to_wecom / _upload_feishu_*
#        / _fetch_as_base64）已迁移至 plugins/im_gateway/adapters/，
#        由 media_library_push 通过插件实例 im.push_media() 调用。


def _send_file_or_stream(fp, filename, mime):
    from flask import Response, request as _req
    range_header = _req.headers.get('Range', None)
    size = os.path.getsize(fp)
    if range_header:
        import re
        byte_range = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if byte_range:
            start = int(byte_range.group(1))
            end = int(byte_range.group(2)) if byte_range.group(2) else size - 1
            length = end - start + 1
            with open(fp, 'rb') as f:
                f.seek(start)
                data = f.read(length)
            return Response(data, 206, {
                'Content-Type': mime,
                'Content-Range': 'bytes {}-{}/{}'.format(start, end, size),
                'Content-Length': str(length),
                'Accept-Ranges': 'bytes',
                'Content-Disposition': 'inline; filename="{}"'.format(filename)
            })
    from flask import send_file as _sf
    return _sf(fp, mimetype=mime, as_attachment=False,
               download_name=filename, conditional=True)


# =============================================
# OAuth 提供商配置（多租户抖音登录）
# =============================================

# ════════════════════════════════════════════════════════════════
# OAuth 登录配置管理已迁移至 plugins/oauth_config/（Phase 4A 逻辑解耦）
#   - REST 路由：plugins/oauth_config/routes.py（/admin/oauth/configs）
#   - oauth_providers 表仍留主库，供登录回调链路（auth.py / *_service）共享读取
#   - 登录回调链路（auth.py oauth_login/callback、oauth_service）保持不变
# ════════════════════════════════════════════════════════════════


def _get_media_agent_id():
    """获取 Media Agent 的 ID（带缓存）"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM agent_matrix WHERE name='Media Agent' AND role_type='sub' AND is_active=1"
        ).fetchone()
    if row:
        return row['id']
    # fallback: 找 domain='media' 的活跃 agent
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM agent_matrix WHERE domain='media' AND is_active=1 LIMIT 1"
        ).fetchone()
    return row['id'] if row else 0


# =============================================
# API Quota Management
# =============================================
@admin_bp.route('/quota/stats', methods=['GET'])
def quota_stats():
    """API配额概览统计数据"""
    admin, err = _require_admin()
    if err:
        return err
    from models import TIERS
    with get_db() as conn:
        total_keys = conn.execute('SELECT COUNT(*) as c FROM api_keys').fetchone()['c']
        active_keys = conn.execute('SELECT COUNT(*) as c FROM api_keys WHERE active=1').fetchone()['c']
        today_calls = conn.execute("SELECT COALESCE(SUM(calls_today),0) as c FROM api_keys WHERE last_reset=CURRENT_DATE").fetchone()['c']
        total_calls = conn.execute('SELECT COALESCE(SUM(calls_total),0) as c FROM api_keys').fetchone()['c']
        user_tiers = conn.execute(
            "SELECT a.tier, COUNT(DISTINCT a.user_id) as count FROM app_authorizations a WHERE a.active=1 GROUP BY a.tier"
        ).fetchall()
    tier_breakdown = {}
    for t in ['free', 'standard', 'pro']:
        tier_breakdown[t] = {'name': TIERS.get(t, {}).get('name', t), 'daily_limit': TIERS.get(t, {}).get('daily_limit', 0), 'count': 0}
    for r in user_tiers:
        if r['tier'] in tier_breakdown:
            tier_breakdown[r['tier']]['count'] = r['count']
    return jsonify({'success': True, 'data': {
        'total_keys': total_keys, 'active_keys': active_keys,
        'today_calls': today_calls, 'total_calls': total_calls,
        'tier_breakdown': tier_breakdown
    }})


@admin_bp.route('/quota/users', methods=['GET'])
def quota_users():
    """查询所有用户的配额信息"""
    admin, err = _require_admin()
    if err:
        return err
    from models import TIERS
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    search = request.args.get('search', '').strip()

    with get_db() as conn:
        where = ''
        params = []
        if search:
            where = "WHERE (u.username LIKE %s OR u.display_name LIKE %s)"
            params = [f'%{search}%', f'%{search}%']
        total = conn.execute(f'SELECT COUNT(*) as c FROM users u {where}', params).fetchone()['c']
        rows = conn.execute(f"""
            SELECT u.id, u.username, u.display_name, u.created_at,
                   COALESCE(a.tier, 'free') as tier,
                   COALESCE(a.calls_today, 0) as calls_today,
                   COALESCE(a.calls_total, 0) as calls_total,
                   (SELECT COUNT(*) FROM api_keys k WHERE k.user_id=u.id AND k.active=1) as active_keys
            FROM users u
            LEFT JOIN app_authorizations a ON u.id=a.user_id AND a.active=1
            {where}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset]).fetchall()
        users = [dict(r) for r in rows]
        for u in users:
            tier_info = TIERS.get(u['tier'], TIERS['free'])
            u['daily_limit'] = tier_info['daily_limit']
            u['tier_name'] = tier_info['name']
    return jsonify({'success': True, 'data': {
        'total': total, 'page': page, 'limit': limit, 'users': users
    }})


@admin_bp.route('/quota/users/<int:uid>/tier', methods=['POST'])
def quota_set_user_tier(uid):
    """设置用户的API配额等级"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    tier = data.get('tier', '').strip()
    from models import TIERS
    if tier not in TIERS:
        return jsonify({'success': False, 'error': _('无效的等级: {tier}', tier=tier)}), 400
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM app_authorizations WHERE user_id=%s AND active=1", (uid,)
        ).fetchone()
        if existing:
            conn.execute("UPDATE app_authorizations SET tier=%s, last_reset=CURRENT_DATE WHERE id=%s", (tier, existing['id']))
        else:
            conn.execute(
                "INSERT INTO app_authorizations (user_id, app_name, tier, active) VALUES (%s, 'platform', %s, 1)",
                (uid, tier)
            )
        conn.commit()
    _log(admin['user_id'], 'set_user_tier', 'user', str(uid), f'tier→{tier}')
    return jsonify({'success': True, 'message': _('已更新用户等级为 {name}', name=TIERS[tier]["name"])})


@admin_bp.route('/quota/keys', methods=['GET'])
def quota_keys():
    """查询所有API Key的配额使用情况"""
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM api_keys').fetchone()['c']
        rows = conn.execute("""
            SELECT k.id, k.name, k.key_prefix, k.calls_today, k.calls_total,
                   k.last_reset, k.last_used, k.active, k.created_at,
                   COALESCE(u.display_name, u.username, '') as user_name, u.id as user_id,
                   COALESCE(a.tier, 'free') as tier
            FROM api_keys k
            LEFT JOIN users u ON k.user_id=u.id
            LEFT JOIN app_authorizations a ON u.id=a.user_id AND a.active=1
            ORDER BY k.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset)).fetchall()
    return jsonify({'success': True, 'data': {
        'total': total, 'page': page, 'limit': limit, 'keys': [dict(r) for r in rows]
    }})


@admin_bp.route('/quota/keys/<int:kid>/reset', methods=['POST'])
def quota_reset_key(kid):
    """重置单个API Key的日调用量"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute("UPDATE api_keys SET calls_today=0, last_reset=CURRENT_DATE WHERE id=%s", (kid,))
        conn.commit()
    _log(admin['user_id'], 'reset_key_quota', 'api_key', str(kid))
    return jsonify({'success': True, 'message': _('已重置该密钥的日调用量')})


@admin_bp.route('/quota/overview', methods=['GET'])
def quota_overview():
    """详细配额使用报表（最近7天趋势）"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        # 每日总调用量最近7天
        daily = conn.execute("""
            SELECT last_reset as date, SUM(calls_today) as calls_count
            FROM api_keys WHERE last_reset >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY last_reset ORDER BY last_reset
        """).fetchall()
        daily_stats = [dict(r) for r in daily]
        # 超出阈值（calls_today >= tier daily_limit * 0.8）的key
        from models import TIERS
        near_limit = conn.execute("""
            SELECT k.id, k.name, k.key_prefix, k.calls_today,
                   COALESCE(u.display_name, u.username, '') as user_name
            FROM api_keys k
            LEFT JOIN users u ON k.user_id=u.id
            LEFT JOIN app_authorizations a ON u.id=a.user_id AND a.active=1
            WHERE k.active=1
        """).fetchall()
        near_limit_list = []
        for r in near_limit:
            tier_key = 'free'
            with get_db() as conn2:
                tr = conn2.execute(
                    "SELECT tier FROM app_authorizations WHERE user_id=%s AND active=1",
                    (r['user_id'],)
                ).fetchone()
                if tr:
                    tier_key = tr['tier']
            limit_val = TIERS.get(tier_key, TIERS['free'])['daily_limit']
            if limit_val > 0 and r['calls_today'] >= limit_val * 0.8:
                nr = dict(r)
                nr['daily_limit'] = limit_val
                nr['usage_pct'] = round(r['calls_today'] / limit_val * 100, 1)
                near_limit_list.append(nr)
    return jsonify({'success': True, 'data': {
        'daily_stats': daily_stats,
        'near_limit_keys': near_limit_list
    }})


# ── 客户管理 (Customer Management) ──

@admin_bp.route('/customers', methods=['GET'])
def customer_list():
    """客户列表 — 统一查看个人/企业认证状态"""
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("search", "").strip()
    cust_type = request.args.get("type", "").strip()       # enterprise / individual / ''
    verify_status = request.args.get("verify", "").strip() # verified / unverified / ''
    offset = (page - 1) * limit

    where = []
    params = []

    if search:
        where.append("(u.phone LIKE %s OR COALESCE(u.display_name, u.username) LIKE %s OR u.enterprise_name LIKE %s)")
        s = '%' + search + '%'
        params.extend([s, s, s])

    if cust_type == 'enterprise':
        where.append("u.enterprise_verified = 1")
    elif cust_type == 'individual':
        where.append("u.enterprise_verified = 0")

    if verify_status == 'verified':
        where.append("(u.enterprise_verified = 1 OR u.is_real_name_verified = 1)")
    elif verify_status == 'unverified':
        where.append("u.enterprise_verified = 0 AND u.is_real_name_verified = 0")

    wsql = 'WHERE ' + ' AND '.join(where) if where else ''

    from_sql = ("FROM users u")
    sql = ("SELECT u.id, u.phone, COALESCE(u.display_name, u.username) as nickname, u.email, "
           "u.created_at, u.last_login, u.active, "
           "u.is_real_name_verified, u.real_name_verified_at, u.verified_by, "
           "u.enterprise_name, u.enterprise_tax_id, u.enterprise_verified, u.enterprise_verified_at, "
           "'' as plan_key, NULL as sub_expires "
           + from_sql + ' ' + wsql + ' ORDER BY u.created_at DESC LIMIT %s OFFSET %s')
    csql = 'SELECT COUNT(DISTINCT u.id) as c ' + from_sql + ' ' + wsql

    with get_db() as conn:
        total = conn.execute(csql, params).fetchone()['c']
        rows = conn.execute(sql, params + [limit, offset]).fetchall()

    customers = []
    for r in rows:
        c = dict(r)
        if c.get('enterprise_verified'):
            c['cert_status'] = 'enterprise'
            c['cert_badge'] = _('Enterprise Verified')
        elif c.get('is_real_name_verified'):
            c['cert_status'] = 'individual'
            c['cert_badge'] = _('Individual Verified')
        else:
            c['cert_status'] = 'none'
            c['cert_badge'] = _('Unverified')
        customers.append(c)

    return jsonify({"success": True, "data": {
        "total": total, "page": page, "limit": limit,
        "customers": customers,
    }})





# ════════════════════════════════════════════════════════════════
# i18n 翻译管理
# ════════════════════════════════════════════════════════════════

@admin_bp.route('/i18n/translations', methods=['GET'])
def admin_i18n_list():
    """列出翻译（分页+搜索）"""
    admin, err = _require_admin()
    if err:
        return err

    locale = request.args.get('locale', 'en')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    offset = (page - 1) * limit

    from i18n import list_translations
    data = list_translations(locale=locale, search=search, offset=offset, limit=limit)
    return jsonify({'success': True, 'data': data})


@admin_bp.route('/i18n/translations', methods=['POST'])
def admin_i18n_create():
    """新增一条翻译"""
    admin, err = _require_admin()
    if err:
        return err

    data = request.get_json(force=True) or {}
    locale = data.get('locale', 'en')
    source = (data.get('source') or '').strip()
    translation = (data.get('translation') or '').strip()

    if not source:
        return jsonify({'success': False, 'error': _('原文不能为空')}), 400

    from i18n import set_translation
    ok = set_translation(locale, source, translation, is_auto=0)
    return jsonify({'success': ok, 'error': '' if ok else _('写入失败')}),
    201 if ok else 400,


@admin_bp.route('/i18n/translations/<int:tid>', methods=['PUT'])
def admin_i18n_update(tid):
    """编辑一条翻译"""
    admin, err = _require_admin()
    if err:
        return err

    data = request.get_json(force=True) or {}
    translation = (data.get('translation') or '').strip()
    is_auto = data.get('is_auto', 0)

    with get_db() as conn:
        exist = conn.execute('SELECT id FROM i18n_strings WHERE id=%s', (tid,)).fetchone()
        if not exist:
            return jsonify({'success': False, 'error': _('翻译不存在')}), 404
        conn.execute(
            "UPDATE i18n_strings SET translation=%s, is_auto=%s, updated_at=NOW() WHERE id=%s",
            (translation, is_auto, tid)
        )
        conn.commit()

    return jsonify({'success': True, 'message': _('Updated')})


@admin_bp.route('/i18n/translations/<int:tid>', methods=['DELETE'])
def admin_i18n_delete(tid):
    """删除一条翻译"""
    admin, err = _require_admin()
    if err:
        return err

    from i18n import delete_translation
    ok = delete_translation(tid)
    return jsonify({'success': ok, 'error': '' if ok else _('Delete failed')})


@admin_bp.route('/i18n/seed', methods=['POST'])
def admin_i18n_seed():
    """从 YAML 同步翻译到 DB"""
    admin, err = _require_admin()
    if err:
        return err

    locale = request.args.get('locale', 'en')
    from i18n import seed_from_yaml
    count = seed_from_yaml(locale)
    return jsonify({'success': True, 'message': _('已同步 {count} 条到 DB', count=count)})
