#!/usr/bin/env python3
# VeroRon 维洛智能 (verorun.com / verorun.cn)
# 版权所有 (c) 2026 樊聚民 (fanjumin). All Rights Reserved.

"""Platform — User Console (端口 8083)"""

import sys, os, sysconfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center'))

# Prepend stdlib path LAST so it stays at sys.path[0] and prevents
# the project's platform/ dir from shadowing stdlib platform module.
stdlib_dir = sysconfig.get_path('stdlib')
if stdlib_dir in sys.path:
    sys.path.remove(stdlib_dir)
sys.path.insert(0, stdlib_dir)
from services.deployment_config import deploy
from services.brand_service import get_brand_settings
from services.notification_service import get_unread_count, mark_read
# ══ routes 包名冲突处理 ══
from auth_blueprint import register_auth
from routes.subscription import sub_bp
from routes.douyin_miniprogram import douyin_mp_bp
try:
    from routes.deployment_api import deploy_bp, init_deployment_tables
    _HAS_DEPLOY_API = True
except ImportError:
    _HAS_DEPLOY_API = False
    deploy_bp = None
    init_deployment_tables = None
    print('[Platform] ⚠️ deployment_api 未找到，跳过独立部署功能')

# 移除 auth-center sys.path
_auth_center_norm = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
sys.path = [p for p in sys.path if os.path.normpath(p) != _auth_center_norm]
_platform_dir = os.path.dirname(os.path.abspath(__file__))
if _platform_dir not in sys.path:
    sys.path.insert(0, _platform_dir)
sys.modules.pop('routes', None)

from routes.api_v1 import api_v1_bp
from routes.shop_public import shop_public_bp
from routes.mini_program import mini_program_bp

from flask import (Flask, request, jsonify, render_template,
                   send_from_directory, redirect, Blueprint, Response, make_response)
from models import get_db, init_shop_db
import json
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

# 初始化商城独立数据库
try:
    init_shop_db()
except Exception as e:
    print(f'[Platform] init_shop_db warning: {e}')


@app.context_processor
def inject_deploy():
    return dict(deploy=deploy)


# ══ i18n ══
from i18n import _, get_lang, get_all_translations

@app.context_processor
def inject_i18n():
    return {'_': _, 'LANG': get_lang(), 'translations': get_all_translations()}
app.jinja_env.globals['_'] = _


# ══ CSP ══
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )
    return response


# AnalyticsMiddleware 仅在 Admin 服务启用，避免多进程 SQLite 写锁竞争
# from analytics.middleware import AnalyticsMiddleware
# AnalyticsMiddleware(app, service_name="platform")
app.config['TEMPLATES_AUTO_RELOAD'] = True
import jinja2
app.jinja_loader = jinja2.ChoiceLoader([
    app.jinja_loader,
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..')),
])

# ── PluginManager ──
try:
    from plugin_manager.manager import PluginManager
    app.plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins')
    PluginManager(app)
    print('[PluginManager] ✅ Platform 服务插件管理器已初始化')
except Exception as e:
    print(f'[PluginManager] ⚠️ Platform 服务初始化失败: {e}')

# ── Blueprint 注册 ──
register_auth(app, exclude_blueprints=['admin', 'cms_admin'])
app.register_blueprint(sub_bp, name='platform_subscription')
app.register_blueprint(api_v1_bp)
app.register_blueprint(douyin_mp_bp)
app.register_blueprint(shop_public_bp)
app.register_blueprint(mini_program_bp)
# 独立部署API — 仅主服务器模式注册
if _HAS_DEPLOY_API:
    _MODE = os.environ.get('EASYKAI_MODE', 'main')
    if _MODE == 'main':
        app.register_blueprint(deploy_bp)
        try:
            init_deployment_tables()
        except Exception:
            print('[Deploy] ⚠️ deployment_tables init skipped')
    else:
        print('[Deploy] 客户端模式，跳过部署API注册')
else:
    print('[Deploy] deployment_api 不可用，跳过注册')

# ── 旧用户中心路由重定向到 SPA ──
@app.route('/user-console/')
@app.route('/user-console/<path:subpath>')
def redirect_user_console(subpath=''):
    return redirect('/', 301)


@app.route('/orders')
def redirect_old_orders():
    return redirect('/', 301)


# ══════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════

def get_domain_config():
    """获取域名和Cookie配置信息"""
    host = request.headers.get('Host', '')
    try:
        brand = get_brand_settings()
        site_domain = brand.get('site_domain', '').strip()
    except Exception:
        site_domain = ''
    if not site_domain:
        site_domain = os.environ.get('DEPLOY_DOMAIN', '')
    host_name = host.split(':')[0].lower()
    cookie_domain = ('.' + site_domain) if site_domain else ('.' + host_name)
    platform_domain = f'platform.{site_domain}' if site_domain else f'platform.{host_name}'
    is_platform_host = (host_name == platform_domain or host_name == 'localhost'
                        or host_name.startswith('127.0.0.1') or host_name.startswith('192.168.'))
    return {
        'host_name': host_name,
        'site_domain': site_domain,
        'cookie_domain': cookie_domain,
        'platform_domain': platform_domain,
        'is_platform_host': is_platform_host,
    }


