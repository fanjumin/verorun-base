#!/usr/bin/env python3
"""Auth Routes — phone SMS login, WeChat OAuth, JWT token management"""
import sys, os, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from flask import Blueprint, request, jsonify, make_response
from models import get_db, init_db, now_iso
from services.jwt_service import create_token, validate_token
# SMS functions — delegates to SmsPlugin if available, fallback to sms_service
try:
    import flask as _flask
    _pm = _flask.current_app.extensions.get('plugin_manager')
    _sms = _pm.get_instance('sms') if (_pm and _pm.is_enabled('sms')) else None
    if _sms:
        generate_code = _sms.generate_code
        send_sms = _sms.send_sms
        check_rate_limit = _sms.check_rate_limit
        validate_phone = _sms.validate_phone
    else:
        raise RuntimeError('plugin not available')
except Exception:
    from services.sms_service import generate_code, send_sms, check_rate_limit, validate_phone
import hashlib
from i18n import _

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def api_ok(data=None):
    return jsonify({'success': True, 'data': data})


def api_err(msg, code=400):
    return jsonify({'success': False, 'error': msg}), code


def _get_token_from_request():
    """从请求中提取 token — 优先 Authorization header，其次 cookie"""
    auth = request.headers.get('Authorization', '')
    if auth and auth.startswith('Bearer '):
        return auth[7:]
    return request.cookies.get('sso_token') or request.cookies.get('tm_token') or None


# =============================================
# SMS: Send verification code
# =============================================
@auth_bp.route('/sms/send', methods=['POST'])
def sms_send():
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    purpose = data.get('purpose', 'login')
    country_code = data.get('country_code', '')
    valid, normalized_phone, phone_err = validate_phone(phone, country_code)
    if not valid:
        return api_err(phone_err or 'Please enter a valid phone number')
    phone = normalized_phone
    # CAPTCHA: skip for logged-in users resetting password (already authenticated via JWT)
    need_captcha = True
    if purpose == 'modify_password':
        token = _get_token_from_request()
        if token and validate_token(token):
            need_captcha = False
    if need_captcha:
        captcha_id = data.get('captcha_id', '')
        if not captcha_id:
            return api_err('Please complete the CAPTCHA challenge')
        try:
            import urllib.request, json as _json
            req = urllib.request.Request('http://127.0.0.1:8084/api/captcha/consume',
                data=_json.dumps({'token': captcha_id, 'drag_distance': 0, 'drag_trace': []}).encode(),
                headers={'Content-Type': 'application/json'})
            resp = urllib.request.urlopen(req, timeout=3)
            result = _json.loads(resp.read().decode())
            if not result.get('valid'):
                return api_err(_('CAPTCHA expired or incomplete, please retry'), 400)
        except Exception:
            return api_err(_('Verification service error, please retry later'), 500)
    if not check_rate_limit(phone):
        return api_err(_('Too many requests, please retry in one hour'))
    code = generate_code()
    with get_db() as conn:
        expires_at = (__import__('datetime').datetime.now() +
                      __import__('datetime').timedelta(minutes=10)).isoformat()
        cur = conn.execute('INSERT INTO sms_codes (phone, code, purpose, expires_at) VALUES (%s,%s,%s,%s)',
                     (phone, code, purpose, expires_at))
        conn.commit()
    result = send_sms(phone, code, purpose)
    if not result.get('success'):
        return api_err('SMS send failed: ' + result.get('message', result.get('error', 'unknown error')))
    # In stub mode, return code for testing
    stub_info = {'code': code} if result.get('provider') == 'stub' else {}
    return api_ok({'sent': True, 'provider': result.get('provider', 'unknown'), **stub_info})


