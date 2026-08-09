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
    """Extract token from request — Authorization header first, then cookie"""
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
    # CAPTCHA: disabled for SMS send (only triggered on password login after 10 fails)
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
        return api_err(_('Phone, verification code, password and username are required'))

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
        return api_err(_('Username must be 3-20 characters long'))
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]+$', username):
        return api_err(_('Username must start with a letter, only letters, digits, underscores and hyphens allowed'))
    # Check against prohibited words
    un = check_username(username)
    if not un['valid']:
        return api_err(un['error'])

    # Validate password
    from services.password_validator import validate_password
    v = validate_password(password)
    if not v['valid']:
        return api_err('；'.join(v['errors']))

    # Hash password: pbkdf2:sha256:600000:{salt}:{hash}
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    stored = f'pbkdf2:sha256:600000:{salt}:{pw_hash}'

    # Create user
    with get_db() as conn:
        # Check username uniqueness
        existing = conn.execute('SELECT id FROM users WHERE username=%s', (username,)).fetchone()
        if existing:
            return api_err(_('Username already taken'))
        # Check phone uniqueness
        existing_phone = conn.execute('SELECT id FROM users WHERE phone=%s', (phone,)).fetchone()
        if existing_phone:
            return api_err(_('This phone is already registered'))
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

    # ── Hook: user registered ──
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
    # Inject role for admin users
    role = 'user'
    if is_admin_val:
        try:
            with get_db() as conn:
                prof = conn.execute('SELECT role FROM admin_profiles WHERE user_id=%s', (user['id'],)).fetchone()
                if prof:
                    role = prof['role']
        except Exception:
            pass
    token = create_token(user['id'], phone=phone, app_name='trademind', is_admin=is_admin_val, role=role)
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
    # Set cross-subdomain SSO cookie so subdomain can authenticate
    main_domain = os.environ.get('DEPLOY_DOMAIN', '')
    _is_https = os.environ.get('DEPLOY_PROTOCOL', 'https') == 'https'
    if main_domain:
        resp.set_cookie('sso_token', token, domain='.' + main_domain,
                        path='/', max_age=604800, samesite='Lax',
                        secure=_is_https, httponly=True)
    else:
        resp.set_cookie('sso_token', token, path='/',
                        max_age=604800, samesite='Lax',
                        secure=_is_https, httponly=True)
    return resp

# =============================================
# Dynamic login methods — plugin-driven
# =============================================
def _build_password_method():
    """Core password login method — always available"""
    return {
        'type': 'password',
        'name': 'Password Login',
        'icon': 'key',
        'tab_id': 'tabPwd',
        'priority': 10,
        'fields': [
            {'name': 'account', 'type': 'text', 'placeholder': 'Username / Email / Phone',
             'autocomplete': 'username'},
            {'name': 'password', 'type': 'password', 'placeholder': 'Enter password',
             'autocomplete': 'current-password'},
        ],
        'submit_url': '/user/password/login',
        'submit_text': 'Log In',
        'has_forgot_password': True,
    }


def _build_email_register_method():
    """Core email register method — default signup channel, always available.

    Email registration is the system default (independent of SMS plugin).
    EmailPlugin acts only as the sending channel; this route lives in auth.py.
    """
    return {
        'type': 'email',
        'name': 'Email Registration',
        'icon': 'mail',
        'priority': 10,
        'fields': [
            {'name': 'email', 'type': 'email', 'placeholder': 'Enter email',
             'autocomplete': 'email'},
            {'name': 'code', 'type': 'text', 'placeholder': 'Verification code',
             'autocomplete': 'one-time-code'},
            {'name': 'password', 'type': 'password', 'placeholder': 'Set password',
             'autocomplete': 'new-password'},
            {'name': 'username', 'type': 'text', 'placeholder': 'Username',
             'autocomplete': 'username'},
        ],
        'send_url': '/auth/email/send',
        'submit_url': '/auth/email/register',
        'submit_text': 'Sign Up',
    }