def handle_oauth_callback(domain_config):
    """处理OAuth登录回调：验证token、设置Cookie、重定向"""
    url_token = request.args.get('token')
    if not url_token:
        return None
    from services.jwt_service import validate_token
    payload = validate_token(url_token)
    if not payload:
        return None
    from urllib.parse import urlencode
    other_params = {k: v for k, v in request.args.items() if k != 'token'}
    target = request.path
    if other_params:
        target += '?' + urlencode(other_params, doseq=True)
    resp = make_response(redirect(target))
    is_secure = request.scheme == 'https'
    resp.set_cookie('sso_token', url_token, domain=domain_config['cookie_domain'],
                    path='/', max_age=604800, samesite='Lax', secure=is_secure, httponly=True)
    return resp


def _chatbot_context():
    """读取 AI Advisor 插件配置，供模板渲染使用。"""
    defaults = {
        'chatbot_enabled': True,
        'chatbot_title': 'AI Advisor',
        'chatbot_subtitle': 'Powered by AI Engine',
        'chatbot_welcome_message': 'Hello! I am your AI advisor. How can I help you today?',
        'chatbot_help_hint': 'Type help to see what I can do for you',
        'chatbot_avatar_url': '/static/ai-chat.png',
        'chatbot_agent_id': 'kai_assistant',
        'chatbot_max_history': 20,
        'chatbot_float_button_text': 'AI Advisor'
    }
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key, value FROM plugin_configs WHERE plugin_name='chatbot'"
            ).fetchall()
        cfg = {r['key']: r['value'] for r in rows}
        return {
            'chatbot_enabled': str(cfg.get('enabled', '1')).lower() in ('1', 'true', 'yes', 'on'),
            'chatbot_title': cfg.get('title', defaults['chatbot_title']),
            'chatbot_subtitle': cfg.get('subtitle', defaults['chatbot_subtitle']),
            'chatbot_welcome_message': cfg.get('welcome_message', defaults['chatbot_welcome_message']),
            'chatbot_help_hint': cfg.get('help_hint', defaults['chatbot_help_hint']),
            'chatbot_avatar_url': cfg.get('avatar_url', defaults['chatbot_avatar_url']),
            'chatbot_agent_id': cfg.get('agent_id', defaults['chatbot_agent_id']),
            'chatbot_max_history': int(cfg.get('max_history', defaults['chatbot_max_history'])),
            'chatbot_float_button_text': cfg.get('float_button_text', defaults['chatbot_float_button_text']),
        }
    except Exception as e:
        print(f'[Platform] chatbot context failed: {e}')
        return defaults


def handle_platform_auth(domain_config):
    """处理平台域名认证，返回后台页面响应或重定向"""
    from services.jwt_service import validate_token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token')

    payload = validate_token(token) if token else None
    if not payload:
        return redirect('/login?redirect=' + request.path)

    resp = make_response(render_template('index.html',
                                         site_domain=domain_config['site_domain'],
                                         server_token=token or '',
                                         **_chatbot_context()))
    is_secure = request.scheme == 'https'
    resp.set_cookie('sso_token', token, domain=domain_config['cookie_domain'],
                    path='/', max_age=604800, samesite='Lax', secure=is_secure, httponly=True)
    return resp


def _get_user_id_from_token():
    """从 JWT token 中提取 user_id"""
    from services.jwt_service import validate_token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token')
    if not token:
        return None
    payload = validate_token(token)
    return payload.get('user_id') if payload else None


# ══════════════════════════════════════════════════════════════
# Routes — User Console
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """用户控制台首页 — 验证登录后渲染 SPA"""
    # 1. 处理 OAuth 回调
    if request.args.get('code'):
        domain_config = get_domain_config()
        oauth_response = handle_oauth_callback(domain_config)
        if oauth_response:
            return oauth_response

    # 2. 验证 token → 渲染控制台
    from services.jwt_service import validate_token
    token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token') or ''
    if token:
        payload = validate_token(token)
        if payload:
            from services.brand_service import get_brand_settings
            brand = get_brand_settings() or {}
            resp = make_response(render_template('index.html', brand=brand, server_token=token, **_chatbot_context()))
            site_domain = brand.get('site_domain', '').strip()
            cd = ('.' + site_domain) if site_domain else ''
            if cd:
                resp.set_cookie('sso_token', token, domain=cd, path='/',
                                max_age=604800, samesite='Lax', secure=True, httponly=True)
            else:
                resp.set_cookie('sso_token', token, path='/',
                                max_age=604800, samesite='Lax', secure=True, httponly=True)
            return resp

    # 3. 未登录 → 重定向到官网登录页
    site_url = deploy.url()
    from urllib.parse import quote
    return redirect(f'{site_url}/login?redirect=' + quote(request.url))


@app.route('/api-keys')
def api_keys_page():
    return redirect('/', 301)


# ══ 通知系统 API ══

