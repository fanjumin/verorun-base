#!/usr/bin/env python3
# VeroRon 维洛智能 (verorun.com / verorun.cn)
# 版权所有 (c) 2026 樊聚民 (fanjumin). All Rights Reserved.

"""Admin Panel — 管理后台 (独立端口 8084)"""
"""VeroRon v0.11.1 — Multi-agent AI Content & Commerce Hub"""

import sys, os, secrets
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'auth-center'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, Response
from models import init_db
from services.deployment_config import DeployConfig, deploy
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.cms_admin import cms_admin_bp
from routes.user import user_bp
# social_bp（社媒推广）已解耦为 plugins/social_push/，由 PluginManager 挂载
from routes.social_media import social_media_bp
from routes.footer_admin import footer_bp
from routes.header_admin import header_bp
from routes.comments import comments_bp
from routes.theme_admin import theme_bp
from routes.shop_admin import shop_bp
from routes.subscription import sub_bp
from routes.cleaner_agent import cleaner_bp
from models.cms import init_cms_tables
from routes.douyin_miniprogram import douyin_mp_bp
from routes.shop_admin import shop_bp
from routes.subscription import sub_bp
from routes.cleaner_agent import cleaner_bp
from routes.deployment_api import deploy_bp, init_deployment_tables
from routes.renewal import renew_bp
import time as _time

# ── PluginManager ──
from plugin_manager.manager import PluginManager
from plugin_manager.routes import bp as plugin_bp

# ══ Simple in-memory rate limiter for captcha consume ══
_captcha_rate_limit = {}

def _check_rate_limit(key, max_per_minute=10):
    """Sliding window rate limit. Returns True if allowed."""
    now = _time.time()
    window = 60.0
    if key not in _captcha_rate_limit:
        _captcha_rate_limit[key] = []
    _captcha_rate_limit[key] = [t for t in _captcha_rate_limit[key] if now - t < window]
    if len(_captcha_rate_limit[key]) >= max_per_minute:
        return False
    _captcha_rate_limit[key].append(now)
    return True

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32)))

@app.context_processor
def inject_deploy():
    return dict(deploy=deploy)


# ══ i18n 国际化注入 ══
from i18n import _, get_lang, get_all_translations
import os as _os

@app.context_processor
def inject_i18n():
    return {'_': _, 'LANG': get_lang(), 'translations': get_all_translations(), 'MARKET': _os.environ.get('DEPLOY_MARKET', 'cn')}

app.jinja_env.globals['_'] = _


# ══ Content Security Policy (CSP) ══
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self' ws: wss: https://cdn.jsdelivr.net; "
        "frame-ancestors 'self';"
    )
    return response

# 添加项目根目录到模板搜索路径（统一页脚 _footer.html）
import jinja2
app.jinja_loader = jinja2.ChoiceLoader([
    app.jinja_loader,
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'platform', 'templates')),
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..')),
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'health_check', 'templates')),
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'analytics', 'templates')),
    jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'ads', 'templates')),
])

app.config['TEMPLATES_AUTO_RELOAD'] = True

try:
    init_db()
except Exception as e:
    print(f'[DB] init_db warning: {e}')

# ── i18n: 启动时从 YAML 播种到 DB ──
try:
    from i18n import seed_from_yaml
    seed_from_yaml('zh-CN')
    seed_from_yaml('en')
except Exception as e:
    print(f'[i18n] seed warning: {e}')
