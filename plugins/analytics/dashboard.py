#!/usr/bin/env python3
"""
analytics/dashboard.py — 分析仪表盘 Flask Blueprint

提供:
  - 管理后台页面: /admin/analytics
  - REST API: /admin/analytics/api/*

集成方式:
  from analytics.dashboard import analytics_bp
  app.register_blueprint(analytics_bp)
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, render_template, Response, g, current_app

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
from . import models as am
from .tracker import track_event, create_alert, list_alerts, update_alert, delete_alert
from .geoip import get_market, download_geolite2_auto, download_geolite2_cdn, download_ip2region_auto, get_geoip_status, detect_client_market, install_geolite2_file
from .tracker import generate_report, generate_insight_text

analytics_bp = Blueprint('analytics', __name__, url_prefix='/admin/analytics',
                         template_folder='templates',
                         static_folder='static',
                         static_url_path='/admin/analytics/static')

# i18n 桥接 — 由插件注入
_t = lambda s: s


def init_i18n(t_func):
    global _t
    _t = t_func


# ─── 鉴权 ──────────────────────────────────────────────────────────────────────

_AUTH_EXEMPT_PATHS = ['/admin/analytics/static/', '/admin/analytics/api/v1/log', '/admin/analytics/api/v1/event']

@analytics_bp.before_request
def check_auth():
    """所有 analytics 路由都需要管理员 JWT 验证（除日志/事件采集 API）"""
    path = request.path
    for exempt in _AUTH_EXEMPT_PATHS:
        if path.startswith(exempt):
            return None

    from services.jwt_service import validate_token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.args.get('token')
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        if request.is_json or path.startswith('/admin/analytics/api/'):
            return jsonify({'success': False, 'error': _t('Unauthorized')}), 401
        # Direct access without admin token → redirect to login
        from flask import redirect
        return redirect('/admin/login')
    return None


# ─── 页面路由 ───────────────────────────────────────────────────────────────────

# ─── 静态文件 ──────────────────────────────────────────────────────────────────

@analytics_bp.route('/static/<path:filename>')
def analytics_static(filename):
    """提供静态文件，包括 china.json 地图数据等"""
    from flask import send_from_directory
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


# ─── 页面路由 ───────────────────────────────────────────────────────────────────

@analytics_bp.route('/')
def analytics_page():
    """渲染分析仪表盘页面"""
    return render_template('analytics.html', geo_market=get_market())


# ─── 原始日志采集 API（供其他服务使用） ────────────────────────────────────────

@analytics_bp.route('/api/v1/log', methods=['POST'])
def api_log():
    """
    记录一条访问日志（服务端调用）
    Body: {
        "path": "/stocks/000001",
        "user_agent": "...",
        "ip": "192.168.1.1",
        "referer": "...",
        "status_code": 200,
        "response_time": 45,
        ...
    }
    """
    data = request.get_json(silent=True) or {}
    if not data.get('path'):
        return jsonify({'success': False, 'error': _t('path required')}), 400

    conn = am.get_db()
    try:
        now = int(time.time())
        today = datetime.now().strftime('%Y-%m-%d')
        ip_prefix = am.hash_ip(data.get('ip', ''))
        ua = data.get('user_agent', '')
        visitor_hash = am.make_visitor_hash(ip_prefix, ua, today)
        session_hash = am.make_session_hash(visitor_hash, now)

        log_data = {
            'timestamp': data.get('timestamp', now),
            'visitor_hash': visitor_hash,
            'session_hash': session_hash,
            'ip_prefix': ip_prefix,
            'user_agent': ua,
            'path': data.get('path', '/'),
            'query_string': data.get('query_string', ''),
            'referer': data.get('referer', ''),
            'status_code': data.get('status_code', 200),
            'response_time': data.get('response_time', 0),
            'request_method': data.get('method', 'GET'),
            'service_name': data.get('service_name', 'api'),
            'language': data.get('language', ''),
            'is_bot': 1 if am.is_bot(ua) else 0,
        }
        log_id = am.insert_log(conn, log_data)
        return jsonify({'success': True, 'log_id': log_id})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/event', methods=['POST'])
def api_event():
    """
    记录自定义业务事件
    Body: {
        "event_name": "launch_agent",
        "category": "agent",
        "label": "hermes",
        "value": 0,
        "path": "/dashboard",
        "metadata": {...}
    }
    """
    data = request.get_json(silent=True) or {}
    if not data.get('event_name'):
        return jsonify({'success': False, 'error': _t('event_name required')}), 400

    event_id = track_event(
        event_name=data['event_name'],
        category=data.get('category', ''),
        label=data.get('label', ''),
        value=data.get('value', 0),
        path=data.get('path', ''),
        service_name=data.get('service_name', 'api'),
        metadata=data.get('metadata'),
    )
    return jsonify({'success': True, 'event_id': event_id})


# ─── 查询 API ──────────────────────────────────────────────────────────────────

@analytics_bp.route('/api/v1/realtime')
def api_realtime():
    """实时概览"""
    conn = am.get_db()
    try:
        data = am.get_realtime(conn)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/trend')
def api_trend():
    """流量趋势"""
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()
    try:
        data = am.get_trend(conn, days)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/hourly')
def api_hourly():
    """小时级数据"""
    date_str = request.args.get('date', '')
    conn = am.get_db()
    try:
        data = am.get_hourly_breakdown(conn, date_str if date_str else None)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/pages')
def api_pages():
    """页面热度排行"""
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 20, type=int)
    conn = am.get_db()
    try:
        data = am.get_page_rank(conn, days, limit)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/sources')
def api_sources():
    """来源分析"""
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()
    try:
        data = am.get_source_analysis(conn, days)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/geo')
def api_geo():
    """地理分布"""
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()
    try:
        data = am.get_geo_distribution(conn, days)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/geo/cities')
def api_geo_cities():
    """城市分布（可按国家筛选）"""
    days = request.args.get('days', 30, type=int)
    country = request.args.get('country', '')
    conn = am.get_db()
    try:
        data = am.get_city_distribution(conn, days, country)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/geo/china-cities')
def api_china_cities():
    """中国城市分布（主视图，自动拼音转中文）"""
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()
    try:
        data = am.get_china_city_distribution(conn, days)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/geo/market')
def api_geo_market():
    """根据客户端 IP 判断市场：'cn' 或 'intl'"""
    client_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    if not client_ip:
        client_ip = request.headers.get('X-Real-IP', '')
    if not client_ip:
        client_ip = request.remote_addr or ''
    market = detect_client_market(client_ip)
    return jsonify({'success': True, 'data': {'market': market}})


@analytics_bp.route('/api/v1/devices')
def api_devices():
    """设备分布"""
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()
    try:
        data = am.get_device_distribution(conn, days)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/events')
def api_events():
    """事件统计"""
    days = request.args.get('days', 30, type=int)
    category = request.args.get('category', '')
    conn = am.get_db()
    try:
        data = am.get_event_stats(conn, days, category)
        return jsonify({'success': True, 'data': data})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/overview')
def api_overview():
    """综合概览（一次返回所有关键数据）"""
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()
    try:
        result = {
            'realtime': am.get_realtime(conn),
            'trend': am.get_trend(conn, days),
            'pages': am.get_page_rank(conn, days, 10),
            'sources': am.get_source_analysis(conn, days),
            'geo': am.get_geo_distribution(conn, days),
            'devices': am.get_device_distribution(conn, days),
            'events': am.get_event_stats(conn, days),
        }
        return jsonify({'success': True, 'data': result})
    finally:
        conn.close()


# ─── 告警 API ──────────────────────────────────────────────────────────────────

@analytics_bp.route('/api/v1/alerts', methods=['GET'])
def api_alerts_list():
    """告警规则列表"""
    enabled_only = request.args.get('enabled', '').lower() == 'true'
    alerts = list_alerts(enabled_only)
    return jsonify({'success': True, 'data': alerts})


@analytics_bp.route('/api/v1/alerts', methods=['POST'])
def api_alerts_create():
    """创建告警规则"""
    data = request.get_json(silent=True) or {}
    required = ['name', 'metric', 'operator', 'threshold']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'{field} required'}), 400

    alert_id = create_alert(
        name=data['name'],
        metric=data['metric'],
        operator=data['operator'],
        threshold=float(data['threshold']),
        time_window=data.get('time_window', '1h'),
        channels=data.get('channels'),
    )
    return jsonify({'success': True, 'alert_id': alert_id})


@analytics_bp.route('/api/v1/alerts/<int:alert_id>', methods=['PUT'])
def api_alerts_update(alert_id):
    """更新告警规则"""
    data = request.get_json(silent=True) or {}
    ok = update_alert(alert_id, **data)
    return jsonify({'success': ok})


@analytics_bp.route('/api/v1/alerts/<int:alert_id>', methods=['DELETE'])
def api_alerts_delete(alert_id):
    """删除告警规则"""
    ok = delete_alert(alert_id)
    return jsonify({'success': ok})


# ─── 隐私配置 API ──────────────────────────────────────────────────────────────

@analytics_bp.route('/api/v1/privacy', methods=['GET'])
def api_privacy_get():
    """获取隐私配置"""
    conn = am.get_db()
    try:
        config = am.get_privacy_config(conn)
        return jsonify({'success': True, 'data': config})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/privacy', methods=['PUT'])
def api_privacy_update():
    """更新隐私配置"""
    data = request.get_json(silent=True) or {}
    conn = am.get_db()
    try:
        for key, value in data.items():
            am.update_privacy_config(conn, key, str(value))
        return jsonify({'success': True})
    finally:
        conn.close()


# ─── GeoIP 设置 API ────────────────────────────────────────────────────────────

@analytics_bp.route('/settings/geoip/status', methods=['GET'])
def api_geoip_status():
    """获取 GeoIP 数据库安装状态 + 已保存的 MaxMind 凭证"""
    status = get_geoip_status()

    # 附加已保存的 MaxMind 凭证（用于前端预填）
    pm = _get_pm()
    if pm:
        cfg = pm.get_config('analytics') or {}
        status['maxmind_account_id'] = cfg.get('maxmind_account_id', '')
        status['maxmind_license_key'] = cfg.get('maxmind_license_key', '')

    return jsonify({'success': True, 'data': status})


@analytics_bp.route('/settings/geoip/download', methods=['POST'])
def api_geoip_download():
    """下载/更新 MaxMind 数据库（GeoLite2 免费版 或 GeoIP2 付费版）"""
    data = request.get_json(silent=True) or {}
    license_key = (data.get('license_key') or '').strip()
    account_id = (data.get('account_id') or '').strip()
    edition = (data.get('edition') or 'GeoLite2-City').strip()
    if not license_key:
        return jsonify({'success': False, 'error': _t('license_key required')}), 400

    result = download_geolite2_auto(license_key, account_id, edition)
    return jsonify(result)


@analytics_bp.route('/settings/geoip/upload', methods=['POST'])
def api_geoip_upload():
    """手动上传 .mmdb 文件"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': _t('No file uploaded')}), 400

    f = request.files['file']
    if not f.filename or not f.filename.endswith('.mmdb'):
        return jsonify({'success': False, 'error': _t('Only .mmdb files allowed')}), 400

    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.mmdb', delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = install_geolite2_file(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return jsonify(result)


