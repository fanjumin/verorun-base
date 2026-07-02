#!/usr/bin/env python3
"""Cloud Provisioner — API 路由"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
from flask import Blueprint, request, jsonify
from models import get_db

provisioner_bp = Blueprint('cloud', __name__, url_prefix='/cloud')

# ── 辅助函数 ──

def _require_auth():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        return None, (jsonify({'success': False, 'error': '请先登录'}), 401)
    from services.jwt_service import validate_token
    payload = validate_token(token)
    if not payload:
        return None, (jsonify({'success': False, 'error': '无效Token'}), 401)
    return payload, None


def _require_admin():
    payload, err = _require_auth()
    if err:
        return None, err
    if not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': '需要管理员权限'}), 403)
    return payload, None


# =============================================
# 云服务商品列表
# =============================================
@provisioner_bp.route('/products', methods=['GET'])
def cloud_products():
    """列出所有云服务类型商品"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE product_type='cloud_service' AND is_active=1 ORDER BY sort_order ASC, id DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d['product_config'] = json.loads(d.get('product_config', '{}'))
        except Exception:
            d['product_config'] = {}
        result.append(d)
    return jsonify({'success': True, 'data': result})


# =============================================
# 我的云资源列表
# =============================================
@provisioner_bp.route('/instances', methods=['GET'])
def my_instances():
    payload, err = _require_auth()
    if err:
        return err
    uid = payload['user_id']
    from .models import get_user_instances
    instances = get_user_instances(uid)
    return jsonify({'success': True, 'data': instances})


@provisioner_bp.route('/instances/<int:iid>', methods=['GET'])
def instance_detail(iid):
    payload, err = _require_auth()
    if err:
        return err
    from .models import get_instance, get_logs
    inst = get_instance(iid)
    if not inst or inst.get('user_id') != payload['user_id']:
        if not payload.get('is_admin'):
            return jsonify({'success': False, 'error': '实例不存在或无权访问'}), 404
        inst = get_instance(iid)
        if not inst:
            return jsonify({'success': False, 'error': '实例不存在'}), 404
    logs = get_logs(iid)
    inst['logs'] = logs
    return jsonify({'success': True, 'data': inst})


# =============================================
# 开通云服务（下单后自动调用）
# =============================================
@provisioner_bp.route('/instances/provision', methods=['POST'])
def provision_instance():
    """
    手动触发开通（管理员用）
    通常由订单支付后自动触发，此接口用于手动重试
    """
    admin, err = _require_admin()
    if err:
        return err

    data = request.get_json(force=True) or {}
    instance_id = data.get('instance_id')
    if not instance_id:
        return jsonify({'success': False, 'error': '缺少 instance_id'}), 400

    from .models import get_instance
    inst = get_instance(instance_id)
    if not inst:
        return jsonify({'success': False, 'error': '实例不存在'}), 404

    from .engine import ProvisionerEngine
    engine = ProvisionerEngine()
    result = engine.provision({
        'order_id': inst['order_id'],
        'user_id': inst['user_id'],
        'product_id': inst['product_id'],
        'product_title': inst['product_title'],
        'product_config': inst.get('metadata', {}),
        'service_type': inst['service_type'],
        'provider': inst['provider'],
        'auto_renew': inst.get('auto_renew', False),
    })

    return jsonify({'success': True, 'data': result})


# =============================================
# 查询实例状态
# =============================================
@provisioner_bp.route('/instances/<int:iid>/status', methods=['GET'])
def instance_status(iid):
    payload, err = _require_auth()
    if err:
        return err
    from .engine import ProvisionerEngine
    engine = ProvisionerEngine()
    status = engine.get_status(iid)
    return jsonify({'success': True, 'data': {'id': iid, 'status': status}})


# =============================================
# 销毁实例
# =============================================
@provisioner_bp.route('/instances/<int:iid>/terminate', methods=['POST'])
def terminate_instance(iid):
    admin, err = _require_admin()
    if err:
        return err
    from .engine import ProvisionerEngine
    engine = ProvisionerEngine()
    success = engine.terminate(iid)
    return jsonify({'success': success, 'message': '已销毁' if success else '销毁失败'})


# =============================================
# 管理端：所有实例
# =============================================
@provisioner_bp.route('/admin/instances', methods=['GET'])
def admin_instances():
    admin, err = _require_admin()
    if err:
        return err
    status = request.args.get('status', '')
    from .models import get_all_instances
    instances = get_all_instances(status=status if status else None)
    return jsonify({'success': True, 'data': instances})


# =============================================
# 管理端：创建云服务商品
# =============================================
@provisioner_bp.route('/admin/products', methods=['POST'])
def admin_create_cloud_product():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    required = ['title', 'price']
    for f in required:
        if f not in data:
            return jsonify({'success': False, 'error': f'缺少必填字段: {f}'}), 400
    if not data.get('product_config'):
        return jsonify({'success': False, 'error': '云服务商品必须提供 product_config'}), 400

    product_config = data.get('product_config', {})
    if isinstance(product_config, str):
        try:
            product_config = json.loads(product_config)
        except Exception:
            return jsonify({'success': False, 'error': 'product_config 必须是有效的 JSON'}), 400

    with get_db() as conn:
        conn.execute('''INSERT INTO products
            (title, subtitle, product_type, category, price, original_price,
             stock, thumbnail, description, features, product_config, sort_order, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (data['title'], data.get('subtitle', ''), 'cloud_service',
             data.get('category', '云计算'), float(data['price']),
             float(data.get('original_price', 0)), int(data.get('stock', 0)),
             data.get('thumbnail', ''), data.get('description', ''),
             json.dumps(data.get('features', [])), json.dumps(product_config),
             int(data.get('sort_order', 0)), 1))
        pid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
    return jsonify({'success': True, 'data': {'id': pid}, 'message': '云服务商品已创建'})
