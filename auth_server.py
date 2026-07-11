#!/usr/bin/env python3
"""auth-center standalone server (port 8081) - login/OAuth/user/CMS/payment + Main Site"""
import sys, os

# Load .env BEFORE any auth imports (dotnet may be optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR in sys.path:
    sys.path.remove(_SCRIPT_DIR)
if '' in sys.path:
    sys.path.remove('')
AUTH_DIR = os.path.join(_SCRIPT_DIR, 'auth-center')
sys.path.insert(0, AUTH_DIR)
sys.path.append(_SCRIPT_DIR)

from flask import Flask, render_template, make_response, request
from auth_blueprint import register_auth

app = Flask(__name__)

# 主站(www)模板位于 site/templates 与 platform/templates，非本文件同级 templates，
# 因此显式挂载到 jinja loader，避免 public_home.html 等模板 TemplateNotFound。
import jinja2
app.jinja_loader = jinja2.ChoiceLoader([
    jinja2.FileSystemLoader(os.path.join(_SCRIPT_DIR, 'site', 'templates')),
    jinja2.FileSystemLoader(os.path.join(_SCRIPT_DIR, 'platform', 'templates')),
    app.jinja_loader,
])

app.secret_key = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'

# ══ Try to load i18n ══
try:
    from i18n import _ as _t
except Exception:
    _t = lambda s: s

register_auth(app)

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
    resp = make_response(render_template('public_home.html', LANG='zh-CN', site_plans=site_plans))
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
    return render_template('public_home.html', LANG='zh-CN', site_plans=site_plans)


@app.route('/features')
def site_features():
    site_plans = []
    try:
        from services.subscription_service import get_all_plans
        site_plans = get_all_plans() or []
    except Exception:
        pass
    return render_template('public_home.html', LANG='zh-CN', site_plans=site_plans)


@app.route('/contact')
def site_contact():
    site_plans = []
    try:
        from services.subscription_service import get_all_plans
        site_plans = get_all_plans() or []
    except Exception:
        pass
    return render_template('public_home.html', LANG='zh-CN', site_plans=site_plans)


@app.route('/login')
def login_page():
    """Unified SSO login page."""
    return render_template('login.html', LANG='zh-CN')


@app.context_processor
def inject_globals():
    return dict(_=_t)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    print(f'[Auth-Center+Site] starting on port {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