@analytics_bp.route('/settings/geoip/download-cdn', methods=['POST'])
def api_geoip_download_cdn():
    """从 jsDelivr CDN 免费镜像下载 GeoLite2（无需 MaxMind 账号）"""
    result = download_geolite2_cdn()
    return jsonify(result)


@analytics_bp.route('/settings/geoip/download-ip2region', methods=['POST'])
def api_geoip_download_ip2region():
    """下载 ip2region 数据库（开源免费，无需注册）"""
    result = download_ip2region_auto()
    return jsonify(result)


# ─── 维护 API ──────────────────────────────────────────────────────────────────

@analytics_bp.route('/api/v1/cleanup', methods=['POST'])
def api_cleanup():
    """手动触发日志清理"""
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()
    try:
        deleted = am.cleanup_old_logs(conn, days)
        return jsonify({'success': True, 'deleted': deleted})
    finally:
        conn.close()


@analytics_bp.route('/api/v1/stats')
def api_self_stats():
    """分析系统自身统计"""
    conn = am.get_db()
    try:
        total_logs = conn.execute(
            "SELECT COUNT(*) c FROM analytics_logs"
        ).fetchone()['c']
        total_events = conn.execute(
            "SELECT COUNT(*) c FROM analytics_events"
        ).fetchone()['c']
        total_sessions = conn.execute(
            "SELECT COUNT(*) c FROM analytics_visitor_sessions"
        ).fetchone()['c']
        oldest_log = conn.execute(
            "SELECT MIN(timestamp) ts FROM analytics_logs"
        ).fetchone()['ts'] or 0

        # 数据库大小 — 兼容 SQLite 和 PostgreSQL
        db_size = 0
        try:
            row = conn.execute(
                "SELECT page_count * page_size AS size FROM pragma_page_count, pragma_page_size"
            ).fetchone()
            db_size = row['size'] if row else 0
        except Exception:
            try:
                row = conn.execute(
                    "SELECT pg_database_size(current_database()) AS size"
                ).fetchone()
                db_size = row['size'] if row else 0
            except Exception:
                db_size = 0

        return jsonify({'success': True, 'data': {
            'total_logs': total_logs,
            'total_events': total_events,
            'total_sessions': total_sessions,
            'oldest_log_date': datetime.fromtimestamp(oldest_log).strftime('%Y-%m-%d %H:%M') if oldest_log else '-',
            'db_size_bytes': db_size,
            'db_size_mb': round(db_size / 1048576, 2),
            'tables': ['analytics_logs', 'analytics_hourly_stats', 'analytics_daily_stats',
                       'analytics_visitor_sessions', 'analytics_events', 'analytics_page_stats',
                       'analytics_source_stats', 'analytics_geo_stats', 'analytics_device_stats',
                       'analytics_alerts', 'analytics_privacy_config'],
        }})
    finally:
        conn.close()


