#!/usr/bin/env python3
"""Ad Management Plugin — 广告管理 API 路由"""
import sys, os

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


# ── GET /admin/ads ──
@ads_bp.route('', methods=['GET'])
def list_ads():
    admin, err = _require_admin()
    if err:
        return err
    from plugins.ads.models import get_ads_db
    conn = get_ads_db()
    rows = conn.execute(
        'SELECT * FROM ad_placements ORDER BY sort_order, id'
    ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


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
        (name, position, page, ad_type, image_url, link_url, ad_code, width, height, is_active, sort_order)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (name,
         data.get('position', 'sidebar'),
         data.get('page', '*'),
         data.get('ad_type', 'image'),
         data.get('image_url', ''),
         data.get('link_url', ''),
         data.get('ad_code', ''),
         data.get('width', 320),
         data.get('height', 0),
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
        name=?, position=?, page=?, ad_type=?, image_url=?, link_url=?,
        ad_code=?, width=?, height=?, is_active=?, sort_order=?,
        updated_at=datetime('now')
        WHERE id=?''',
        (data.get('name', ''),
         data.get('position', 'sidebar'),
         data.get('page', '*'),
         data.get('ad_type', 'image'),
         data.get('image_url', ''),
         data.get('link_url', ''),
         data.get('ad_code', ''),
         data.get('width', 320),
         data.get('height', 0),
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