@auth_bp.route('/login-methods', methods=['GET'])
def login_methods():
    """Return all available login and register methods based on enabled plugins.

    Core 'password' method is always included. Plugins register additional
    methods via get_login_methods() / get_register_methods() on their instance.
    """
    methods = [_build_password_method()]
    # Email registration is the system default — always available
    register_methods = [_build_email_register_method()]

    try:
        from flask import current_app
        pm = current_app.extensions.get('plugin_manager')
        if pm:
            for identifier, info in pm._cache.items():
                if not pm.is_enabled(identifier):
                    continue
                instance = pm.get_instance(identifier)
                if instance is None:
                    continue
                if hasattr(instance, 'get_login_methods'):
                    extra = instance.get_login_methods()
                    if extra:
                        methods.extend(extra)
                if hasattr(instance, 'get_register_methods'):
                    extra = instance.get_register_methods()
                    if extra:
                        register_methods.extend(extra)
    except Exception:
        pass

    # Sort: primary methods (is_third_party=False) first by priority,
    # then third-party methods by priority
    primary = [m for m in methods if not m.get('is_third_party')]
    third_party = [m for m in methods if m.get('is_third_party')]
    primary.sort(key=lambda m: m.get('priority', 50))
    third_party.sort(key=lambda m: m.get('priority', 50))
    register_methods.sort(key=lambda m: m.get('priority', 50))

    return api_ok({
        'methods': primary + third_party,
        'register_methods': register_methods,
    })


# ---------------------------------------------------------------------------
# The following OAuth routes (wechat/qr, wechat/callback, wechat/login,
# douyin/qr, douyin/callback, oauth/providers, oauth/*/login, oauth/*/callback,
# _get_site_domain, _get_cookie_domain) have been moved to plugins/oauth_config/
# and are loaded by Auth_server.py via try/except.
# /auth/wechat/login for WeChat Mini Program is now provided by plugin oauth_bp.
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
                             is_admin=payload.get('is_admin', False),
                             role=payload.get('role', 'user'))
    return api_ok({'token': new_token})


# =============================================
# Email verification endpoints
# =============================================
@auth_bp.route('/email/send', methods=['POST'])
def email_send_code():
    """Send verification code to email.

    Purposes:
    - 'email_verify': requires JWT auth (binding flow, logged-in user)
    - 'register':     no JWT required (signup flow, anonymous user)
    - 'login':        no JWT required (email login flow, anonymous user)
    """
    data = request.get_json() or {}
    purpose = (data.get('purpose') or 'email_verify').strip()
    email = data.get('email', '').strip()
    if not email or '@' not in email:
        return api_err('Please enter a valid email address')

    # Binding flow requires JWT; register/login flows are anonymous
    if purpose == 'email_verify':
        token = _get_token_from_request()
        payload = validate_token(token) if token else None
        if not payload:
            return api_err('Please login first', 401)

    # Rate limit: 60s cooldown
    if not check_rate_limit(email):
        return api_err('Too many requests, please retry later')

    # For register purpose: reject if email already registered
    if purpose == 'register':
        with get_db() as conn:
            exist = conn.execute('SELECT id FROM users WHERE email=%s', (email,)).fetchone()
            if exist:
                return api_err('This email is already registered')

    code = generate_code()
    with get_db() as conn:
        expires_at = (__import__('datetime').datetime.now() +
                      __import__('datetime').timedelta(minutes=10)).isoformat()
        conn.execute('INSERT INTO sms_codes (phone, code, purpose, expires_at) VALUES (%s,%s,%s,%s)',
                     (email, code, purpose, expires_at))
        conn.commit()
    from plugins.email.services import send_email
    subject = _('VeroRun Email Verification Code')
    body_text = _('Your verification code is: {code}, valid for 10 minutes. If this was not you, please ignore.').format(code=code)
    body_html = '<h3>{title}</h3><p>Your verification code is: <b style="font-size:20px;color:#6366f1">{code}</b></p><p>{footer}</p>'.format(
        title=_('Email Verification'),
        code=code,
        footer=_('Valid for 10 minutes. If this was not you, please ignore.')
    )
    success, msg = send_email(email, subject, body_text, body_html)
    if not success:
        return api_err('Email send failed: ' + msg)
    return api_ok({'sent': True})