# 注册管理后台需要的 blueprint — 包含 user_bp（管理员基本设置 /user/config）
app.register_blueprint(user_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(cms_admin_bp)
# social_bp 由 PluginManager 挂载（plugins/social_push），此处不再注册
app.register_blueprint(social_media_bp)
app.register_blueprint(footer_bp)
app.register_blueprint(header_bp)
app.register_blueprint(comments_bp)
app.register_blueprint(theme_bp)
app.register_blueprint(douyin_mp_bp)  # Douyin Mini-Program API
app.register_blueprint(shop_bp)        # 商城管理
app.register_blueprint(sub_bp)
app.register_blueprint(cleaner_bp)     # 数据清洗智能体
app.register_blueprint(renew_bp)     # 订阅续费页面
# 独立部署订阅管理API — 仅在主服务器模式注册
_EASYKAI_MODE = os.environ.get('EASYKAI_MODE', 'main')
if _EASYKAI_MODE == 'main':
    app.register_blueprint(deploy_bp)
    init_deployment_tables()
else:
    print('[Deploy] 客户端模式，跳过部署API注册')
# 自动注册 Cleaner 为矩阵子 Agent
try:
    from routes.cleaner_agent import auto_register_sub_agent
    auto_register_sub_agent()
except Exception as e:
    print(f'[CleanerAgent] ⚠️ 自动注册失败: {e}')
init_cms_tables()

# ===== PluginManager（新插件系统）=====
try:
    app.version = '0.10.4'
    app.plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins')
    pm = PluginManager(app)
    app.register_blueprint(plugin_bp)
    # 启动期挂载全部已安装插件（含 disabled）的路由，运行时由门卫按启用状态放行/拦截，
    # 从而实现后台启用/禁用插件免重启（Flask 3 运行时无法动态注册蓝图）。
    pm.mount_all_routes()

    @app.before_request
    def _plugin_gatekeeper():
        """禁用插件的路由请求返回 404，等价于插件不存在。"""
        from flask import request, abort
        if not pm.is_path_allowed(request.path):
            abort(404)

    print(f'[PluginManager] ✅ 管理 API 蓝图已注册 (/admin/plugins/*)')
except Exception as e:
    print(f'[PluginManager] ❌ 初始化失败: {e}')
    import traceback
    traceback.print_exc()

# ===== 自动化调度系统 (Cron + Workflow) =====
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'orchestrator'))
try:
    from orchestrator.routes import init_automation
    sched, worker = init_automation(app)
    app.config['AUTOMATION_SCHEDULER'] = sched
    app.config['AUTOMATION_WORKER'] = worker
    print(f'[Automation] ✅ 调度器 + Worker 池已初始化')
    print(f'[Automation] 📋 API: /admin/automation/*')
except ImportError as e:
    print(f'[Automation] ⚠️ 未安装 APScheduler: pip install apscheduler sqlalchemy')
    print(f'[Automation]    import error: {e}')
except Exception as e:
    print(f'[Automation] ❌ 初始化失败: {e}')
    import traceback
    traceback.print_exc()

# ===== Site Builder 核心模块 =====
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from site_builder import init_site_builder
    from site_builder.models import init_tables, seed_default_prompts
    init_tables()
    # 蓝图注册优先，确保路由始终可用（seed 失败不应阻断注册）
    init_site_builder(app)
    try:
        seed_default_prompts()
    except Exception as _seed_err:
        print(f'[SiteBuilder] ⚠️ 种子数据播种失败（不影响路由）: {_seed_err}')
    print(f'[SiteBuilder] ✅ 核心模块已初始化')
    print(f'[SiteBuilder] 📋 API: /admin/site-builder/*')
except Exception as e:
    print(f'[SiteBuilder] ❌ 初始化失败: {e}')
    import traceback
    traceback.print_exc()

# ===== Agent 矩阵系统 =====
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from agent_matrix.routes import init_agent_matrix
    init_agent_matrix(app)
    print(f'[Agent Matrix] ✅ 已初始化')
    print(f'[Agent Matrix] 📋 API: /admin/agent-matrix/*')
except Exception as e:
    print(f'[Agent Matrix] ❌ 初始化失败: {e}')
    import traceback
    traceback.print_exc()

PLATFORM_STATIC = os.path.join(os.path.dirname(__file__), '..', 'platform', 'static')
ADMIN_STATIC = os.path.join(os.path.dirname(__file__), 'static')
ADS_STATIC = os.path.join(os.path.dirname(__file__), '..', 'plugins', 'ads', 'static')

