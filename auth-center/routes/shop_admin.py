#!/usr/bin/env python3
"""Shop Admin — 商城管理 (商品CRUD + 多图上传 + SKU/规格 + 分类 + 订单 + 优惠券)"""
import sys, os, json, time, secrets
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from flask import Blueprint, jsonify, request
from models import get_db
from datetime import datetime
from werkzeug.utils import secure_filename

shop_bp = Blueprint('shop', __name__, url_prefix='/shop')

# ── 输入长度限制 ──
_MAX_TITLE = 200
_MAX_SUBTITLE = 500
_MAX_CATEGORY = 100
_MAX_THUMBNAIL = 500
_MAX_DESC = 50000
_MAX_FEATURES_JSON = 50000
_MAX_AI_CONFIG_JSON = 50000

# ── 图片上传配置 ──
_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'platform', 'static', 'products')
_ALLOWED_EXTS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
os.makedirs(_UPLOAD_DIR, exist_ok=True)


def _require_admin():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        return None, (jsonify({'success': False, 'error': _('Please log in first')}), 401)
    from services.jwt_service import validate_token
    payload = validate_token(token)
    if not payload:
        return None, (jsonify({'success': False, 'error': '无效Token'}), 401)
    if not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': '需要管理员权限'}), 403)
    return payload, None


def _require_user():
    """验证用户登录（不要求管理员）"""
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    if not token:
        return None, (jsonify({'success': False, 'error': _('Please log in first')}), 401)
    from services.jwt_service import validate_token
    payload = validate_token(token)
    if not payload:
        return None, (jsonify({'success': False, 'error': '无效Token'}), 401)
    return payload, None


def _log_admin_action(conn, admin_id, action, target_type, target_id, detail=''):
    try:
        conn.execute(
            'INSERT INTO admin_logs (admin_id, action, target_type, target_id, detail) VALUES (?,?,?,?,?)',
            (admin_id, action, target_type, str(target_id), detail[:500])
        )
    except Exception:
        pass


def _safe_json(val, default=None):
    """安全解析JSON字段"""
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str) and val:
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return default if default is not None else ([] if isinstance(default, list) else {})


def _product_to_dict(row):
    """将 products 行转为dict并解析JSON字段"""
    p = dict(row)
    p['features'] = _safe_json(p.get('features'), [])
    p['ai_config'] = _safe_json(p.get('ai_config'), {})
    p['images'] = _safe_json(p.get('images'), [])
    return p


# =============================================
# 图片上传
# =============================================
@shop_bp.route('/products/upload-image', methods=['POST'])
def upload_image():
    """上传商品图片，返回URL"""
    payload, err = _require_admin()
    if err:
        return err

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未选择文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': '文件名为空'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in _ALLOWED_EXTS:
        return jsonify({'success': False, 'error': f'不支持的文件格式: {ext}，支持{_ALLOWED_EXTS}'}), 400

    # 限流：每秒最多上传2张
    _rl_key = f'upload_img_{payload["user_id"]}'
    _rl = getattr(request, '_rate_limit_cache', {})
    now_t = time.time()
    last = _rl.get(_rl_key, 0)
    if now_t - last < 0.5:
        return jsonify({'success': False, 'error': '操作太快，请稍候'}), 429
    _rl[_rl_key] = now_t
    request._rate_limit_cache = _rl

    # 生成唯一文件名
    ts = str(int(time.time() * 1000))
    rand = secrets.token_hex(4)
    filename = f'{ts}_{rand}.{ext}'
    filepath = os.path.join(_UPLOAD_DIR, filename)
    file.save(filepath)

    url = f'/pimg/{filename}'
    return jsonify({'success': True, 'data': {'url': url, 'filename': filename}})


