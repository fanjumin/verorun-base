#!/usr/bin/env python3
"""auth-center standalone server (port 8081) - login/OAuth/user/CMS/payment + Main Site"""
import sys, os

# Load .env BEFORE any auth imports (dotnet may be optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from services.deployment_config import deploy

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR in sys.path:
    sys.path.remove(_SCRIPT_DIR)
if '' in sys.path:
    sys.path.remove('')
AUTH_DIR = os.path.join(_SCRIPT_DIR, 'auth-center')
sys.path.insert(0, AUTH_DIR)
sys.path.append(_SCRIPT_DIR)

from flask import Flask, render_template, make_response, request, jsonify
import urllib.request as _ur
from auth_blueprint import register_auth

app = Flask(__name__)

# 主站(www)模板位于 site/templates 与 platform/templates，非本文件同级 templates，
# 因此显式挂载到 jinja loader，避免 public_home.html 等模板 TemplateNotFound。
import jinja2
app.jinja_loader = jinja2.ChoiceLoader([
    jinja2.FileSystemLoader(os.path.join(_SCRIPT_DIR, 'site', 'templates')),
    jinja2.FileSystemLoader(os.path.join(_SCRIPT_DIR, 'main_site', 'templates')),
    app.jinja_loader,
])

app.secret_key = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'

# ══ Try to load i18n ══
try:
    from i18n import _ as _t
except Exception:
    _t = lambda s: s

# ── PluginManager ──
try:
    from plugin_manager.manager import PluginManager
    app.plugins_dir = os.path.join(_SCRIPT_DIR, 'plugins')
    PluginManager(app)
    print('[PluginManager] ✅ Auth 服务插件管理器已初始化')
except Exception as e:
    print(f'[PluginManager] ⚠️ Auth 服务初始化失败: {e}')

register_auth(app)

# ── OAuth Plugin 第三方登录路由 ──
try:
    from plugins.oauth_config.routes.auth import oauth_bp
    app.register_blueprint(oauth_bp)
    print('[OAuth Plugin] ✅ 已注册第三方登录路由')
except ImportError:
    print('[OAuth Plugin] ⚠️ OAuth 插件未安装，第三方登录不可用')
except Exception as e:
    print(f'[OAuth Plugin] ⚠️ 加载失败: {e}')

try:
    from flask_cors import CORS
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
except Exception:
    pass


@app.route('/')
def site_home():
    """Render the main landing page using the existing theme template."""
    site_plans = []
    try:
        from services.subscription_service import get_all_plans
        site_plans = get_all_plans() or []
    except Exception:
        pass
    resp = make_response(render_template('public_home.html', LANG=deploy.LANG, site_plans=site_plans))
    # Set cross-subdomain SSO cookie if token present in URL
    token = request.args.get('token', '')
    if token and len(token) > 20:
        try:
            from services.jwt_service import validate_token
            if validate_token(token):
                main_domain = os.environ.get('DEPLOY_DOMAIN', '')
                if main_domain:
                    resp.set_cookie('sso_token', token, domain='.' + main_domain,
                                    path='/', max_age=604800, samesite='Lax',
                                    secure=True, httponly=True)
        except Exception:
            pass
    return resp


@app.route('/pricing')
def site_pricing():
    """Redirect pricing to the main page (anchor) or render the home page."""
    site_plans = []
    try:
        from services.subscription_service import get_all_plans
        site_plans = get_all_plans() or []
    except Exception:
        pass
    return render_template('public_home.html', LANG=deploy.LANG, site_plans=site_plans)


@app.route('/features')
def site_features():
    site_plans = []
    try:
        from services.subscription_service import get_all_plans
        site_plans = get_all_plans() or []
    except Exception:
        pass
    return render_template('public_home.html', LANG=deploy.LANG, site_plans=site_plans)


@app.route('/contact')
def site_contact():
    site_plans = []
    try:
        from services.subscription_service import get_all_plans
        site_plans = get_all_plans() or []
    except Exception:
        pass
    return render_template('public_home.html', LANG=deploy.LANG, site_plans=site_plans)


@app.route('/login')
def login_page():
    """Unified SSO login page."""
    from services.brand_service import get_brand_settings
    brand = get_brand_settings() or {}
    return render_template('login.html', LANG=deploy.LANG, brand=brand)


# ══ Captcha proxy → admin:8084 ══
def _proxy_captcha(path, data=None, method='GET'):
    url = 'http://127.0.0.1:8084' + path
    req = _ur.Request(url, data=data, method=method)
    if data:
        req.add_header('Content-Type', 'application/json')
    resp = _ur.urlopen(req, timeout=5)
    return resp.read(), resp.status, {'Content-Type': resp.headers.get('Content-Type', 'application/json')}


@app.route('/api/captcha/generate', methods=['GET'])
def captcha_generate():
    try:
        return _proxy_captcha('/api/captcha/generate')
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/captcha/verify', methods=['POST'])
def captcha_verify():
    try:
        return _proxy_captcha('/api/captcha/verify', request.get_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.route('/api/captcha/consume', methods=['POST'])
def captcha_consume():
    try:
        return _proxy_captcha('/api/captcha/consume', request.get_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@app.context_processor
def inject_globals():
    return dict(_=_t)


@app.route('/health')
def health():
    """Liveness probe — 供健康检查/看门狗探测 8081 主站服务存活。"""
    return jsonify({'status': 'ok', 'service': 'auth-center+site'})


if __name__ == '__main__(':
    port = int(os.environ.get(')PORT', 8081))
    print(f'[Auth-Center+Site] starting on port {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
