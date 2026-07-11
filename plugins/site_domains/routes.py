# Site Domains Routes — 主库 site_domains 表 CRUD + Nginx 配置生成
# 迁移自 admin/app.py:741-894
import os
import re
import sys

_auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
if _auth_dir not in sys.path:
    sys.path.insert(0, _auth_dir)

from flask import Blueprint, request, jsonify

site_domains_bp = Blueprint("site_domains_bp", __name__)


# ── 鉴权（从 admin/app.py 原样移植） ──
def _admin_auth():
    """验证管理员 token，返回 payload 或 None"""
    from services.jwt_service import validate_token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('sso_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return None
    return payload


def _get_main_db():
    """读取主库连接（site_domains 留主库，中间件每请求查询）"""
    from models import get_db
    return get_db()


# ── Caddy On-Demand TLS 校验端点 ──
# Caddy 在为某域名签发证书前调用 `ask` 指向的此接口；返回 200 才放行签发。
# 该接口无需 JWT（Caddy 无法携带管理员 token），但通过两道防线保证安全：
#   1) 仅信任来自本机回环（127.0.0.1）的请求 —— Caddy 与后端同机
#   2) 域名必须已登记在 site_domains 且 is_published=1 —— 签发权绑定业务数据
# 防止攻击者用随机域名耗尽 Let's Encrypt 速率限制。
def _is_loopback_request():
    ra = request.remote_addr or ''
    return ra in ('127.0.0.1', '::1', 'localhost')


@site_domains_bp.route('/internal/caddy/check', methods=['GET'])
def caddy_check_domain():
    """Caddy On-Demand TLS ask 端点：校验域名是否允许签发证书"""
    if not _is_loopback_request():
        return ('forbidden', 403)
    domain = (request.args.get('domain') or '').strip().lower()
    if not domain:
        return ('missing domain', 400)
    # 基础格式校验（防注入/异常输入）
    if not re.match(r'^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?$', domain) or len(domain) > 253:
        return ('invalid domain', 400)
    try:
        with _get_main_db() as conn:
            row = conn.execute(
                'SELECT id FROM site_domains WHERE full_domain=? AND is_published=1',
                (domain,)
            ).fetchone()
    except Exception:
        return ('db error', 500)
    if row:
        return ('ok', 200)
    return ('not allowed', 403)


# ── 路由 ──
@site_domains_bp.route('/admin/api/domains', methods=['GET'])
def list_domains():
    """获取子域名列表 + 配额"""
    payload = _admin_auth()
    if not payload:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    with _get_main_db() as conn:
        rows = conn.execute(
            'SELECT id, site_config_id, subdomain, full_domain, display_name, '
            'template, is_published, page_keys_json, sort_order, service_port, '
            'created_at, updated_at '
            'FROM site_domains ORDER BY sort_order ASC, id ASC'
        ).fetchall()
    data = [dict(r) for r in rows]
    max_domains = 10
    try:
        with _get_main_db() as conn:
            sc = conn.execute("SELECT max_domains FROM site_configs WHERE id=1").fetchone()
            if sc and sc['max_domains']:
                max_domains = sc['max_domains']
    except Exception:
        pass
    used = len(data)
    quota = {'used': used, 'limit': max_domains, 'can_add': used < max_domains}
    return jsonify({'success': True, 'data': data, 'quota': quota})


@site_domains_bp.route('/admin/api/domains', methods=['POST'])
def create_domain():
    """添加子域名"""
    payload = _admin_auth()
    if not payload:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    body = request.get_json(silent=True) or {}
    subdomain = (body.get('subdomain') or '').strip().lower()
    display_name = (body.get('display_name') or '').strip()
    service_port = body.get('service_port')
    if not subdomain or not display_name:
        return jsonify({'success': False, 'error': 'subdomain and display_name required'}), 400
    if not re.match(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$', subdomain):
        return jsonify({'success': False, 'error': 'Invalid subdomain format'}), 400
    if service_port and (not isinstance(service_port, int) or service_port < 1024 or service_port > 65535):
        return jsonify({'success': False, 'error': 'Invalid port range (1024-65535)'}), 400
    deploy_domain = os.environ.get('DEPLOY_DOMAIN', 'localhost')
    full_domain = f"{subdomain}.{deploy_domain}"
    try:
        with _get_main_db() as conn:
            conn.execute(
                'INSERT INTO site_domains (subdomain, full_domain, display_name, service_port) '
                'VALUES (?, ?, ?, ?)',
                (subdomain, full_domain, display_name, service_port)
            )
            conn.commit()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 409
    return jsonify({'success': True, 'message': 'Domain created'})


@site_domains_bp.route('/admin/api/domains/<int:domain_id>', methods=['PUT'])
def update_domain(domain_id):
    """更新子域名"""
    payload = _admin_auth()
    if not payload:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    body = request.get_json(silent=True) or {}
    display_name = (body.get('display_name') or '').strip()
    is_published = body.get('is_published')
    service_port = body.get('service_port')
    if not display_name:
        return jsonify({'success': False, 'error': 'display_name required'}), 400
    with _get_main_db() as conn:
        existing = conn.execute('SELECT id FROM site_domains WHERE id=?', (domain_id,)).fetchone()
        if not existing:
            return jsonify({'success': False, 'error': 'Domain not found'}), 404
        conn.execute(
            'UPDATE site_domains SET display_name=?, is_published=?, service_port=?, '
            "updated_at=datetime('now') WHERE id=?",
            (display_name, 1 if is_published else 0, service_port, domain_id)
        )
        conn.commit()
    return jsonify({'success': True, 'message': 'Domain updated'})


@site_domains_bp.route('/admin/api/domains/<int:domain_id>', methods=['DELETE'])
def delete_domain(domain_id):
    """删除子域名"""
    payload = _admin_auth()
    if not payload:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    with _get_main_db() as conn:
        existing = conn.execute('SELECT id, full_domain FROM site_domains WHERE id=?', (domain_id,)).fetchone()
        if not existing:
            return jsonify({'success': False, 'error': 'Domain not found'}), 404
        conn.execute('DELETE FROM site_domains WHERE id=?', (domain_id,))
        conn.commit()
    return jsonify({'success': True, 'message': f"Domain {existing['full_domain']} deleted"})


@site_domains_bp.route('/admin/api/domains/<int:domain_id>/nginx-config', methods=['GET'])
def get_nginx_config(domain_id):
    """生成 Nginx 配置"""
    payload = _admin_auth()
    if not payload:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    with _get_main_db() as conn:
        row = conn.execute(
            'SELECT id, full_domain, service_port, display_name FROM site_domains WHERE id=?',
            (domain_id,)
        ).fetchone()
    if not row:
        return jsonify({'success': False, 'error': 'Domain not found'}), 404
    if not row['service_port']:
        return jsonify({'success': False, 'error': 'Not an independent service (no port)'}), 400
    domain = row['full_domain']
    port = row['service_port']
    server_path = f"/home/easykai/easykai-workspace/{domain}"
    config_text = (
        f"server {{\n"
        f"    listen 80;\n"
        f"    server_name {domain};\n\n"
        f"    location / {{\n"
        f"        proxy_pass http://127.0.0.1:{port};\n"
        f"        proxy_set_header Host $host;\n"
        f"        proxy_set_header X-Real-IP $remote_addr;\n"
        f"        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        f"        proxy_set_header X-Forwarded-Proto $scheme;\n"
        f"    }}\n"
        f"}}"
    )
    return jsonify({'success': True, 'data': {
        'full_domain': domain,
        'server_path': server_path,
        'config_text': config_text
    }})