# ══ 独立部署：订阅过期锁定（客户端模式，仅锁定后台管理页面） ══
if os.environ.get('EASYKAI_MODE', 'main') == 'client':
    try:
        from services.license_service import LicenseService as _LicenseService
        _ls = _LicenseService()

        @app.before_request
        def _check_subscription():
            """订阅过期时，管理后台页面跳转到续费页"""
            # 只锁定 /admin 开头的页面请求，不锁定 API
            path = request.path
            if not path.startswith('/admin'):
                return None
            # 静态文件不锁定
            if path.startswith('/admin/static/'):
                return None
            # 续费页不锁定
            if path == '/admin/renew' or path.startswith('/api/subscription'):
                return None
            # 仅检查页面路由（HTML展示），API调用不锁定
            if path.startswith('/admin/') and not path.startswith('/admin/api'):
                if not _ls.check_admin_access():
                    return redirect('/admin/renew')
            return None
        print('[License] ✅ 订阅过期检查已启用（客户端模式）')
    except Exception as e:
        print(f'[License] ⚠️ 订阅检查未启用: {e}')
else:
    print('[License] 主服务器模式，跳过订阅过期检查')

@app.route('/')
def index():
    return redirect('/admin')


@app.route('/admin', strict_slashes=False)
def admin_page():
    """规范入口 — 先验证 is_admin，未登录跳 login"""
    from services.jwt_service import validate_token
    from flask import make_response
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('sso_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return redirect('/admin/login')
    resp = make_response(render_template('admin.html', sso_token=token))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    # Set sso_token as HttpOnly cookie for reliable refresh auth
    resp.set_cookie('sso_token', token, max_age=86400*7, httponly=True,
                    secure=request.is_secure, samesite='Strict', path='/')
    return resp


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/admin/login')
def admin_login_page():
    """管理员专用登录页 — 无验证码、无OAuth、支持三端（browser/desktop/mobile）"""
    # 如果已登录且有 admin 权限，直接跳到后台
    from services.jwt_service import validate_token
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.cookies.get('sso_token')
    payload = validate_token(token) if token else None
    if payload and payload.get('is_admin'):
        return redirect('/admin')
    return render_template('admin_login.html')


@app.route('/admin/login', methods=['POST'])
def admin_login_action():
    """管理员登录处理器
    支持两种方式:
      1. 密码登录 (所有客户端) — { username, password[, client_type] }
      2. 验证码登录 (桌面/移动) — { username, code[, client_type] }
         CN: 短信验证码, INTL: 邮箱验证码

    client_type: 'browser' (默认, Set-Cookie), 'desktop'/'mobile' (返回 JSON token)
    """
    import hashlib, hmac, time as _time_module, random, string
    from services.jwt_service import create_token

    data = request.get_json(force=True, silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    code = (data.get('code') or '').strip()
    client_type = (data.get('client_type') or 'browser').strip().lower()
    ip = request.remote_addr or 'unknown'

    # ── IP 限流 ──
    now = int(_time_module.time())
    attempt_key = f'admin_login_{ip}'
    attempts = _admin_login_attempts.get(attempt_key, {'count': 0, 'first': now, 'banned_until': 0})
    if attempts.get('banned_until', 0) > now:
        remaining = attempts['banned_until'] - now
        return jsonify({'success': False, 'error': f'登录被临时锁定，{remaining // 60 + 1} 分钟后重试'}), 429
    if now - attempts['first'] > 900:
        attempts = {'count': 0, 'first': now, 'banned_until': 0}

    # ── 验证码登录分支 (桌面/移动端) ──
    if code:
        if not username:
            return jsonify({'success': False, 'error': '请输入账号'}), 400

        market = os.environ.get('DEPLOY_MARKET', 'cn')
        now_iso = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        from models import get_db

        with get_db() as conn:
            if market == 'intl':
                # 邮箱验证码登录
                row = conn.execute(
                    "SELECT * FROM email_codes WHERE email=? AND code=? AND purpose='login' AND used=0 AND expires_at>? ORDER BY id DESC LIMIT 1",
                    (username, code, now_iso)
                ).fetchone()
                if not row:
                    _hit_attempt(attempts, now)
                    return jsonify({'success': False, 'error': '验证码错误或已过期'}), 400
                row = dict(row)
                if row['attempts'] >= 5:
                    return jsonify({'success': False, 'error': '尝试次数过多，请重新获取验证码'}), 400
                conn.execute('UPDATE email_codes SET used=1 WHERE id=?', (row['id'],))
                # Find user by email
                user = conn.execute('SELECT * FROM users WHERE email=? AND is_admin=1', (username,)).fetchone()
            else:
                # 短信验证码登录 — 复用 sms_codes 表
                row = conn.execute(
                    "SELECT * FROM sms_codes WHERE phone=? AND code=? AND purpose='login' AND used=0 AND expires_at>? ORDER BY id DESC LIMIT 1",
                    (username, code, now_iso)
                ).fetchone()
                if not row:
                    _hit_attempt(attempts, now)
                    return jsonify({'success': False, 'error': '验证码错误或已过期'}), 400
                row = dict(row)
                if row['attempts'] >= 5:
                    return jsonify({'success': False, 'error': '尝试次数过多，请重新获取验证码'}), 400
                conn.execute('UPDATE sms_codes SET used=1 WHERE id=?', (row['id'],))
                # Find user by phone
                user = conn.execute('SELECT * FROM users WHERE phone=? AND is_admin=1', (username,)).fetchone()

            conn.commit()

        if not user:
            attempts['count'] += 1
            _admin_login_attempts[attempt_key] = attempts
            return jsonify({'success': False, 'error': '账号不存在或非管理员账号'}), 400

        user = dict(user)
        _admin_login_attempts.pop(attempt_key, None)
        token = create_token(user['id'], phone=user.get('phone'), app_name='trademind', is_admin=True)
        _log_admin_action(user['id'], 'login_success_code', ip, f'user={username} client={client_type}')

        return _make_login_response(token, client_type)

    # ── 密码登录分支 (浏览器/所有端) ──
    if not username or not password:
        return jsonify({'success': False, 'error': '请输入账号和密码'}), 400

    from models import get_db
    with get_db() as conn:
        user = conn.execute(
            'SELECT id, username, phone, password_hash, is_admin, display_name FROM users WHERE (username=? OR phone=?) AND is_admin=1',
            (username, username)
        ).fetchone()

    if not user:
        attempts['count'] += 1
        if attempts['count'] >= 5:
            attempts['banned_until'] = now + 1800
        _admin_login_attempts[attempt_key] = attempts
        _log_admin_action(None, 'login_failed', ip, f'user={username} not_found')
        return jsonify({'success': False, 'error': '账号不存在或非管理员账号'}), 400

    stored = user['password_hash']
    if not stored:
        attempts['count'] += 1
        _admin_login_attempts[attempt_key] = attempts
        return jsonify({'success': False, 'error': '该账号未设置密码，请使用验证码登录'}), 400

    pw_ok = False
    parts = stored.split(':')
    if len(parts) == 5 and parts[0] == 'pbkdf2' and parts[1] == 'sha256':
        salt = parts[3]
        pw_hash = parts[4]
        check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        pw_ok = hmac.compare_digest(pw_hash, check)
    else:
        try:
            from werkzeug.security import check_password_hash
            pw_ok = check_password_hash(stored, password)
        except Exception:
            pass

    if not pw_ok:
        attempts['count'] += 1
        if attempts['count'] >= 5:
            attempts['banned_until'] = now + 1800
        _admin_login_attempts[attempt_key] = attempts
        _log_admin_action(user['id'], 'login_failed', ip, f'user={username} bad_password')
        return jsonify({'success': False, 'error': '密码错误'}), 400

    _admin_login_attempts.pop(attempt_key, None)
    token = create_token(user['id'], phone=user['phone'], app_name='admin', is_admin=True)
    _log_admin_action(user['id'], 'login_success', ip, f'user={username} client={client_type}')

    return _make_login_response(token, client_type)


def _make_login_response(token, client_type):
    """根据客户端类型返回不同的响应格式"""
    from flask import make_response
    resp = make_response(jsonify({'success': True, 'data': {'token': token}}))
    if client_type in ('desktop', 'mobile'):
        # 桌面/移动端：只返回 JSON，不设 cookie
        return resp
    # 浏览器：Set-Cookie
    resp.set_cookie('sso_token', token, max_age=86400*7, httponly=True,
                    secure=request.is_secure, samesite='Strict', path='/')
    return resp


def _hit_attempt(attempts, now):
    """记录一次失败尝试"""
    attempts['count'] += 1
    if attempts['count'] >= 5:
        attempts['banned_until'] = now + 1800


@app.route('/admin/login/send-code', methods=['POST'])
def admin_send_code():
    """发送桌面/移动端验证码
    CN: 短信验证码  INTL: 邮箱验证码
    """
    import hashlib, hmac, time as _time_module, random, string, secrets
    data = request.get_json(force=True, silent=True) or {}
    target = (data.get('phone') or data.get('email') or '').strip()
    ip = request.remote_addr or 'unknown'

    if not target:
        return jsonify({'success': False, 'error': '请输入手机号或邮箱'}), 400

    # IP 频控：每分钟最多 2 次
    code_key = f'code_{ip}'
    now = int(_time_module.time())
    last = _admin_login_attempts.get(code_key, 0)
    if now - last < 60:
        remaining = 60 - (now - last)
        return jsonify({'success': False, 'error': f'发送过于频繁，请 {remaining} 秒后再试'}), 429
    _admin_login_attempts[code_key] = now

    market = os.environ.get('DEPLOY_MARKET', 'cn')
    code = ''.join(secrets.choice(string.digits) for _ in range(6))
    now_iso = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expires_ts = __import__('datetime').datetime.now() + __import__('datetime').timedelta(minutes=5)
    expires_at = expires_ts.strftime('%Y-%m-%d %H:%M:%S')

    # Check user exists AND is admin
    from models import get_db
    with get_db() as conn:
        if market == 'intl':
            user = conn.execute('SELECT id FROM users WHERE email=? AND is_admin=1', (target,)).fetchone()
        else:
            user = conn.execute('SELECT id FROM users WHERE phone=? AND is_admin=1', (target,)).fetchone()

    if not user:
        return jsonify({'success': False, 'error': '该账号不存在或非管理员账号'}), 400

    if market == 'intl':
        # 邮箱验证码：存表 + 发邮件
        from models import get_db
        with get_db() as conn:
            conn.execute(
                'INSERT INTO email_codes (email, code, purpose, expires_at) VALUES (?,?,?,?)',
                (target, code, 'login', expires_at))
            conn.commit()

        try:
            from plugins.email.services import send_email
            send_email(
                to_addr=target,
                subject='VeroRun Admin Login Code',
                body_text=f'Your verification code is: {code}\n\nValid for 5 minutes.\n\nIf you did not request this, please ignore.'
            )
            print(f'[Admin] Email code sent to {target}')
        except Exception as e:
            print(f'[Admin] Email send failed: {e} (stub: {code})')
        return jsonify({'success': True, 'message': '验证码已发送到邮箱'})
    else:
        # 短信验证码：委托给 /auth/sms/send
        from models import get_db
        with get_db() as conn:
            conn.execute(
                'INSERT INTO sms_codes (phone, code, purpose, expires_at) VALUES (?,?,?,?)',
                (target, code, 'login', expires_at))
            conn.commit()

        try:
            # Try SmsPlugin first
            import flask as _flask
            _pm = _flask.current_app.extensions.get('plugin_manager')
            _sms = _pm.get_instance('sms') if (_pm and _pm.is_enabled('sms')) else None
            if _sms:
                _sms.send_sms(target, code, 'login')
            else:
                from services.sms_service import send_sms
                send_sms(target, code, 'login')
        except Exception:
            pass  # stub mode already prints
        return jsonify({'success': True, 'message': '验证码已发送'})


# ── 内存限流存储（服务重启后清空，可接受）──
_admin_login_attempts = {}


def _log_admin_action(admin_id, action, ip, detail=''):
    """记录管理员操作日志 — 异步写入，不阻塞响应"""
    import threading
    def _write():
        from models import get_db as _gdb
        try:
            with _gdb() as conn:
                conn.execute(
                    'INSERT INTO admin_logs (admin_id, action, target_type, target_id, detail, ip_address) VALUES (?,?,?,?,?,?)',
                    (admin_id or 0, action, 'admin', 'login', detail, ip)
                )
                conn.commit()
        except Exception:
            pass
    threading.Thread(target=_write, daemon=True).start()


@app.route('/reset-password')
def reset_password_page():
    return render_template('reset_password.html')


@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "admin-panel", "port": 8084})