# =============================================
# Username availability check
# =============================================
@auth_bp.route('/username/check', methods=['POST'])
def username_check():
    """Check if a username is available"""
    import re
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    if not username:
        return api_err('Please enter a username')
    if len(username) < 3 or len(username) > 20:
        return api_ok({'available': False, 'error': 'Username must be 3-20 characters long'})
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]+$', username):
        return api_ok({'available': False, 'error': 'Username must start with a letter, only letters, digits, underscores and hyphens allowed'})
    # Check against prohibited words
    from services.name_validator import check_username
    un = check_username(username)
    if not un['valid']:
        return api_ok({'available': False, 'error': un['error']})
    with get_db() as conn:
        row = conn.execute('SELECT id FROM users WHERE username=%s', (username,)).fetchone()
    return api_ok({'available': row is None})


# =============================================
# SMS: Register with password + username
# =============================================
@auth_bp.route('/sms/register', methods=['POST'])
def sms_register():
    """Full registration flow: verify captcha + SMS code, then create user with password + username"""
    import re, secrets
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()
    password = data.get('password', '').strip()
    username = data.get('username', '').strip()
    display_name = data.get('display_name', '').strip()

    if not phone or not code or not password or not username:
        return api_err('Phone, verification code, password and username are required')

    # Verify SMS code (purpose='register')
    now = now_iso()
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM sms_codes WHERE phone=%s AND code=%s AND purpose=%s AND used=0 AND expires_at>%s ORDER BY id DESC LIMIT 1',
            (phone, code, 'register', now))
        sms_row = row.fetchone()
        if not sms_row:
            return api_err(_('Invalid or expired verification code'))
        sms_row = dict(sms_row)
        if sms_row['attempts'] >= 5:
            return api_err(_('Too many attempts, please request a new code'))
        conn.execute('UPDATE sms_codes SET used=1 WHERE id=%s', (sms_row['id'],))

    # Validate display_name (sanitize first)
    from services.name_validator import check_username, check_display_name, sanitize_name
    display_name = sanitize_name(display_name) if display_name else ''
    if display_name:
        dn = check_display_name(display_name)
        if not dn['valid']:
            return api_err(_('Display name') + dn['error'])

    # Validate username (3-20 chars, alphanumeric + _ + -, starts with letter)
    if len(username) < 3 or len(username) > 20:
        return api_err('Username must be 3-20 characters long')
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]+$', username):
        return api_err('Username must start with a letter, only letters, digits, underscores and hyphens allowed')
    # Check against prohibited words (国家相关规定)
    un = check_username(username)
    if not un['valid']:
        return api_err(un['error'])

    # Validate password
    from services.password_validator import validate_password
    v = validate_password(password)
    if not v['valid']:
        return api_err('；'.join(v['errors']))

    # Hash password: pbkdf2:sha256:100000:{salt}:{hash}
    salt = secrets.token_hex(8)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    stored = f'pbkdf2:sha256:100000:{salt}:{pw_hash}'

    # Create user
    with get_db() as conn:
        # Check username uniqueness
        existing = conn.execute('SELECT id FROM users WHERE username=%s', (username,)).fetchone()
        if existing:
            return api_err(_('Username already taken'))
        # Check phone uniqueness
        existing_phone = conn.execute('SELECT id FROM users WHERE phone=%s', (phone,)).fetchone()
        if existing_phone:
            return api_err('This phone is already registered')
        user_id = conn.execute(
            'INSERT INTO users (phone, username, display_name, password_hash, phone_verified, email_verified, last_login) VALUES (%s,%s,%s,%s,1,0,%s) RETURNING id',
            (phone, username, display_name or username, stored, now)).fetchone()['id']
        # Auto-create free-tier authorization
        conn.execute(
            'INSERT INTO app_authorizations (user_id, app_name, tier) VALUES (%s,%s,%s) ON CONFLICT (user_id, app_name) DO NOTHING',
            (user_id, 'trademind', 'free'))
        conn.commit()

    token = create_token(user_id, phone=phone, app_name='trademind', is_admin=0)

    # Record user session
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr or ''
    device_type = 'mobile' if ('Mobile' in user_agent or 'Android' in user_agent) else 'desktop'
    device_name = user_agent[:256] if user_agent else ''
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_sessions (user_id, token_hash, device_name, device_type, ip_address, user_agent, is_current, created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,1, NOW())",
            (user_id, token_hash, device_name, device_type, ip_address, user_agent))
        conn.commit()

    # ── 钩子: 用户注册完成 ──
    try:
        from plugin_manager.injectors import fire_hook
        fire_hook('user/registered', user_id=user_id, username=username, phone=phone)
    except Exception:
        pass

    return api_ok({
        'token': token,
        'user': {
            'id': user_id,
            'phone': phone,
            'username': username,
            'display_name': display_name or username,
        },
    })


