#!/usr/bin/env python3
"""
Currency Converter Plugin Routes — 币种管理 API + 前台换算接口
===============================================================
"""
import os
import sys

_auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
if _auth_dir not in sys.path:
    sys.path.insert(0, _auth_dir)

from flask import Blueprint, request, jsonify, render_template

currency_bp = Blueprint('currency', __name__, url_prefix='/admin/currency',
                        template_folder='templates',
                        static_folder='static')


def _require_admin():
    """复用主系统的管理员鉴权"""
    from routes.admin import _require_admin as _ra
    return _ra()


def _log(admin_id, action, target_type='', target_id='', detail=''):
    """复用主系统的操作日志"""
    from routes.admin import _log as _l
    _l(admin_id, action, target_type, target_id, detail)


# ── 管理页面 ──────────────────────────────────────

@currency_bp.route('/', methods=['GET'])
def admin_page():
    admin, err = _require_admin()
    if err:
        return err
    return render_template('admin_currency.html')


# ── 公有 API（无需管理员登录） ──────────────────────────


@currency_bp.route('/rates', methods=['GET'])
def public_get_rates():
    """获取所有汇率映射（前端价格换算使用）"""
    from .services import get_all_rates, get_enabled_currencies
    try:
        rates = get_all_rates()
        currencies = get_enabled_currencies()
        return jsonify({
            'success': True,
            'data': {
                'base_currency': 'CNY',
                'rates': rates,
                'currencies': currencies,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@currency_bp.route('/convert', methods=['POST'])
def public_convert():
    """换算金额（前端防抖调用）"""
    from .services import convert, format_amount
    data = request.get_json(force=True) or {}
    amount = data.get('amount', 0)
    from_currency = data.get('from', 'CNY')
    to_currency = data.get('to', 'CNY')
    try:
        converted, rate = convert(float(amount), from_currency, to_currency)
        return jsonify({
            'success': True,
            'data': {
                'original': float(amount),
                'from': from_currency.upper(),
                'to': to_currency.upper(),
                'converted': round(converted, 2),
                'rate': round(rate, 6),
                'formatted': format_amount(converted, to_currency),
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── 用户偏好 ────────────────────────────────────────────


@currency_bp.route('/preference', methods=['GET'])
def get_preference():
    """获取当前用户币种偏好"""
    from flask import g
    user_id = getattr(g, 'user_id', None)
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    from .services import get_user_preferred_currency
    currency = get_user_preferred_currency(user_id)
    return jsonify({'success': True, 'data': {'currency': currency}})


@currency_bp.route('/preference', methods=['POST'])
def set_preference():
    """设置当前用户币种偏好"""
    from flask import g
    user_id = getattr(g, 'user_id', None)
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json(force=True) or {}
    currency = data.get('currency', '').strip().upper()
    if not currency:
        return jsonify({'success': False, 'error': 'Currency required'}), 400
    from .services import set_user_preferred_currency
    ok = set_user_preferred_currency(user_id, currency)
    if not ok:
        return jsonify({'success': False, 'error': 'Failed to save preference'}), 500
    return jsonify({'success': True, 'data': {'currency': currency}})


# ── GeoIP 自动检测 ──────────────────────────────────────


@currency_bp.route('/geoip', methods=['GET'])
def geoip_detect():
    """根据访客 IP 自动检测推荐币种（无需登录）"""
    from .services import detect_currency_by_ip
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    # X-Forwarded-For 可能是 "client, proxy1, proxy2"
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    result = detect_currency_by_ip(ip)
    return jsonify({'success': True, 'data': result})


# ── 管理 API（需管理员） ────────────────────────────────


@currency_bp.route('/manage/sync', methods=['POST'])
def admin_sync_rates():
    """管理员手动触发汇率同步"""
    admin, err = _require_admin()
    if err:
        return err
    from .services import sync_rates
    import asyncio
    try:
        count = asyncio.run(sync_rates())
        _log(admin['user_id'], 'sync_rates', 'currency', '', f'Synced {count} rates')
        return jsonify({'success': True, 'data': {'count': count}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@currency_bp.route('/manage/stats', methods=['GET'])
def admin_rate_stats():
    """管理员查看汇率统计"""
    admin, err = _require_admin()
    if err:
        return err
    from .models import get_db
    try:
        conn = get_db()
        count = conn.execute('SELECT COUNT(*) FROM exchange_rates').fetchone()['count']
        latest = conn.execute(
            'SELECT currency_code, rate_to_base, fetched_at FROM exchange_rates ORDER BY fetched_at DESC LIMIT 10'
        ).fetchall()
        return jsonify({
            'success': True,
            'data': {
                'total_rates': count,
                'latest_rates': [dict(r) for r in latest],
                'memory_cache_size': 0,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@currency_bp.route('/manage/config', methods=['GET'])
def admin_get_config():
    """获取当前配置"""
    admin, err = _require_admin()
    if err:
        return err
    from .services import _BASE_CURRENCY, _CACHE_TTL
    return jsonify({
        'success': True,
        'data': {
            'base_currency': _BASE_CURRENCY,
            'cache_ttl_seconds': _CACHE_TTL,
        }
    })


# ─── PluginManager 标准化配置 ─────────────────────────────────────────

_CC_CONFIG_KEYS = [
    'primary_api', 'fallback_api', 'base_currency', 'refresh_interval_minutes',
    'cache_ttl_minutes', 'default_currency', 'enable_geoip', 'enabled_currencies',
]

_CC_DEFAULTS = {
    'primary_api': 'https://api.frankfurter.app/latest',
    'fallback_api': 'https://open.er-api.com/v6/latest',
    'base_currency': 'CNY',
    'refresh_interval_minutes': 60,
    'cache_ttl_minutes': 60,
    'default_currency': 'CNY',
    'enable_geoip': True,
    'enabled_currencies': 'CNY,USD,EUR,JPY,GBP,HKD,KRW,AUD,CAD,SGD,THB,MYR,PHP,IDR,VND',
}


def _get_cc_pm():
    import flask
    try:
        return flask.current_app.extensions.get('plugin_manager')
    except Exception:
        return None


@currency_bp.route('/settings', methods=['GET'])
def cc_settings_get():
    admin, err = _require_admin()
    if err:
        return err
    pm = _get_cc_pm()
    if not pm:
        return jsonify({'success': False, 'error': 'PluginManager not available'}), 503
    cfg = pm.get_config('currency_converter') or {}
    result = {}
    for k in _CC_CONFIG_KEYS:
        v = cfg.get(k)
        if v is not None:
            result[k] = v
        else:
            result[k] = _CC_DEFAULTS.get(k)
    return jsonify({'success': True, 'data': result})


@currency_bp.route('/settings', methods=['POST'])
def cc_settings_save():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    pm = _get_cc_pm()
    if not pm:
        return jsonify({'success': False, 'error': 'PluginManager not available'}), 503
    filtered = {}
    for k in _CC_CONFIG_KEYS:
        if k in data:
            v = data[k]
            if k in ('refresh_interval_minutes', 'cache_ttl_minutes'):
                try:
                    filtered[k] = int(v)
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': f'{k} must be integer'}), 400
            elif k == 'enable_geoip':
                if isinstance(v, str):
                    filtered[k] = v.lower() in ('1', 'true', 'yes')
                else:
                    filtered[k] = bool(v)
            else:
                filtered[k] = str(v) if v is not None else ''
    if not filtered:
        return jsonify({'success': False, 'error': 'No valid config keys'}), 400
    result = pm.set_config_batch('currency_converter', filtered, coerce=True)
    if result.get('errors'):
        return jsonify({'success': True, 'warning': str(result['errors'])})
    return jsonify({'success': True})
