#!/usr/bin/env python3
"""Ad Management Plugin — 广告管理 API 路由 (v0.2.0)"""
import sys, os, json
from datetime import datetime

_auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
if _auth_dir not in sys.path:
    sys.path.insert(0, _auth_dir)

from flask import Blueprint, request, jsonify

ads_bp = Blueprint('ads', __name__, url_prefix='/admin/ads')


def _require_admin():
    """复用主系统的管理员鉴权"""
    from routes.admin import _require_admin as _ra
    return _ra()


def _log(admin_id, action, target_type='', target_id='', detail=''):
    """复用主系统的操作日志"""
    from routes.admin import _log as _l
    _l(admin_id, action, target_type, target_id, detail)


# ============================================================
# 通用辅助
# ============================================================

def _now_str():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')


def _parse_targeting(data):
    """解析并校验定向规则 JSON"""
    rules = data.get('targeting_rules') or data.get('targeting') or {}
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except (json.JSONDecodeError, TypeError):
            rules = {}
    if not isinstance(rules, dict):
        rules = {}
    return rules


def _ad_row_to_dict(row):
    r = dict(row)
    try:
        r['targeting_rules'] = json.loads(r.get('targeting_rules') or '{}')
    except (json.JSONDecodeError, TypeError):
        r['targeting_rules'] = {}
    return r


# ============================================================
# 广告位 CRUD
# ============================================================

# ── GET /admin/ads ──
@ads_bp.route('/', methods=['GET'])
def list_ads():
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    site_key = request.args.get('site_key', '').strip() or None
    zone_id = request.args.get('zone_id', type=int)

    from plugins.ads.models import get_ads_db
    conn = get_ads_db()

    where = []
    params = []
    if site_key:
        where.append('site_key=?')
        params.append(site_key)
    if zone_id is not None:
        where.append('zone_id=?')
        params.append(zone_id)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ''
    total = conn.execute(f'SELECT COUNT(*) FROM ad_placements {where_sql}', params).fetchone()[0]
    rows = conn.execute(
        f'SELECT * FROM ad_placements {where_sql} ORDER BY sort_order, id LIMIT ? OFFSET ?',
        params + [limit, offset]
    ).fetchall()
    return jsonify({
        'success': True,
        'data': [_ad_row_to_dict(r) for r in rows],
        'total': total, 'page': page, 'limit': limit
    })