# ─── 导出 API ──────────────────────────────────────────────────────────────────

@analytics_bp.route('/api/v1/export')
def api_export():
    """导出统计数据为 CSV"""
    report_type = request.args.get('type', 'trend')  # trend / pages / sources / geo
    days = request.args.get('days', 30, type=int)
    conn = am.get_db()

    try:
        if report_type == 'trend':
            data = am.get_trend(conn, days)
            csv = "date,pv,uv,sessions,bounce_rate,avg_duration\n"
            for r in data:
                csv += f"{r['date']},{r['pv']},{r['uv']},{r['sessions']},{r['bounce_rate']},{r['avg_duration']}\n"

        elif report_type == 'pages':
            data = am.get_page_rank(conn, days, 100)
            csv = "path,pv,uv,avg_response_time_ms\n"
            for r in data:
                csv += f"{r['path']},{r['pv']},{r['uv']},{r['avg_time']}\n"

        elif report_type == 'sources':
            data = am.get_source_analysis(conn, days)
            csv = "source_type,source_name,pv,uv,percentage\n"
            for r in data:
                csv += f"{r['source_type']},{r['source_name']},{r['pv']},{r['uv']},{r.get('pct', 0)}\n"

        elif report_type == 'geo':
            data = am.get_geo_distribution(conn, days)
            csv = "country,pv,uv\n"
            for r in data:
                csv += f"{r['country']},{r['pv']},{r['uv']}\n"

        else:
            return jsonify({'success': False, 'error': f'{_t("unknown type")}: {report_type}'}), 400

        filename = f'analytics_{report_type}_{datetime.now().strftime("%Y%m%d")}.csv'
        return Response(
            csv,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    finally:
        conn.close()


# ─── 报告 API（供 Workflow 集成） ──────────────────────────────────────────────

@analytics_bp.route('/api/v1/report')
def api_report():
    """生成分析报告（JSON 格式）"""
    days = request.args.get('days', 7, type=int)
    report = generate_report(days)
    return jsonify({'success': True, 'data': report})


@analytics_bp.route('/api/v1/report/text')
def api_report_text():
    """生成可读文字报告"""
    days = request.args.get('days', 7, type=int)
    report = generate_report(days)
    text = generate_insight_text(report)
    return Response(text, mimetype='text/plain; charset=utf-8')


# ─── PluginManager 标准化配置 ─────────────────────────────────────────

_ANALYTICS_CONFIG_KEYS = ['sample_rate', 'geoip_enabled', 'service_name', 'maxmind_account_id', 'maxmind_license_key']

_ANALYTICS_CONFIG_DEFAULTS = {
    'sample_rate': 1.0,
    'geoip_enabled': True,
    'service_name': 'admin',
    'maxmind_account_id': '',
    'maxmind_license_key': '',
}


def _get_pm():
    """获取 PluginManager 实例"""
    pm = getattr(request, 'plugin_manager', None)
    if pm is None:
        pm = getattr(g, 'plugin_manager', None)
    if pm is None:
        pm = current_app.extensions.get('plugin_manager')
    return pm


@analytics_bp.route('/settings', methods=['GET'])
def analytics_settings_get():
    """获取插件配置（PluginManager 标准化）"""
    from flask import current_app, g
    pm = _get_pm()
    if not pm:
        return jsonify({'success': False, 'error': 'PluginManager not available'}), 503
    cfg = pm.get_config('analytics') or {}
    result = {}
    for k in _ANALYTICS_CONFIG_KEYS:
        v = cfg.get(k)
        if v is not None:
            result[k] = v
        else:
            result[k] = _ANALYTICS_CONFIG_DEFAULTS.get(k)
    return jsonify({'success': True, 'data': result})


@analytics_bp.route('/settings', methods=['POST'])
def analytics_settings_save():
    """保存插件配置（PluginManager 标准化）"""
    from flask import current_app, g
    data = request.get_json(force=True) or {}
    pm = _get_pm()
    if not pm:
        return jsonify({'success': False, 'error': 'PluginManager not available'}), 503
    filtered = {k: v for k, v in data.items() if k in _ANALYTICS_CONFIG_KEYS}
    if not filtered:
        return jsonify({'success': False, 'error': 'No valid config keys provided'}), 400
    # 类型转换
    for k in filtered:
        if k == 'sample_rate':
            try:
                filtered[k] = float(filtered[k])
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': f'{k} must be a number'}), 400
        elif k == 'geoip_enabled':
            if isinstance(filtered[k], str):
                filtered[k] = filtered[k].lower() in ('1', 'true', 'yes')
            else:
                filtered[k] = bool(filtered[k])
        else:
            filtered[k] = str(filtered[k])
    result = pm.set_config_batch('analytics', filtered, coerce=True)
    if result.get('errors'):
        return jsonify({'success': True, 'warning': str(result['errors'])})
    return jsonify({'success': True})