@shop_bp.route('/products/<int:pid>/images', methods=['GET'])
def get_product_images(pid):
    """获取商品图片列表"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('SELECT images FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        images = _safe_json(row['images'], [])
    return jsonify({'success': True, 'data': {'images': images}})


@shop_bp.route('/products/<int:pid>/images', methods=['POST'])
def add_product_image(pid):
    """为商品添加图片"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': '请提供图片URL'}), 400

    with get_db() as conn:
        row = conn.execute('SELECT images FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        images = _safe_json(row['images'], [])
        images.append({'url': url, 'sort_order': len(images)})
        conn.execute('UPDATE products SET images=?, updated_at=datetime(\'now\',\'localtime\') WHERE id=?',
                     (json.dumps(images, ensure_ascii=False), pid))
        conn.commit()
    return jsonify({'success': True, 'data': {'images': images}})


@shop_bp.route('/products/<int:pid>/images/<int:idx>', methods=['DELETE'])
def delete_product_image(pid, idx):
    """删除商品指定图片"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('SELECT images FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        images = _safe_json(row['images'], [])
        if idx < 0 or idx >= len(images):
            return jsonify({'success': False, 'error': '图片索引无效'}), 400

        removed = images.pop(idx)
        # 如果是本地图片，删除物理文件
        url = removed.get('url', '') if isinstance(removed, dict) else str(removed)
        if url.startswith('/pimg/'):
            fpath = os.path.join(_UPLOAD_DIR, os.path.basename(url))
            if os.path.exists(fpath):
                os.remove(fpath)

        conn.execute('UPDATE products SET images=?, updated_at=datetime(\'now\',\'localtime\') WHERE id=?',
                     (json.dumps(images, ensure_ascii=False), pid))
        conn.commit()
    return jsonify({'success': True, 'data': {'images': images}})


@shop_bp.route('/products/<int:pid>/images/reorder', methods=['POST'])
def reorder_product_images(pid):
    """重新排序商品图片"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    order = data.get('order', [])  # [2, 0, 1, 3] 新顺序索引
    if not order:
        return jsonify({'success': False, 'error': '请提供顺序'}), 400

    with get_db() as conn:
        row = conn.execute('SELECT images FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        images = _safe_json(row['images'], [])
        if len(order) != len(images):
            return jsonify({'success': False, 'error': '顺序索引数量不匹配'}), 400
        try:
            reordered = [images[i] for i in order]
        except IndexError:
            return jsonify({'success': False, 'error': '索引超出范围'}), 400
        conn.execute('UPDATE products SET images=?, updated_at=datetime(\'now\',\'localtime\') WHERE id=?',
                     (json.dumps(reordered, ensure_ascii=False), pid))
        conn.commit()
    return jsonify({'success': True, 'data': {'images': reordered}})


# =============================================
# 商品列表 / CRUD（增强版）
# =============================================
@shop_bp.route('/products', methods=['GET'])
def list_products():
    """商品列表，支持搜索/分类/状态筛选"""
    payload, err = _require_admin()
    if err:
        return err
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int, default=0)
    is_active = request.args.get('is_active', type=int, default=-1)
    with get_db() as conn:
        sql = 'SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE 1=1'
        params = []
        if search:
            sql += ' AND (p.title LIKE ? OR p.subtitle LIKE ?)'
            s = f'%{search}%'
            params.extend([s, s])
        if category_id > 0:
            sql += ' AND p.category_id=?'
            params.append(category_id)
        if is_active >= 0:
            sql += ' AND p.is_active=?'
            params.append(is_active)
        sql += ' ORDER BY p.sort_order ASC, p.id DESC'
        rows = conn.execute(sql, params).fetchall()
    return jsonify({'success': True, 'data': [_product_to_dict(r) for r in rows]})


@shop_bp.route('/products/<int:pid>', methods=['GET'])
def get_product(pid):
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute(
            'SELECT p.*, c.name as category_name FROM products p '
            'LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=?', (pid,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
    return jsonify({'success': True, 'data': _product_to_dict(row)})


@shop_bp.route('/products/<int:pid>/preview', methods=['GET'])
def admin_preview_product(pid):
    """预览商品 — 绕过 is_active 检查"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute(
            'SELECT p.*, c.name as category_name FROM products p '
            'LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=?', (pid,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
    return jsonify({'success': True, 'data': _product_to_dict(row)})


@shop_bp.route('/products', methods=['POST'])
def create_product():
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    required = ['title', 'price']
    for f in required:
        if f not in data:
            return jsonify({'success': False, 'error': f'缺少必填字段: {f}'}), 400

    if len(str(data.get('title', ''))) > _MAX_TITLE:
        return jsonify({'success': False, 'error': f'标题不能超过{_MAX_TITLE}字'}), 400
    if len(str(data.get('description', ''))) > _MAX_DESC:
        return jsonify({'success': False, 'error': f'描述不能超过{_MAX_DESC}字'}), 400

    images = data.get('images', [])
    if isinstance(images, str):
        try:
            images = json.loads(images)
        except:
            images = []

    with get_db() as conn:
        c = conn.execute(
            '''INSERT INTO products (title, subtitle, product_type, category,
               category_id, price, original_price, stock, thumbnail, description,
               features, images, ai_config, sort_order, is_active)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                data.get('title', ''),
                data.get('subtitle', ''),
                data.get('product_type', 'service'),
                data.get('category', ''),
                int(data.get('category_id', 0)),
                float(data.get('price', 0)),
                float(data.get('original_price', 0)),
                int(data.get('stock', 0)),
                data.get('thumbnail', ''),
                data.get('description', ''),
                json.dumps(data.get('features', []), ensure_ascii=False),
                json.dumps(images, ensure_ascii=False),
                json.dumps(data.get('ai_config', {}), ensure_ascii=False),
                int(data.get('sort_order', 0)),
                1
            )
        )
        pid = c.lastrowid
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'create', 'product', pid, data.get('title', ''))
    return jsonify({'success': True, 'data': {'id': pid}, 'message': '商品已创建'})


@shop_bp.route('/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    if not data:
        return jsonify({'success': False, 'error': '无更新数据'}), 400

    fields = ['title', 'subtitle', 'product_type', 'category',
              'category_id', 'price', 'original_price', 'stock', 'thumbnail',
              'description', 'sort_order', 'is_active']
    sets = []
    vals = []
    for f in fields:
        if f in data:
            sets.append(f'{f}=?')
            vals.append(data[f])
    if 'features' in data:
        sets.append('features=?')
        vals.append(json.dumps(data['features'], ensure_ascii=False))
    if 'images' in data:
        imgs = data['images']
        if isinstance(imgs, str):
            try:
                imgs = json.loads(imgs)
            except:
                imgs = []
        sets.append('images=?')
        vals.append(json.dumps(imgs, ensure_ascii=False))
    if 'ai_config' in data:
        sets.append('ai_config=?')
        vals.append(json.dumps(data['ai_config'], ensure_ascii=False))
    if not sets:
        return jsonify({'success': False, 'error': '无有效更新字段'}), 400

    sets.append("updated_at=datetime('now','localtime')")
    vals.append(pid)
    with get_db() as conn:
        conn.execute(f'UPDATE products SET {",".join(sets)} WHERE id=?', vals)
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'update', 'product', pid,
                          json.dumps({k: data[k] for k in data if k in fields}, ensure_ascii=False))
    return jsonify({'success': True, 'message': '商品已更新'})


@shop_bp.route('/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('SELECT images FROM products WHERE id=?', (pid,)).fetchone()
        if row:
            images = _safe_json(row['images'], [])
            for img in images:
                url = img.get('url', '') if isinstance(img, dict) else str(img)
                if url.startswith('/static/products/'):
                    fpath = os.path.join(_UPLOAD_DIR, os.path.basename(url))
                    if os.path.exists(fpath):
                        os.remove(fpath)
        # 清理关联数据
        conn.execute('DELETE FROM product_specs WHERE product_id=?', (pid,))
        conn.execute('DELETE FROM product_spec_values WHERE spec_id IN (SELECT id FROM product_specs WHERE product_id=?)', (pid,))
        conn.execute('DELETE FROM product_skus WHERE product_id=?', (pid,))
        conn.execute('DELETE FROM products WHERE id=?', (pid,))
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'delete', 'product', pid)
    return jsonify({'success': True, 'message': '商品已删除'})


# =============================================
# 商品规格管理 (Specs)
# =============================================
@shop_bp.route('/products/<int:pid>/specs', methods=['GET'])
def list_specs(pid):
    """获取商品规格列表（含规格值）"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        specs = conn.execute(
            'SELECT * FROM product_specs WHERE product_id=? ORDER BY sort_order ASC', (pid,)
        ).fetchall()
        result = []
        for s in specs:
            sd = dict(s)
            vals = conn.execute(
                'SELECT * FROM product_spec_values WHERE spec_id=? ORDER BY sort_order ASC', (s['id'],)
            ).fetchall()
            sd['values'] = [dict(v) for v in vals]
            result.append(sd)
    return jsonify({'success': True, 'data': result})


@shop_bp.route('/products/<int:pid>/specs', methods=['POST'])
def create_spec(pid):
    """添加规格名"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    name = data.get('spec_name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': '规格名不能为空'}), 400
    with get_db() as conn:
        conn.execute(
            'INSERT INTO product_specs (product_id, spec_name, sort_order) VALUES (?,?,?)',
            (pid, name, int(data.get('sort_order', 0)))
        )
        sid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
    return jsonify({'success': True, 'data': {'id': sid}, 'message': '规格已添加'})


@shop_bp.route('/products/<int:pid>/specs/<int:sid>', methods=['PUT'])
def update_spec(pid, sid):
    """修改规格名"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    name = data.get('spec_name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': '规格名不能为空'}), 400
    with get_db() as conn:
        conn.execute('UPDATE product_specs SET spec_name=?, sort_order=? WHERE id=? AND product_id=?',
                     (name, int(data.get('sort_order', 0)), sid, pid))
        conn.commit()
    return jsonify({'success': True, 'message': '规格已更新'})


@shop_bp.route('/products/<int:pid>/specs/<int:sid>', methods=['DELETE'])
def delete_spec(pid, sid):
    """删除规格及所有规格值"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('DELETE FROM product_spec_values WHERE spec_id=?', (sid,))
        conn.execute('DELETE FROM product_specs WHERE id=? AND product_id=?', (sid, pid))
        conn.commit()
    return jsonify({'success': True, 'message': '规格已删除'})


# ── 规格值管理 ──
@shop_bp.route('/products/<int:pid>/specs/<int:sid>/values', methods=['POST'])
def create_spec_value(pid, sid):
    """添加规格值"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    value = data.get('spec_value', '').strip()
    if not value:
        return jsonify({'success': False, 'error': '规格值不能为空'}), 400
    with get_db() as conn:
        conn.execute(
            'INSERT INTO product_spec_values (spec_id, spec_value, sort_order) VALUES (?,?,?)',
            (sid, value, int(data.get('sort_order', 0)))
        )
        vid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
    return jsonify({'success': True, 'data': {'id': vid}, 'message': '规格值已添加'})


@shop_bp.route('/products/<int:pid>/specs/values/<int:vid>', methods=['PUT'])
def update_spec_value(pid, vid):
    """修改规格值"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    value = data.get('spec_value', '').strip()
    if not value:
        return jsonify({'success': False, 'error': '规格值不能为空'}), 400
    with get_db() as conn:
        conn.execute('UPDATE product_spec_values SET spec_value=?, sort_order=? WHERE id=?',
                     (value, int(data.get('sort_order', 0)), vid))
        conn.commit()
    return jsonify({'success': True, 'message': '规格值已更新'})


@shop_bp.route('/products/<int:pid>/specs/values/<int:vid>', methods=['DELETE'])
def delete_spec_value(pid, vid):
    """删除规格值"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('DELETE FROM product_spec_values WHERE id=?', (vid,))
        conn.commit()
    return jsonify({'success': True, 'message': '规格值已删除'})


# =============================================
# SKU 管理
# =============================================
@shop_bp.route('/products/<int:pid>/skus', methods=['GET'])
def list_skus(pid):
    """获取商品SKU列表"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM product_skus WHERE product_id=? ORDER BY id ASC', (pid,)
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@shop_bp.route('/products/<int:pid>/skus/generate', methods=['POST'])
def generate_skus(pid):
    """
    根据规格组合自动生成SKU
    例如：颜色[红,蓝] × 尺寸[S,L] → 4个SKU
    """
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    base_price = float(data.get('base_price', 0))

    with get_db() as conn:
        # 获取所有规格及其值
        specs = conn.execute(
            'SELECT * FROM product_specs WHERE product_id=? ORDER BY sort_order ASC', (pid,)
        ).fetchall()
        if not specs:
            return jsonify({'success': False, 'error': '请先添加规格'}), 400

        spec_values = {}
        for s in specs:
            vals = conn.execute(
                'SELECT * FROM product_spec_values WHERE spec_id=? ORDER BY sort_order ASC', (s['id'],)
            ).fetchall()
            if not vals:
                return jsonify({'success': False, 'error': f'规格"{s["spec_name"]}"缺少规格值'}), 400
            spec_values[s['id']] = {
                'name': s['spec_name'],
                'values': [dict(v) for v in vals]
            }

    # 笛卡尔积生成所有组合
    value_lists = [sv['values'] for sv in spec_values.values()]
    spec_ids = list(spec_values.keys())

    from itertools import product
    combinations = list(product(*value_lists))

    created_skus = []
    with get_db() as conn:
        for combo in combinations:
            spec_path = {}
            parts = []
            for i, v in enumerate(combo):
                spec_name = spec_values[spec_ids[i]]['name']
                spec_path[spec_name] = v['spec_value']
                parts.append(v['spec_value'])
            sku_code = f"SKU-{pid}-{'-'.join(parts)}"

            # 检查是否已存在
            existing = conn.execute(
                'SELECT id FROM product_skus WHERE product_id=? AND sku_code=?', (pid, sku_code)
            ).fetchone()
            if existing:
                continue

            conn.execute(
                'INSERT INTO product_skus (product_id, sku_code, spec_path, price, stock) VALUES (?,?,?,?,?)',
                (pid, sku_code, json.dumps(spec_path, ensure_ascii=False), base_price, 0)
            )
            sku_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            created_skus.append({'id': sku_id, 'sku_code': sku_code, 'spec_path': spec_path,
                                'price': base_price, 'stock': 0})
        conn.commit()

    return jsonify({
        'success': True,
        'data': {'skus': created_skus, 'total': len(created_skus)},
        'message': f'已生成 {len(created_skus)} 个SKU'
    })


@shop_bp.route('/products/<int:pid>/skus/<int:skuid>', methods=['PUT'])
def update_sku(pid, skuid):
    """修改SKU信息（价格/库存/图片）"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    fields = ['price', 'stock', 'image', 'is_active']
    sets = []
    vals = []
    for f in fields:
        if f in data:
            sets.append(f'{f}=?')
            vals.append(data[f])
    if not sets:
        return jsonify({'success': False, 'error': '无更新数据'}), 400
    sets.append("updated_at=datetime('now','localtime')")
    vals.append(skuid)
    with get_db() as conn:
        conn.execute(f'UPDATE product_skus SET {",".join(sets)} WHERE id=? AND product_id=?', vals + [pid])
        conn.commit()
    return jsonify({'success': True, 'message': 'SKU已更新'})


@shop_bp.route('/products/<int:pid>/skus/<int:skuid>', methods=['DELETE'])
def delete_sku(pid, skuid):
    """删除SKU"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('DELETE FROM product_skus WHERE id=? AND product_id=?', (skuid, pid))
        conn.commit()
    return jsonify({'success': True, 'message': 'SKU已删除'})


# =============================================
# 商品分类管理 (Categories)
# =============================================
@shop_bp.route('/categories', methods=['GET'])
def list_categories():
    """获取分类树"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM categories ORDER BY level ASC, sort_order ASC, id ASC'
        ).fetchall()

    # 构建树形结构
    cats = [dict(r) for r in rows]
    tree = []
    cat_map = {}
    for c in cats:
        c['children'] = []
        cat_map[c['id']] = c
    for c in cats:
        if c['parent_id'] and c['parent_id'] in cat_map:
            cat_map[c['parent_id']]['children'].append(c)
        else:
            tree.append(c)

    return jsonify({'success': True, 'data': {'tree': tree, 'list': cats}})


@shop_bp.route('/categories', methods=['POST'])
def create_category():
    """创建分类"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': '分类名不能为空'}), 400
    parent_id = int(data.get('parent_id', 0))
    level = 0
    if parent_id:
        with get_db() as conn:
            parent = conn.execute('SELECT level FROM categories WHERE id=?', (parent_id,)).fetchone()
            if parent:
                level = parent['level'] + 1

    slug = data.get('slug', '').strip() or name.lower().replace(' ', '-')
    with get_db() as conn:
        try:
            conn.execute(
                'INSERT INTO categories (name, slug, parent_id, level, icon, sort_order, is_active) VALUES (?,?,?,?,?,?,?)',
                (name, slug, parent_id, level, data.get('icon', ''), int(data.get('sort_order', 0)), 1)
            )
            cid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.commit()
        except Exception as e:
            return jsonify({'success': False, 'error': f'创建失败: {e}'}), 400
    return jsonify({'success': True, 'data': {'id': cid}, 'message': '分类已创建'})


@shop_bp.route('/categories/<int:cid>', methods=['PUT'])
def update_category(cid):
    """修改分类"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    fields = ['name', 'slug', 'icon', 'sort_order', 'is_active', 'parent_id']
    sets = []
    vals = []
    for f in fields:
        if f in data:
            sets.append(f'{f}=?')
            vals.append(data[f])
    if not sets:
        return jsonify({'success': False, 'error': '无更新数据'}), 400
    # 如果更新了 parent_id，重算 level
    if 'parent_id' in data:
        parent_id = int(data.get('parent_id', 0))
        level = 0
        if parent_id:
            with get_db() as conn:
                parent = conn.execute('SELECT level FROM categories WHERE id=?', (parent_id,)).fetchone()
                if parent:
                    level = parent['level'] + 1
        sets.append('level=?')
        vals.append(level)
    sets.append("updated_at=datetime('now','localtime')")
    vals.append(cid)
    with get_db() as conn:
        conn.execute(f'UPDATE categories SET {",".join(sets)} WHERE id=?', vals)
        conn.commit()
    return jsonify({'success': True, 'message': '分类已更新'})


@shop_bp.route('/categories/<int:cid>', methods=['DELETE'])
def delete_category(cid):
    """删除分类"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        # 检查是否有子分类
        children = conn.execute('SELECT id FROM categories WHERE parent_id=?', (cid,)).fetchall()
        if children:
            return jsonify({'success': False, 'error': '请先删除子分类'}), 400
        # 检查是否有商品使用此分类
        prods = conn.execute('SELECT id FROM products WHERE category_id=? LIMIT 1', (cid,)).fetchall()
        if prods:
            return jsonify({'success': False, 'error': '该分类下有商品，无法删除'}), 400
        conn.execute('DELETE FROM categories WHERE id=?', (cid,))
        conn.commit()
# =============================================
# AI 智能优化 — 直接使用 AIEngine，支持 DeepSeek/阿里百炼/硅基流动/OpenAI等
# =============================================
class ShopAIProcessor:
    """商城AI内容处理器，内置 Prompt 模板，无需外部依赖"""

    SYSTEM_PROMPT = '你是一个专业的电商文案优化专家，擅长优化商品标题和描述，使其更具吸引力和营销力。'

    def __init__(self):
        self.engine = None
        self.provider = None
        self.model = None
        self._init_engine()

    def _read_config(self, key, default=''):
        try:
            with get_db() as conn:
                row = conn.execute("SELECT value FROM system_config WHERE key=?", (key,)).fetchone()
                return row['value'] if row and row['value'] else default
        except Exception:
            return default

    def _init_engine(self):
        """使用 system_config 配置初始化 AIEngine"""
        try:
            self.provider = self._read_config('shop_ai_provider', 'deepseek')
            self.model = self._read_config('shop_ai_model', 'deepseek-chat')

            from agent_matrix.engine import AIEngine
            agent_config = {
                'provider': self.provider,
                'model_name': self.model,
                'api_key_ref': f'{self.provider}_api_key',
                'system_prompt': self.SYSTEM_PROMPT,
            }
            self.engine = AIEngine(agent_config)
            if not self.engine or not self.engine.client:
                self.engine = None
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.engine = None

    def _call_ai(self, prompt, max_tokens=2048, temperature=0.7):
        """调用 LLM，返回 (成功, 内容)"""
        if not self.engine or not self.engine.client:
            return False, 'AI引擎未初始化，请检查 system_config 中的 shop_ai_provider/shop_ai_model 及对应 API Key'
        try:
            resp = self.engine.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self.SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if resp.choices and resp.choices[0].message.content:
                return True, resp.choices[0].message.content.strip()
            return False, 'AI 返回空内容'
        except Exception as e:
            return False, str(e)

    def is_ready(self):
        return self.engine is not None and self.engine.client is not None

    # ── 标题优化（多版本） ──
    def generate_title_options(self, product_info):
        """生成 3 个风格不同的标题选项"""
        original_title = product_info.get('title', '')
        if not original_title:
            return False, '原始标题不能为空'

        prompt = f'''你是一个电商标题优化专家。请根据以下商品信息，生成 3 个优化后的商品标题。

原始标题：{original_title}
商品描述：{product_info.get('description', '无')[:200]}
商品类目：{product_info.get('category', '无')}

要求：
1. 标题长度 20-40 字
2. 包含核心卖点和关键词
3. SEO 友好，适合电商平台搜索
4. 3 个标题风格不同：①专业型  ②吸引力型  ③简洁型

请以 JSON 格式返回，不要包含任何其他文本：
[{{"id":1,"title":"标题1","style":"professional","reason":"选择理由"}},{{"id":2,"title":"标题2","style":"appealing","reason":"选择理由"}},{{"id":3,"title":"标题3","style":"concise","reason":"选择理由"}}]'''

        success, response = self._call_ai(prompt, max_tokens=800, temperature=0.8)
        if not success:
            return False, response

        import re
        try:
            options = json.loads(response)
            if not isinstance(options, list):
                m = re.search(r'\[[\s\S]*?\]', response)
                if m:
                    options = json.loads(m.group())
                else:
                    return False, 'AI 返回格式无效，未能解析 JSON'
            result = []
            for opt in options:
                result.append({
                    'id': opt.get('id', len(result) + 1),
                    'title': opt.get('title', ''),
                    'style': opt.get('style', 'normal'),
                    'reason': opt.get('reason', ''),
                })
            return True, result
        except (json.JSONDecodeError, Exception) as e:
            return False, f'解析 AI 返回结果失败: {e}'

    # ── 描述优化 ──
    def optimize_description(self, original_description, product_features=None):
        """重写商品描述，突出卖点"""
        if not original_description or not original_description.strip():
            return False, '原始描述不能为空'

        prompt = f'''你是一个电商描述优化专家。请优化以下商品描述：

原始描述：{original_description}

要求：
1. 保持核心信息完整
2. 突出产品卖点和优势
3. 语言生动有感染力，适合电商平台展示
4. 使用段落结构，200-500 字
5. 无需包含标题，直接输出描述正文'''

        if product_features and product_features.get('specs'):
            prompt += f'\n\n商品特征/规格：{product_features["specs"]}'

        success, optimized = self._call_ai(prompt, max_tokens=1500, temperature=0.6)
        if success and optimized:
            optimized = optimized.strip().strip('"').strip("'")
        return success, optimized

    # ── 卖点生成 ──
    def _generate_selling_points(self, product_info):
        """生成 3-5 个核心卖点"""
        specs = product_info.get('specs', [])
        specs_text = ', '.join(str(s) for s in specs) if isinstance(specs, list) else str(specs)

        prompt = f'''请为以下商品生成 3-5 个核心卖点：

商品名称：{product_info.get('title', '')}
商品描述：{product_info.get('description', '')[:300]}
{('规格: ' + specs_text) if specs_text else ''}

要求：
1. 每个卖点一句话，简洁有力
2. 突出差异化优势
3. 从用户角度出发，强调利益而非功能
4. 适合在商品详情页展示

请以 JSON 数组格式返回，不要包含其他文本：
["卖点1","卖点2","卖点3"]'''

        success, response = self._call_ai(prompt, max_tokens=500, temperature=0.6)
        if not success:
            return False, []

        import re
        try:
            points = json.loads(response)
            if not isinstance(points, list):
                m = re.search(r'\[[\s\S]*?\]', response)
                if m:
                    points = json.loads(m.group())
                else:
                    points = []
            return True, [p.strip() for p in points if p.strip()][:5]
        except (json.JSONDecodeError, Exception):
            # Fallback: 按行解析
            points = []
            for line in response.split('\n'):
                line = line.strip().lstrip('- •*·').strip()
                if line and len(line) > 5:
                    points.append(line)
            return (True, points[:5]) if points else (False, [])

    # ── 标签生成 ──
    def _generate_tags(self, product_info):
        """生成 5-8 个相关标签"""
        desc = product_info.get('description', '') or ''
        prompt = f'''请为以下商品生成 5-8 个相关标签：

商品名称：{product_info.get('title', '')}
商品类目：{product_info.get('category', '无')}
描述：{desc[:100]}

要求：标签需覆盖商品核心属性、功能、使用场景。

请以 JSON 数组格式返回：
["标签1","标签2","标签3"]'''

        success, response = self._call_ai(prompt, max_tokens=200, temperature=0.5)
        if not success:
            return False, []

        try:
            tags = json.loads(response)
            if isinstance(tags, list):
                return True, [t.strip() for t in tags if t.strip()][:8]
        except (json.JSONDecodeError, Exception):
            tags = [t.strip().strip('"[]\'') for t in response.replace('"', '').split(',')]
            return True, [t for t in tags if t][:8]
        return False, []


def _get_ai_processor():
    """获取商城AI处理器实例 — 使用 AIEngine，支持 DeepSeek/阿里百炼/硅基流动/OpenAI/OpenRouter/Ollama"""
    proc = ShopAIProcessor()
    return proc if proc.is_ready() else None




@shop_bp.route('/products/<int:pid>/ai-optimize', methods=['POST'])
def ai_optimize_product(pid):
    """AI全量优化：标题 + 描述 + 卖点 + 标签"""
    payload, err = _require_admin()
    if err:
        return err

    proc = _get_ai_processor()
    if not proc or not proc.engine:
        return jsonify({'success': False, 'error': 'AI服务不可用，请检查API Key配置'}), 503

    with get_db() as conn:
        row = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        product = _product_to_dict(row)

    title = product.get('title', '')
    desc = product.get('description', '')
    category = product.get('category', '')
    features_list = product.get('features', [])
    features_str = ' '.join(features_list) if features_list else ''

    result = {
        'optimized_title': '',
        'title_options': [],
        'optimized_description': '',
        'selling_points': [],
        'tags': [],
    }

    try:
        # 1. 标题优化（多版本）
        if title:
            success, title_options = proc.generate_title_options({
                'title': title,
                'category': category,
                'description': features_str or desc[:200],
            })
            if success and title_options:
                result['title_options'] = title_options
                result['optimized_title'] = title_options[0]['title']

        # 2. 描述优化
        if desc:
            success, opt_desc = proc.optimize_description(desc, {'specs': features_str})
            if success:
                result['optimized_description'] = opt_desc

        # 3. 卖点生成
        if title or features_str:
            success, points = proc._generate_selling_points({
                'title': title,
                'description': features_str or desc[:300],
                'specs': features_list,
            })
            if success:
                result['selling_points'] = points

        # 4. 标签生成
        if title:
            success, tags = proc._generate_tags({
                'title': title,
                'category': category,
                'description': desc[:200] if desc else features_str,
            })
            if success:
                result['tags'] = tags

        _log_admin_action(payload.get('user_id', 0), 'ai_optimize', 'product', pid,
                          f'AI优化: {title[:30]}...')
        return jsonify({'success': True, 'data': result})

    except Exception as e:
        return jsonify({'success': False, 'error': f'AI优化失败: {str(e)}'}), 500


@shop_bp.route('/products/<int:pid>/ai-title', methods=['POST'])
def ai_optimize_title(pid):
    """AI单功能：标题多版本生成"""
    payload, err = _require_admin()
    if err:
        return err

    proc = _get_ai_processor()
    if not proc or not proc.engine:
        return jsonify({'success': False, 'error': 'AI服务不可用'}), 503

    with get_db() as conn:
        row = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        product = _product_to_dict(row)

    try:
        features_str = ' '.join(product.get('features', []))
        success, options = proc.generate_title_options({
            'title': product.get('title', ''),
            'category': product.get('category', ''),
            'description': features_str or (product.get('description', '')[:200]),
        })
        if not success:
            return jsonify({'success': False, 'error': options or 'AI标题生成失败'}), 500
        return jsonify({'success': True, 'data': {'options': options}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/products/<int:pid>/ai-description', methods=['POST'])
def ai_optimize_description(pid):
    """AI单功能：描述重写"""
    payload, err = _require_admin()
    if err:
        return err

    proc = _get_ai_processor()
    if not proc or not proc.engine:
        return jsonify({'success': False, 'error': 'AI服务不可用'}), 503

    with get_db() as conn:
        row = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        product = _product_to_dict(row)

    data = request.get_json() or {}
    custom_desc = data.get('description', '') or product.get('description', '')
    if not custom_desc:
        return jsonify({'success': False, 'error': '没有可优化的描述内容'}), 400

    try:
        features_str = ' '.join(product.get('features', []))
        success, optimized = proc.optimize_description(custom_desc, {'specs': features_str})
        if not success:
            return jsonify({'success': False, 'error': optimized or 'AI描述优化失败'}), 500
        return jsonify({'success': True, 'data': {'description': optimized}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/products/<int:pid>/ai-features', methods=['POST'])
def ai_generate_features(pid):
    """AI单功能：生成卖点列表"""
    payload, err = _require_admin()
    if err:
        return err

    proc = _get_ai_processor()
    if not proc or not proc.engine:
        return jsonify({'success': False, 'error': 'AI服务不可用'}), 503

    with get_db() as conn:
        row = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '商品不存在'}), 404
        product = _product_to_dict(row)

    try:
        success, points = proc._generate_selling_points({
            'title': product.get('title', ''),
            'description': product.get('description', '')[:300],
            'specs': product.get('features', []),
        })
        if not success:
            return jsonify({'success': False, 'error': 'AI卖点生成失败'}), 500
        return jsonify({'success': True, 'data': {'features': points}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/products/ai-batch', methods=['POST'])
def ai_batch_optimize():
    """批量AI优化多个商品"""
    payload, err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    product_ids = data.get('product_ids', [])
    optimize_type = data.get('type', 'all')  # all / title / description / features

    if not product_ids or len(product_ids) > 20:
        return jsonify({'success': False, 'error': '请选择1-20个商品'}), 400

    proc = _get_ai_processor()
    if not proc or not proc.engine:
        return jsonify({'success': False, 'error': 'AI服务不可用'}), 503

    results = []
    with get_db() as conn:
        placeholders = ','.join('?' * len(product_ids))
        rows = conn.execute(
            f'SELECT * FROM products WHERE id IN ({placeholders})',
            product_ids
        ).fetchall()

    for row in rows:
        p = _product_to_dict(row)
        item = {'product_id': p['id'], 'title': p.get('title', '')}
        features_str = ' '.join(p.get('features', []))
        try:
            if optimize_type in ('all', 'title'):
                s, opts = proc.generate_title_options({
                    'title': p.get('title', ''),
                    'category': p.get('category', ''),
                    'description': features_str or (p.get('description', '')[:200]),
                })
                if s and opts:
                    item['optimized_title'] = opts[0]['title']
                    item['title_options'] = opts

            if optimize_type in ('all', 'description') and p.get('description'):
                s, opt_desc = proc.optimize_description(
                    p['description'], {'specs': features_str}
                )
                if s:
                    item['optimized_description'] = opt_desc

            if optimize_type in ('all', 'features'):
                s, points = proc._generate_selling_points({
                    'title': p.get('title', ''),
                    'description': p.get('description', '')[:300],
                    'specs': p.get('features', []),
                })
                if s:
                    item['selling_points'] = points

            item['success'] = True
        except Exception as e:
            item['success'] = False
            item['error'] = str(e)

        results.append(item)

    _log_admin_action(payload.get('user_id', 0), 'ai_batch_optimize', 'product',
                      ','.join(str(x) for x in product_ids),
                      f'批量AI优化({optimize_type}): {len(results)}个')
    return jsonify({'success': True, 'data': {'results': results, 'total': len(results)}})


# =============================================
# 优惠券管理
# =============================================
@shop_bp.route('/coupons', methods=['GET'])
def list_coupons():
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM coupons ORDER BY id DESC').fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # 计算使用率
        total_limit = d.get('usage_limit', 0) or d.get('max_uses', 0)
        if total_limit > 0:
            d['usage_rate'] = round(d['used_count'] / total_limit * 100, 1)
        else:
            d['usage_rate'] = 0
        result.append(d)
    return jsonify({'success': True, 'data': result})


@shop_bp.route('/coupons', methods=['POST'])
def create_coupon():
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    data['code'] = data.get('code', '').strip().upper()
    if not data.get('code') or not data.get('value'):
        return jsonify({'success': False, 'error': '缺少必填字段: code, value'}), 400
    with get_db() as conn:
        existing = conn.execute('SELECT id FROM coupons WHERE code=?', (data['code'],)).fetchone()
        if existing:
            return jsonify({'success': False, 'error': '优惠券代码已存在'}), 400
        conn.execute(
            '''INSERT INTO coupons (code, name, coupon_type, value, min_amount, min_quantity,
               usage_limit, per_user_limit, expire_at, is_active, description, coupon_category,
               applicable_products, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))''',
            (
                data['code'],
                data.get('name', ''),
                data.get('coupon_type', 'fixed'),
                float(data['value']),
                float(data.get('min_amount', 0)),
                int(data.get('min_quantity', 0)),
                int(data.get('usage_limit', 0)),
                int(data.get('per_user_limit', 1)),
                data.get('expire_at', ''),
                1,
                data.get('description', ''),
                data.get('coupon_category', 'general'),
                data.get('applicable_products', ''),
            )
        )
        cid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'create', 'coupon', cid, data['code'])
    return jsonify({'success': True, 'data': {'id': cid}, 'message': '优惠券已创建'})


@shop_bp.route('/coupons/<int:cid>', methods=['PUT'])
def update_coupon(cid):
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    fields = ['name', 'coupon_type', 'value', 'min_amount', 'min_quantity',
              'usage_limit', 'per_user_limit', 'expire_at', 'is_active',
              'description', 'coupon_category', 'applicable_products']
    sets = []
    vals = []
    for f in fields:
        if f in data:
            sets.append(f'{f}=?')
            vals.append(data[f])
    if not sets:
        return jsonify({'success': False, 'error': '无更新数据'}), 400
    vals.append(cid)
    with get_db() as conn:
        conn.execute(f'UPDATE coupons SET {",".join(sets)} WHERE id=?', vals)
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'update', 'coupon', cid)
    return jsonify({'success': True, 'message': '优惠券已更新'})


@shop_bp.route('/coupons/<int:cid>', methods=['DELETE'])
def delete_coupon(cid):
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('DELETE FROM coupons WHERE id=?', (cid,))
        conn.execute('DELETE FROM coupon_redemptions WHERE coupon_id=?', (cid,))
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'delete', 'coupon', cid)
    return jsonify({'success': True, 'message': '优惠券已删除'})


# =============================================
# 优惠券统计
# =============================================
@shop_bp.route('/coupons/stats', methods=['GET'])
def coupon_stats():
    """优惠券使用统计"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        total_coupons = conn.execute('SELECT COUNT(*) as c FROM coupons').fetchone()['c']
        active_coupons = conn.execute('SELECT COUNT(*) as c FROM coupons WHERE is_active=1').fetchone()['c']
        total_used = conn.execute('SELECT SUM(used_count) as c FROM coupons').fetchone()['c'] or 0
        # 总折扣金额（从 coupon_redemptions 统计）
        total_discount_fen = conn.execute(
            'SELECT COALESCE(SUM(discount_fen),0) as c FROM coupon_redemptions'
        ).fetchone()['c']
        total_discount = 0
        # 也计算 shop 订单的折扣
        shop_discount = conn.execute(
            'SELECT COALESCE(SUM(discount),0) as c FROM order_items WHERE coupon_id IS NOT NULL'
        ).fetchone()['c']
        total_discount = round(total_discount_fen / 100.0 + shop_discount, 2)
        # 各分类统计
        by_category = conn.execute(
            "SELECT coupon_category, COUNT(*) as c FROM coupons GROUP BY coupon_category"
        ).fetchall()
        # 各类型统计
        by_type = conn.execute(
            "SELECT coupon_type, COUNT(*) as c FROM coupons GROUP BY coupon_type"
        ).fetchall()
        # 使用次数排行 TOP 10
        top_used = conn.execute(
            "SELECT code, name, used_count FROM coupons ORDER BY used_count DESC LIMIT 10"
        ).fetchall()
    return jsonify({'success': True, 'data': {
        'total_coupons': total_coupons,
        'active_coupons': active_coupons,
        'total_used': total_used,
        'total_discount': total_discount,
        'by_category': [dict(r) for r in by_category],
        'by_type': [dict(r) for r in by_type],
        'top_used': [dict(r) for r in top_used],
    }})


# =============================================
# 优惠券发放（批量发放给用户）
# =============================================
@shop_bp.route('/coupons/distribute', methods=['POST'])
def distribute_coupons():
    """批量发放优惠券给指定用户"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    coupon_id = data.get('coupon_id')
    user_ids = data.get('user_ids', [])  # 指定用户ID列表
    all_users = data.get('all_users', False)  # 或发放给所有用户

    if not coupon_id:
        return jsonify({'success': False, 'error': '请指定优惠券ID'}), 400
    if not user_ids and not all_users:
        return jsonify({'success': False, 'error': '请指定用户或选择发放给所有用户'}), 400

    with get_db() as conn:
        coupon = conn.execute('SELECT * FROM coupons WHERE id=?', (coupon_id,)).fetchone()
        if not coupon:
            return jsonify({'success': False, 'error': '优惠券不存在'}), 404

        # 获取目标用户
        if all_users:
            rows = conn.execute('SELECT id FROM users WHERE active=1').fetchall()
            user_ids = [r['id'] for r in rows]

        # 批量插入 coupon_redemptions
        count = 0
        for uid in user_ids:
            # 检查是否已发放过
            existing = conn.execute(
                'SELECT id FROM coupon_redemptions WHERE coupon_id=? AND user_id=?',
                (coupon_id, uid)
            ).fetchone()
            if not existing:
                conn.execute(
                    'INSERT INTO coupon_redemptions (coupon_id, user_id, order_no, discount_fen, created_at) VALUES (?,?,?,?,datetime("now","localtime"))',
                    (coupon_id, uid, f'distribute_{coupon_id}_{uid}', 0)
                )
                count += 1

        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'distribute', 'coupon', coupon_id,
                          f'发放给{count}个用户')
    return jsonify({'success': True, 'data': {'total': count}, 'message': f'已发放给 {count} 个用户'})


# =============================================
# 优惠券发放记录查询
# =============================================
@shop_bp.route('/coupons/<int:cid>/redemptions', methods=['GET'])
def coupon_redemptions(cid):
    """查看优惠券使用记录"""
    payload, err = _require_admin()
    if err:
        return err
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute(
            'SELECT COUNT(*) as c FROM coupon_redemptions WHERE coupon_id=?',
            (cid,)
        ).fetchone()['c']
        rows = conn.execute(
            '''SELECT r.*, u.nickname, u.phone FROM coupon_redemptions r
               LEFT JOIN users u ON u.id=r.user_id
               WHERE r.coupon_id=? ORDER BY r.created_at DESC LIMIT ? OFFSET ?''',
            (cid, limit, offset)
        ).fetchall()
    return jsonify({'success': True, 'data': {
        'total': total, 'page': page, 'redemptions': [dict(r) for r in rows]
    }})


# =============================================
# 订单管理
# =============================================
@shop_bp.route('/orders', methods=['GET'])
def list_orders():
    payload, err = _require_admin()
    if err:
        return err
    status = request.args.get('status', '')
    with get_db() as conn:
        sql = '''SELECT oi.*, u.username, u.phone, p.title as prod_title
                 FROM order_items oi
                 LEFT JOIN users u ON oi.user_id=u.id
                 LEFT JOIN products p ON oi.product_id=p.id'''
        params = []
        if status:
            sql += ' WHERE oi.status=?'
            params.append(status)
        sql += ' ORDER BY oi.created_at DESC'
        rows = conn.execute(sql, params).fetchall()
    data = []
    for r in rows:
        d = dict(r)
        d['shipping_status_text'] = ''
        if d.get('shipping_status') == 'shipped':
            from services.kdniao_service import get_shipping_status_text
            d['shipping_status_text'] = get_shipping_status_text(d['shipping_status'])
        data.append(d)
    return jsonify({'success': True, 'data': data})


@shop_bp.route('/orders/<int:oid>/detail', methods=['GET'])
def order_detail(oid):
    """订单详情 — 含商品快照、支付记录、物流信息"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute(
            '''SELECT oi.*, u.username, u.phone, u.display_name,
                      p.title as prod_title, p.thumbnail as prod_thumb,
                      p.price as prod_price
               FROM order_items oi
               LEFT JOIN users u ON oi.user_id=u.id
               LEFT JOIN products p ON oi.product_id=p.id
               WHERE oi.id=?''', (oid,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404

        d = dict(row)

        # 支付事件记录
        payments = conn.execute(
            "SELECT * FROM payment_events WHERE order_no=? ORDER BY created_at DESC",
            (d.get('order_no') or d.get('id'),)
        ).fetchall()
        d['payments'] = [dict(p) for p in payments]

        # 物流信息
        d['shipping'] = None
        if d.get('shipping_status') == 'shipped':
            try:
                tracking = conn.execute(
                    "SELECT * FROM order_shipping WHERE order_item_id=? ORDER BY created_at DESC",
                    (oid,)
                ).fetchall()
                d['shipping'] = [dict(t) for t in tracking] if tracking else None
            except Exception:
                d['shipping'] = None

    return jsonify({'success': True, 'data': d})


@shop_bp.route('/orders/<int:pid>/confirm', methods=['POST'])
def confirm_order(oid):
    """确认订单支付 → 自动触发云服务开通"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('SELECT * FROM order_items WHERE id=?', (oid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] != 'pending':
            return jsonify({'success': False, 'error': '只能确认待支付订单'}), 400
        conn.execute(
            "UPDATE order_items SET status='paid', paid_at=datetime('now','localtime') WHERE id=?",
            (oid,))
        # 添加 user_purchases 记录
        conn.execute('''INSERT OR IGNORE INTO user_purchases
            (user_id, product_id, order_id, purchase_type, status, created_at)
            VALUES (?,?,?,?,?,datetime('now','localtime'))''',
            (row['user_id'], row['product_id'], row['order_id'], 'once', 'active'))
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'confirm_payment', 'order', oid,
                          f'product_id={row["product_id"]} user_id={row["user_id"]}')

    # ── 自动开通：如果是云服务商品 ──
    try:
        prod_info = None
        with get_db() as conn:
            prod_info = conn.execute(
                'SELECT * FROM products WHERE id=?', (row['product_id'],)).fetchone()
        if prod_info and prod_info.get('product_type') == 'cloud_service':
            import json, threading
            product_config = prod_info.get('product_config', '{}')
            if isinstance(product_config, str):
                product_config = json.loads(product_config)
            specs = product_config.get('specs', {})

            from cloud_provisioner.engine import ProvisionerEngine
            engine = ProvisionerEngine()
            order_data = {
                'order_id': row['order_id'],
                'user_id': row['user_id'],
                'product_id': row['product_id'],
                'product_title': row['product_title'],
                'product_config': product_config,
                'service_type': product_config.get('service_type', 'vps'),
                'provider': 'template',
                'auto_renew': False,
            }
            # 异步开通（不阻塞响应）
            def _provision_async():
                try:
                    result = engine.provision(order_data)
                    print(f'[AutoProvision] order={row["order_id"]} result={result["status"]}')
                except Exception as e:
                    print(f'[AutoProvision] order={row["order_id"]} failed: {e}')
            t = threading.Thread(target=_provision_async, daemon=True)
            t.start()
    except Exception as e:
        print(f'[AutoProvision] Error setting up: {e}')

    return jsonify({'success': True, 'message': '已确认支付，自动开通已触发'})


@shop_bp.route('/orders/<int:oid>/refund', methods=['POST'])
def refund_order(oid):
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    with get_db() as conn:
        row = conn.execute('SELECT * FROM order_items WHERE id=?', (oid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] == 'refunded':
            return jsonify({'success': False, 'error': '订单已退款'}), 400
        if row['status'] not in ('paid', 'shipped', 'refunding'):
            return jsonify({'success': False, 'error': '当前订单状态不允许退款'}), 400
        conn.execute('UPDATE products SET sales_count = MAX(0, sales_count - ?) WHERE id=?',
                     (row['quantity'], row['product_id']))
        conn.execute(
            "UPDATE order_items SET status='refunded', refunded_at=datetime('now','localtime') WHERE id=?",
            (oid,)
        )
        conn.execute(
            "UPDATE user_purchases SET status='cancelled', expire_at=datetime('now','localtime') "
            "WHERE product_id=? AND user_id=? AND status='active'",
            (row['product_id'], row['user_id'])
        )
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'refund', 'order', oid,
                          f'product_id={row["product_id"]} user_id={row["user_id"]} reason={data.get("reason","")}')
    return jsonify({'success': True, 'message': _('Refunded')})


@shop_bp.route('/orders/<int:oid>/complete', methods=['POST'])
def complete_order_admin(oid):
    """管理员标记订单为已完成"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('SELECT * FROM order_items WHERE id=?', (oid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] not in ('paid', 'shipped'):
            return jsonify({'success': False, 'error': '当前订单状态不允许标记完成'}), 400
        conn.execute(
            "UPDATE order_items SET status='completed', completed_at=datetime('now','localtime') WHERE id=?",
            (oid,)
        )
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'complete', 'order', oid, '')
    return jsonify({'success': True, 'message': '已标记为已完成'})


# =============================================
# 物流发货
# =============================================
@shop_bp.route('/express-companies', methods=['GET'])
def list_express_companies():
    """快递公司列表"""
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute(
            'SELECT code, name FROM express_companies WHERE is_active=1 ORDER BY sort_order'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@shop_bp.route('/orders/<int:oid>/ship', methods=['POST'])
def ship_order(oid):
    """发货：填写快递公司和单号"""
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    company = (data.get('company') or '').strip()
    tracking = (data.get('tracking_number') or '').strip()
    if not company or not tracking:
        return jsonify({'success': False, 'error': '请选择快递公司并填写运单号'}), 400

    with get_db() as conn:
        row = conn.execute('SELECT * FROM order_items WHERE id=?', (oid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if row['status'] != 'paid':
            return jsonify({'success': False, 'error': '只能对已支付订单发货'}), 400
        if row.get('shipping_status') == 'shipped':
            return jsonify({'success': False, 'error': '该订单已发货'}), 400

        conn.execute(
            "UPDATE order_items SET tracking_company=?, tracking_number=?, "
            "shipping_status='shipped', shipped_at=datetime('now','localtime') WHERE id=?",
            (company, tracking, oid)
        )
        conn.commit()
        _log_admin_action(conn, payload['user_id'], 'ship_order', 'order', oid,
                          f'company={company} tracking={tracking}')

    return jsonify({'success': True, 'message': f'已标记发货 ({company}: {tracking})'})


@shop_bp.route('/orders/<int:oid>/track', methods=['GET'])
def track_order(oid):
    """查询物流轨迹"""
    payload, err = _require_admin()
    if err:
        return err

    with get_db() as conn:
        row = conn.execute(
            'SELECT oi.*, ec.kdniao_code FROM order_items oi '
            'LEFT JOIN express_companies ec ON oi.tracking_company=ec.code '
            'WHERE oi.id=?', (oid,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        if not row.get('tracking_number'):
            return jsonify({'success': False, 'error': '该订单尚未发货'}), 400

        shipper_code = row['kdniao_code'] or row['tracking_company']
        logistic_code = row['tracking_number']

    # 调用快递鸟查询
    from services.kdniao_service import query_track
    success, data, err_msg = query_track(shipper_code, logistic_code)

    if not success:
        # 返回基础发货信息 + 错误提示
        return jsonify({
            'success': True,
            'data': {
                'tracking_company': row['tracking_company'],
                'tracking_number': row['tracking_number'],
                'shipped_at': row.get('shipped_at', ''),
                'shipping_status': row.get('shipping_status', ''),
                'traces': [],
                'track_error': err_msg,
            }
        })

    return jsonify({
        'success': True,
        'data': {
            'tracking_company': row['tracking_company'],
            'tracking_number': row['tracking_number'],
            'shipped_at': row.get('shipped_at', ''),
            'shipping_status': row.get('shipping_status', ''),
            'traces': data.get('traces', []),
            'state': data.get('state', 0),
            'state_text': data.get('state_text', ''),
        }
    })


# =============================================
# 购买记录
# =============================================
@shop_bp.route('/purchases', methods=['GET'])
def list_purchases():
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT up.*, u.username, u.phone, p.title as prod_title
               FROM user_purchases up
               LEFT JOIN users u ON up.user_id=u.id
               LEFT JOIN products p ON up.product_id=p.id
               ORDER BY up.created_at DESC LIMIT 100'''
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})