@app.route('/admin/debug-jwt')
def debug_jwt():
    """Debug JWT: validate a token from query param"""
    import os
    from services.jwt_service import validate_token, JWT_SECRET
    token_param = request.args.get('token', '')
    result = {
        "jwt_secret_prefix": JWT_SECRET[:20] + "...",
        "jwt_secret_len": len(JWT_SECRET),
        "env_set": bool(os.environ.get('JWT_SECRET')),
        "pyjwt_version": __import__('jwt').__version__,
    }
    if token_param:
        payload = validate_token(token_param)
        result['validate_ok'] = payload is not None
        if payload:
            result['user_id'] = payload['user_id']
            result['is_admin'] = payload.get('is_admin')
            # Also simulate _require_admin DB check
            from models import get_db
            with get_db() as conn:
                user = conn.execute('SELECT id, is_admin FROM users WHERE id=?', (payload['user_id'],)).fetchone()
            result['db_user_exists'] = user is not None
            result['db_is_admin'] = bool(user and user['is_admin'])
        # Also test via actual request context
        import flask
        with flask.current_app.test_request_context(
            '/admin/dashboard',
            headers={'Authorization': f'Bearer {token_param}'}
        ):
            auth = flask.request.headers.get('Authorization', '')
            token2 = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
            result['received_token'] = token2[:20] + '...'
            result['token_match'] = token2 == token_param
            payload2 = validate_token(token2)
            result['validate_via_header_ok'] = payload2 is not None
    else:
        from services.jwt_service import create_token
        tok = create_token(7, phone='13910604299', is_admin=True)
        payload = validate_token(tok)
        result['create_validate_ok'] = payload is not None
    return jsonify(result)