# ── POST /admin/ads ──
@ads_bp.route('', methods=['POST'])
def create_ad():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': '广告名称不能为空'}), 400

    from plugins.ads.models import get_ads_db
    conn = get_ads_db()
    cur = conn.execute('''INSERT INTO ad_placements
        (name, site_key, zone_id, position, page, ad_type, image_url, link_url, ad_code,
         width, height, targeting_rules, schedule_start, schedule_end, weight, freq_cap,
         click_tag, utm_source, is_active, sort_order)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (name,
         data.get('site_key', 'default'),
         data.get('zone_id', 0),
         data.get('position', 'sidebar'),
         data.get('page', '*'),
         data.get('ad_type', 'image'),
         data.get('image_url', ''),
         data.get('link_url', ''),
         data.get('ad_code', ''),
         data.get('width', 320),
         data.get('height', 0),
         json.dumps(_parse_targeting(data), ensure_ascii=False),
         data.get('schedule_start', ''),
         data.get('schedule_end', ''),
         data.get('weight', 1),
         data.get('freq_cap', 0),
         data.get('click_tag', ''),
         data.get('utm_source', ''),
         data.get('is_active', 1),
         data.get('sort_order', 0)))
    conn.commit()
    ad_id = cur.lastrowid
    _log(admin['user_id'], 'create_ad', detail=f'id={ad_id} name={name}')
    return jsonify({'success': True, 'data': {'id': ad_id}})


# ── PUT /admin/ads/<id> ──
@ads_bp.route('/<int:ad_id>', methods=['PUT'])
def update_ad(ad_id):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    from plugins.ads.models import get_ads_db
    conn = get_ads_db()
    existing = conn.execute('SELECT id FROM ad_placements WHERE id=?', (ad_id,)).fetchone()
    if not existing:
        return jsonify({'success': False, 'error': '广告不存在'}), 404
    conn.execute('''UPDATE ad_placements SET
        name=?, site_key=?, zone_id=?, position=?, page=?, ad_type=?, image_url=?,
        link_url=?, ad_code=?, width=?, height=?, targeting_rules=?, schedule_start=?,
        schedule_end=?, weight=?, freq_cap=?, click_tag=?, utm_source=?, is_active=?,
        sort_order=?, updated_at=datetime('now')
        WHERE id=?''',
        (data.get('name', ''),
         data.get('site_key', 'default'),
         data.get('zone_id', 0),
         data.get('position', 'sidebar'),
         data.get('page', '*'),
         data.get('ad_type', 'image'),
         data.get('image_url', ''),
         data.get('link_url', ''),
         data.get('ad_code', ''),
         data.get('width', 320),
         data.get('height', 0),
         json.dumps(_parse_targeting(data), ensure_ascii=False),
         data.get('schedule_start', ''),
         data.get('schedule_end', ''),
         data.get('weight', 1),
         data.get('freq_cap', 0),
         data.get('click_tag', ''),
         data.get('utm_source', ''),
         data.get('is_active', 1),
         data.get('sort_order', 0),
         ad_id))
    conn.commit()
    _log(admin['user_id'], 'update_ad', detail=f'id={ad_id}')
    return jsonify({'success': True})


# ── DELETE /admin/ads/<id> ──
@ads_bp.route('/<int:ad_id>', methods=['DELETE'])
def delete_ad(ad_id):
    admin, err = _require_admin()
    if err:
        return err
    from plugins.ads.models import get_ads_db
    conn = get_ads_db()
    conn.execute('DELETE FROM ad_placements WHERE id=?', (ad_id,))
    conn.commit()
    _log(admin['user_id'], 'delete_ad', detail=f'id={ad_id}')
    return jsonify({'success': True})


# ============================================================
# 广告位区域（Zone）管理
# ============================================================

@ads_bp.route('/zones', methods=['GET'])
def list_zones():
    admin, err = _require_admin()
    if err:
        return err
    site_key = request.args.get('site_key', '').strip() or 'default'
    active_only = request.args.get('active_only', '').lower() == 'true'
    from plugins.ads.models import list_zones as _list_zones
    return jsonify({'success': True, 'data': _list_zones(site_key=site_key, active_only=active_only)})


@ads_bp.route('/zones', methods=['POST'])
def create_zone():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    identifier = data.get('identifier', '').strip()
    if not name or not identifier:
        return jsonify({'success': False, 'error': '区域名称和标识不能为空'}), 400
    from plugins.ads.models import create_zone as _create_zone
    try:
        zone_id = _create_zone(data)
    except Exception as e:
        return jsonify({'success': False, 'error': f'创建失败: {e}'}), 400
    _log(admin['user_id'], 'create_ad_zone', detail=f'id={zone_id} name={name}')
    return jsonify({'success': True, 'data': {'id': zone_id}})


@ads_bp.route('/zones/<int:zone_id>', methods=['PUT'])
def update_zone(zone_id):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    from plugins.ads.models import update_zone as _update_zone, get_zone
    if not get_zone(zone_id):
        return jsonify({'success': False, 'error': '区域不存在'}), 404
    _update_zone(zone_id, data)
    _log(admin['user_id'], 'update_ad_zone', detail=f'id={zone_id}')
    return jsonify({'success': True})


@ads_bp.route('/zones/<int:zone_id>', methods=['DELETE'])
def delete_zone(zone_id):
    admin, err = _require_admin()
    if err:
        return err
    from plugins.ads.models import delete_zone as _delete_zone, get_zone
    if not get_zone(zone_id):
        return jsonify({'success': False, 'error': '区域不存在'}), 404
    _delete_zone(zone_id)
    _log(admin['user_id'], 'delete_ad_zone', detail=f'id={zone_id}')
    return jsonify({'success': True})


# ============================================================
# 统计上报与查询
# ============================================================

@ads_bp.route('/api/v1/stats/impression', methods=['POST'])
def api_record_impression():
    """公开端点：上报展示"""
    data = request.get_json() or {}
    ad_id = data.get('ad_id')
    if not ad_id:
        return jsonify({'success': False, 'error': 'ad_id 必填'}), 400
    try:
        from plugins.ads.models import record_impression
        record_impression(ad_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ads_bp.route('/api/v1/stats/click', methods=['POST'])
def api_record_click():
    """公开端点：上报点击"""
    data = request.get_json() or {}
    ad_id = data.get('ad_id')
    if not ad_id:
        return jsonify({'success': False, 'error': 'ad_id 必填'}), 400
    try:
        from plugins.ads.models import record_click
        record_click(
            ad_id,
            page=data.get('page', ''),
            position=data.get('position', ''),
            ip=request.remote_addr or '',
            user_agent=request.headers.get('User-Agent', ''),
            referrer=request.headers.get('Referer', '')
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ads_bp.route('/api/v1/stats', methods=['GET'])
def api_get_stats():
    """管理端点：查询统计（需管理员权限）"""
    admin, err = _require_admin()
    if err:
        return err
    ad_id = request.args.get('ad_id', type=int)
    site_key = request.args.get('site_key', '').strip() or None
    days = request.args.get('days', 7, type=int)
    days = max(1, min(days, 90))
    from plugins.ads.models import get_ad_stats
    return jsonify({'success': True, 'data': get_ad_stats(ad_id=ad_id, site_key=site_key, days=days)})


# ============================================================
# 站点解析辅助
# ============================================================

def _resolve_site_key_from_host():
    """根据请求 Host 从 site_domains 表解析当前子域名作为 site_key"""
    host = request.headers.get('Host', '').split(':')[0].lower()
    if not host or host.startswith('127.') or host == 'localhost':
        return 'default'
    try:
        from models import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT subdomain FROM site_domains WHERE full_domain=? AND is_published=1",
                (host,)
            ).fetchone()
            if row and row['subdomain']:
                return row['subdomain']
    except Exception:
        pass
    return 'default'


# ============================================================
# 公开广告渲染 API
# ============================================================

@ads_bp.route('/api/v1/ads', methods=['GET'])
def public_ads():
    """公开端点 — 前端页面调用以渲染广告
    GET /admin/ads/api/v1/ads?page=*&position=sidebar&site_key=default&zone_id=0
    返回当前页、位置、站点下所有活跃且符合投放条件的广告
    """
    page = request.args.get('page', '*', type=str).strip()
    position = request.args.get('position', '', type=str).strip()
    site_key = request.args.get('site_key', '').strip() or _resolve_site_key_from_host()
    zone_id = request.args.get('zone_id', type=int)

    from plugins.ads.models import get_ads_db
    conn = get_ads_db()
    where = ['is_active=1']
    params = []

    if position:
        where.append('position=?')
        params.append(position)
    if site_key:
        where.append('site_key=?')
        params.append(site_key)
    if zone_id is not None:
        where.append('zone_id=?')
        params.append(zone_id)

    # 页面匹配：精确页面或通配 *
    where.append('(page=? OR page=?)')
    params.extend([page, '*'])

    # 时间过滤：当前时间需在 schedule_start 与 schedule_end 之间（若设置）
    now = _now_str()
    where.append("(schedule_start='' OR schedule_start<=?)")
    params.append(now)
    where.append("(schedule_end='' OR schedule_end>=?)")
    params.append(now)

    rows = conn.execute(
        f'SELECT * FROM ad_placements WHERE {" AND ".join(where)} ORDER BY sort_order, id',
        params
    ).fetchall()

    return jsonify({
        'success': True,
        'data': [_ad_row_to_dict(r) for r in rows]
    })