@auth_bp.route('/email/register', methods=['POST'])
def email_register():
    """Register with email + verification code + password + username.

    Mirrors /auth/sms/register but uses email instead of phone. Email is
    verified at registration time (email_verified=1 on insert).
    """
    import re, secrets
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    password = data.get('password', '')
    username = data.get('username', '').strip()
    display_name = data.get('display_name', '').strip()

    if not email or not code or not password or not username:
        return api_err(_('Email, verification code, password and username are required'))

    # Verify email code (purpose='register')
    now = now_iso()
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM sms_codes WHERE phone=%s AND code=%s AND purpose=%s AND used=0 AND expires_at>%s ORDER BY id DESC LIMIT 1',
            (email, code, 'register', now))
        code_row = row.fetchone()
        if not code_row:
            return api_err(_('Invalid or expired verification code'))
        code_row = dict(code_row)
        if code_row['attempts'] >= 5:
            return api_err(_('Too many attempts, please request a new code'))
        conn.execute('UPDATE sms_codes SET used=1 WHERE id=%s', (code_row['id'],))

    # Validate display_name (sanitize first)
    from services.name_validator import check_username, check_display_name, sanitize_name
    display_name = sanitize_name(display_name) if display_name else ''
    if display_name:
        dn = check_display_name(display_name)
        if not dn['valid']:
            return api_err(_('Display name') + dn['error'])

    # Validate username (3-20 chars, alphanumeric + _ + -, starts with letter)
    if len(username) < 3 or len(username) > 20:
        return api_err(_('Username must be 3-20 characters long'))
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]+$', username):
        return api_err(_('Username must start with a letter, only letters, digits, underscores and hyphens allowed'))
    un = check_username(username)
    if not un['valid']:
        return api_err(un['error'])

    # Validate password
    from services.password_validator import validate_password
    v = validate_password(password)
    if not v['valid']:
        return api_err('；'.join(v['errors']))

    # Hash password: pbkdf2:sha256:600000:{salt}:{hash}
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    stored = f'pbkdf2:sha256:600000:{salt}:{pw_hash}'

    # Create user
    with get_db() as conn:
        # Check email uniqueness
        existing_email = conn.execute('SELECT id FROM users WHERE email=%s', (email,)).fetchone()
        if existing_email:
            return api_err(_('This email is already registered'))
        # Check username uniqueness
        existing = conn.execute('SELECT id FROM users WHERE username=%s', (username,)).fetchone()
        if existing:
            return api_err(_('Username already taken'))
        user_id = conn.execute(
            'INSERT INTO users (email, username, display_name, password_hash, phone_verified, email_verified, last_login) VALUES (%s,%s,%s,%s,0,1,%s) RETURNING id',
            (email, username, display_name or username, stored, now)).fetchone()['id']
        # Auto-create free-tier authorization
        conn.execute(
            'INSERT INTO app_authorizations (user_id, app_name, tier) VALUES (%s,%s,%s) ON CONFLICT (user_id, app_name) DO NOTHING',
            (user_id, 'trademind', 'free'))
        conn.commit()

    token = create_token(user_id, phone=None, app_name='trademind', is_admin=0)

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

    # ── Hook: user registered ──
    try:
        from plugin_manager.injectors import fire_hook
        fire_hook('user/registered', user_id=user_id, username=username, email=email)
    except Exception:
        pass

    return api_ok({
        'token': token,
        'user': {
            'id': user_id,
            'email': email,
            'username': username,
            'display_name': display_name or username,
        },
    })


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
# Logout — clear HttpOnly cookie + deactivate current session
# =============================================
@auth_bp.route('/logout', methods=['POST'])
def auth_logout():
    """Logout: mark current session inactive + clear cookie"""
    token = _get_token_from_request()
    # Mark current session as inactive
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with get_db() as conn:
            conn.execute("UPDATE user_sessions SET is_current=0 WHERE token_hash=%s", (token_hash,))
            conn.commit()
    # Clear all related cookies
    cd_val = _get_cookie_domain()
    resp = jsonify({'success': True})
    for cookie_name in ('sso_token', 'tm_token', 'token'):
        if cd_val:
            resp.set_cookie(cookie_name, '', domain=cd_val, path='/', max_age=0)
        else:
            resp.set_cookie(cookie_name, '', path='/', max_age=0)
    return resp