@app.route('/avatar/gen/<path:seed>')
def generated_avatar(seed):
    """生成默认首字母头像 SVG（无自定义头像时使用）"""
    from services.avatar_service import generate_initials_svg
    svg = generate_initials_svg(seed)
    return Response(svg, mimetype='image/svg+xml', headers={'Cache-Control': 'public, max-age=86400'})


@app.route('/api/social-links')
def public_social_links():
    """公开 API：页脚社媒图标列表（旧表 social_links）"""
    from models import get_db
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, url, icon_url, platform, sort_order '
            'FROM social_links WHERE is_active=1 ORDER BY sort_order ASC, id ASC'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@app.route('/api/social-media')
def public_social_media():
    """公开 API：社媒图标列表（新表 social_media_links）"""
    from models import get_db
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, platform_name, icon_type, icon_value, url, hover_text '
            'FROM social_media_links WHERE is_enabled=1 ORDER BY display_order ASC, id ASC'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@app.route('/api/interests')
def public_interests():
    """公开 API：兴趣标签列表（按分类分组），支持 ?search= 模糊搜索"""
    from models import get_db
    search = request.args.get('search', '').strip()
    with get_db() as conn:
        if search:
            rows = conn.execute(
                'SELECT id, name, category, is_hot FROM interests WHERE is_active=1 AND is_hot=1 AND name LIKE ? ORDER BY category, sort_order, id',
                ('%'+search+'%',)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT id, name, category, is_hot FROM interests WHERE is_active=1 AND is_hot=1 ORDER BY category, sort_order, id'
            ).fetchall()
    grouped = {}
    for r in rows:
        d = dict(r)
        cat = d['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(d)
    return jsonify({'success': True, 'data': grouped, 'categories': list(grouped.keys())})


@app.route('/static/<path:filename>')
def static_files(filename):
    """优先从 admin/static/ 读取，回退到 platform/static/"""
    local_path = os.path.join(ADMIN_STATIC, filename)
    if os.path.isfile(local_path):
        return send_from_directory(ADMIN_STATIC, filename)
    return send_from_directory(PLATFORM_STATIC, filename)


@app.route('/static/ads/<path:filename>')
def ads_static_files(filename):
    """广告插件静态文件"""
    return send_from_directory(ADS_STATIC, filename)


# 商品图片（上传到 platform/static/products/）
_PIMG_DIR = os.path.join(PLATFORM_STATIC, 'products')
os.makedirs(_PIMG_DIR, exist_ok=True)


@app.route('/pimg/<path:filename>')
def pimg(filename):
    return send_from_directory(_PIMG_DIR, filename)


# ══ 主题系统: Jinja2 模板覆盖 + theme.css 注入 ══
THEMES_ROOT_ADMIN = os.path.join(os.path.dirname(__file__), '..', 'themes')

# 主题 slug 缓存（60秒 TTL）
_theme_slug_cache = {'value': None, 'ts': 0}

def _get_active_theme_slug_admin():
    """获取当前激活的主题 slug（带 60 秒 TTL 缓存）"""
    now = _time.perf_counter()
    if now - _theme_slug_cache['ts'] < 60:
        return _theme_slug_cache['value']
    try:
        from routes.theme_admin import get_active_theme_slug_for_site
        slug = get_active_theme_slug_for_site('admin')
    except Exception:
        slug = None
    _theme_slug_cache['value'] = slug
    _theme_slug_cache['ts'] = now
    return slug

# Jinja2 ChoiceLoader: 优先从激活主题的 templates/ 目录加载
theme_tpl_dir = None
active_slug = _get_active_theme_slug_admin()
if active_slug:
    candidate = os.path.join(THEMES_ROOT_ADMIN, active_slug, 'templates')
    if os.path.isdir(candidate):
        theme_tpl_dir = candidate
if theme_tpl_dir:
    from jinja2 import ChoiceLoader, FileSystemLoader
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(theme_tpl_dir),
        app.jinja_loader,
    ])


@app.context_processor
def inject_theme():
    """注入 theme_css_url + brand 到所有模板"""
    slug = _get_active_theme_slug_admin()
    result = {}
    if slug and slug != 'default':
        result['theme_css_url'] = '/themes/{}/theme.css'.format(slug)
    else:
        result['theme_css_url'] = None
    try:
        from services.brand_service import get_brand_settings
        result['brand'] = get_brand_settings()
    except:
        result['brand'] = None
    return result


@app.route('/themes/<slug>/<path:filename>')
def serve_theme_file(slug, filename):
    """公开访问主题静态文件"""
    import re
    safe_slug = re.sub(r'[^a-z0-9\-]', '', slug.lower())
    if safe_slug != slug:
        return 'Invalid slug', 400
    theme_static = os.path.join(THEMES_ROOT_ADMIN, slug)
    if not os.path.isdir(theme_static):
        return 'Theme not found', 404
    return send_from_directory(theme_static, filename)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8084
    app.run(host='0.0.0.0', port=port, debug=False)