# =============================================
# SMS: Verify code & login/register
# =============================================
@auth_bp.route('/sms/login', methods=['POST'])
def sms_login():
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()
    if not phone or not code:
        return api_err('Phone and verification code are required')
    now = now_iso()
    with get_db() as conn:
        cur = conn.execute(
            'SELECT * FROM sms_codes WHERE phone=%s AND code=%s AND purpose=%s AND used=0 AND expires_at>%s ORDER BY id DESC LIMIT 1',
            (phone, code, 'login', now))
        row = cur.fetchone()
        if not row:
            return api_err('Invalid or expired verification code')
        row = dict(row)
        if row['attempts'] >= 5:
            return api_err('Too many attempts, please request a new code')
        conn.execute('UPDATE sms_codes SET used=1 WHERE id=%s', (row['id'],))
        # Find or create user
        cur = conn.execute('SELECT * FROM users WHERE phone=%s', (phone,))
        user = cur.fetchone()
        if user:
            user = dict(user)
            conn.execute('UPDATE users SET last_login=%s WHERE id=%s', (now, user['id']))
        else:
            user_id = conn.execute(
                'INSERT INTO users (phone, phone_verified, last_login) VALUES (%s,1,%s) RETURNING id',
                (phone, now)).fetchone()['id']
            # Auto-create free-tier authorization for trademind
            conn.execute(
                'INSERT INTO app_authorizations (user_id, app_name, tier) VALUES (%s,%s,%s) ON CONFLICT (user_id, app_name) DO NOTHING',
                (user_id, 'trademind', 'free'))
            user = {'id': user_id, 'phone': phone}
        conn.commit()
    # user may be sqlite3.Row or dict
    is_admin_val = user['is_admin'] if isinstance(user, dict) else (user['is_admin'] if 'is_admin' in user.keys() else 0)
    nickname_val = user.get('display_name', '') if isinstance(user, dict) else (user['display_name'] if user['display_name'] else '')
    token = create_token(user['id'], phone=phone, app_name='trademind', is_admin=is_admin_val)
    # Record user session
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    ua = request.headers.get('User-Agent', '')
    ip_addr = request.remote_addr or ''
    dev_type = 'mobile' if ('Mobile' in ua or 'Android' in ua) else 'desktop'
    dev_name = ua[:256] if ua else ''
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_sessions (user_id, token_hash, device_name, device_type, ip_address, user_agent, is_current, created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,1, NOW())",
            (user['id'], token_hash, dev_name, dev_type, ip_addr, ua))
        conn.commit()
    resp = make_response(jsonify({'success': True, 'data': {
        'token': token,
        'user': {'id': user['id'], 'phone': phone, 'nickname': nickname_val},
    }}))
    # Set cross-subdomain SSO cookie so platform.easykai.cn can authenticate
    main_domain = os.environ.get('DEPLOY_DOMAIN', '')
    if main_domain:
        resp.set_cookie('sso_token', token, domain='.' + main_domain,
                        path='/', max_age=604800, samesite='Lax',
                        secure=True, httponly=True)
    return resp

# ---------------------------------------------------------------------------
# 以下 OAuth 路由（wechat/qr, wechat/callback, wechat/login, douyin/qr,
# douyin/callback, oauth/providers, oauth/*/login, oauth/*/callback,
# _get_site_domain, _get_cookie_domain）已搬迁至插件 plugins/oauth_config/
# 由 Auth_server.py 通过 try/except 加载。
# 用于微信小程序的 /auth/wechat/login 现由插件 oauth_bp 提供。
# ---------------------------------------------------------------------------