@app.route('/api/notifications')
def user_notifications_list():
    """获取当前用户通知列表"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        limit, offset = 50, 0
    with get_db() as conn:
        total = conn.execute(
            'SELECT COUNT(*) as c FROM user_notifications WHERE user_id=?', (user_id,)
        ).fetchone()['c']
        rows = conn.execute(
            'SELECT id, type, title, content, link_url, is_read, created_at '
            'FROM user_notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (user_id, limit, offset)
        ).fetchall()
    return jsonify({
        'success': True,
        'data': [dict(r) for r in rows],
        'total': total,
        'unread': get_unread_count(user_id)
    })


@app.route('/api/notifications/unread-count')
def user_notifications_unread():
    """获取未读通知数量"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    return jsonify({'success': True, 'count': get_unread_count(user_id)})


@app.route('/api/notifications/<int:nid>/read', methods=['PUT'])
def user_notification_mark_read(nid):
    """标记单条通知已读"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    ok = mark_read(user_id, nid)
    return jsonify({'success': ok})


@app.route('/api/notifications/read-all', methods=['PUT'])
def user_notifications_read_all():
    """标记全部通知已读"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    ok = mark_read(user_id)
    return jsonify({'success': ok})


@app.route('/api/notifications/<int:nid>', methods=['DELETE'])
def user_notification_delete(nid):
    """删除单条通知"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        with get_db() as conn:
            conn.execute('DELETE FROM user_notifications WHERE user_id=? AND id=?', (user_id, nid))
            conn.commit()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': True})


@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """用户提交投诉/建议"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'error': '请先登录'}), 401
    data = request.get_json(silent=True) or {}
    fb_type = data.get('type', '').strip()
    category = data.get('category', '').strip()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    contact = data.get('contact', '').strip()

    if fb_type not in ('complaint', 'suggestion'):
        return jsonify({'success': False, 'error': '类型无效'}), 400
    if category not in ('功能问题', '内容问题', '账号问题', '支付问题', '其他'):
        return jsonify({'success': False, 'error': '分类无效'}), 400
    if not title or len(title) > 200:
        return jsonify({'success': False, 'error': '标题 1-200 字'}), 400
    if not content or len(content) > 5000:
        return jsonify({'success': False, 'error': '内容 1-5000 字'}), 400

    try:
        with get_db() as conn:
            conn.execute(
                'INSERT INTO user_feedback (user_id, type, category, title, content, contact) VALUES (?,?,?,?,?,?)',
                (user_id, fb_type, category, title, content, contact)
            )
            conn.commit()
        return jsonify({'success': True, 'message': '感谢您的反馈，我们会尽快处理！'})
    except Exception as e:
        return jsonify({'success': False, 'error': '提交失败: '+str(e)}), 500


# ══ 静态文件 ══

@app.route('/static/media/<path:filename>')
def static_media(filename):
    """服务媒体库文件"""
    media_dir = os.path.join(os.path.dirname(__file__), '..', 'admin', 'static', 'media')
    return send_from_directory(media_dir, filename)


@app.route('/static/<path:filename>')
def static_files(filename):
    plat_path = os.path.join(os.path.dirname(__file__), 'static', filename)
    if os.path.isfile(plat_path):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)
    # 回退查 admin/static（处理 brand/ 等跨服务共享文件）
    admin_static = os.path.join(os.path.dirname(__file__), '..', 'admin', 'static')
    return send_from_directory(admin_static, filename)


# ══ 主题系统 ══
THEMES_ROOT_PLATFORM = os.path.join(os.path.dirname(__file__), '..', 'themes')


def _get_site_key_for_theme():
    return 'platform'


def _get_active_theme_slug_platform():
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'auth-center', 'routes'))
        from theme_admin import get_active_theme_slug_for_site
        return get_active_theme_slug_for_site(_get_site_key_for_theme())
    except Exception:
        return None


_theme_tpl_dir = None
_active_slug = _get_active_theme_slug_platform()
if _active_slug:
    _candidate = os.path.join(THEMES_ROOT_PLATFORM, _active_slug, 'templates')
    if os.path.isdir(_candidate):
        _theme_tpl_dir = _candidate
if _theme_tpl_dir:
    from jinja2 import ChoiceLoader, FileSystemLoader
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(_theme_tpl_dir),
        app.jinja_loader,
    ])


@app.context_processor
def inject_theme():
    slug = _get_active_theme_slug_platform()
    result = {}
    if slug and slug != 'default':
        result['theme_css_url'] = '/themes/{}/theme.css'.format(slug)
    else:
        result['theme_css_url'] = None
    try:
        result['brand'] = get_brand_settings()
    except:
        result['brand'] = None
    return result


@app.route('/themes/<slug>/<path:filename>')
def serve_theme_file(slug, filename):
    import re
    safe_slug = re.sub(r'[^a-z0-9\-]', '', slug.lower())
    if safe_slug != slug:
        return 'Invalid slug', 400
    theme_static = os.path.join(THEMES_ROOT_PLATFORM, slug)
    if not os.path.isdir(theme_static):
        return 'Theme not found', 404
    return send_from_directory(theme_static, filename)


@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "platform", "version": "1.0.0"})


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8083
    app.run(host='0.0.0.0', port=port, debug=False)