# =============================================
@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json() or {}
    old_token = data.get('token', '')
    payload = validate_token(old_token)
    if not payload:
        return api_err('Invalid or expired token', 401)
    new_token = create_token(payload['user_id'], phone=payload.get('phone'),
                             app_name=payload.get('app_name', 'trademind'),
                             is_admin=payload.get('is_admin', False))
    return api_ok({'token': new_token})


# =============================================
# Email verification endpoints
# =============================================
@auth_bp.route('/email/send', methods=['POST'])
def email_send_code():
    """Send verification code to email. Requires JWT auth."""
    token = _get_token_from_request()
    payload = validate_token(token) if token else None
    if not payload:
        return api_err('Please login first', 401)
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email or '@' not in email:
        return api_err('Please enter a valid email address')
    # Rate limit: 60s cooldown
    if not check_rate_limit(email):
        return api_err('Too many requests, please retry later')
    code = generate_code()
    with get_db() as conn:
        expires_at = (__import__('datetime').datetime.now() +
                      __import__('datetime').timedelta(minutes=10)).isoformat()
        conn.execute('INSERT INTO sms_codes (phone, code, purpose, expires_at) VALUES (%s,%s,%s,%s)',
                     (email, code, 'email_verify', expires_at))
        conn.commit()
    from plugins.email.services import send_email
    subject = _'VeroRun Email Verification Code'
    body_text = f'您的验证码是：{code}，10分钟内有效。如非本人操作，请忽略。'
    body_html = f'<h3>邮箱验证码</h3><p>您的验证码是：<b style="font-size:20px;color:#6366f1">{code}</b></p><p>10分钟内有效。如非本人操作，请忽略。</p>'
    success, msg = send_email(email, subject, body_text, body_html)
    if not success:
        return api_err('Email send failed: ' + msg)
    return api_ok({'sent': True})


@auth_bp.route('/email/verify', methods=['POST'])
def email_verify():
    """Verify email code and update user's email."""
    token = _get_token_from_request()
    payload = validate_token(token) if token else None
    if not payload:
        return api_err('Please login first', 401)
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    if not email or not code:
        return api_err('Email and verification code are required')
    with get_db() as conn:
        row = conn.execute(
            'SELECT code, expires_at FROM sms_codes WHERE phone=%s AND purpose=%s ORDER BY id DESC LIMIT 1',
            (email, 'email_verify')
        ).fetchone()
        if not row:
            return api_err('Please send verification code first')
        if row['expires_at'] < now_iso():
            return api_err('Verification code expired, please resend')
        if row['code'] != code:
            return api_err('Invalid verification code')
        # Check if email already used by another user
        exist = conn.execute('SELECT id FROM users WHERE email=%s AND id!=%s', (email, payload['user_id'])).fetchone()
        if exist:
            return api_err('This email is already in use')
        conn.execute('UPDATE users SET email=%s, email_verified=1 WHERE id=%s', (email, payload['user_id']))
        conn.commit()
    return api_ok({'email': email, 'email_verified': True})


# =============================================
# Logout — 清除 HttpOnly cookie + 下线当前 session
# =============================================
@auth_bp.route('/logout', methods=['POST'])
def auth_logout():
    """退出登录：标记当前 session 下线 + 清除 cookie"""
    token = _get_token_from_request()
    # 标记当前 session 为不活跃
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with get_db() as conn:
            conn.execute("UPDATE user_sessions SET is_current=0 WHERE token_hash=%s", (token_hash,))
            conn.commit()
    # 清除所有相关 cookie
    cd_val = _get_cookie_domain()
    resp = jsonify({'success': True})
    for cookie_name in ('sso_token', 'tm_token', 'token'):
        if cd_val:
            resp.set_cookie(cookie_name, '', domain=cd_val, path='/', max_age=0)
        else:
            resp.set_cookie(cookie_name, '', path='/', max_age=0)
    return resp
