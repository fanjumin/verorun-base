#!/usr/bin/env python3
"""Auth Routes — phone SMS login, WeChat OAuth, JWT token management"""
import sys, os, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from flask import Blueprint, request, jsonify, make_response
from models import get_db, init_db, now_iso
from services.jwt_service import create_token, validate_token
from services.sms_service import generate_code, send_sms, check_rate_limit, validate_phone
from services.wechat_service import get_openid_by_code, get_user_info, get_qr_url, is_stub
from services.douyin_service import get_access_token as dy_get_token, get_user_info as dy_get_user, get_oauth_url as dy_get_url, is_stub as dy_is_stub, _get_config as dy_get_config
import hashlib, hmac, time
from i18n import _
from services.deployment_config import deploy

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
        cur = conn.execute('INSERT INTO sms_codes (phone, code, purpose, expires_at) VALUES (?,?,?,?)',
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
        row = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
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
            'SELECT * FROM sms_codes WHERE phone=? AND code=? AND purpose=? AND used=0 AND expires_at>? ORDER BY id DESC LIMIT 1',
            (phone, code, 'register', now))
        sms_row = row.fetchone()
        if not sms_row:
            return api_err(_('Invalid or expired verification code'))
        sms_row = dict(sms_row)
        if sms_row['attempts'] >= 5:
            return api_err(_('Too many attempts, please request a new code'))
        conn.execute('UPDATE sms_codes SET used=1 WHERE id=?', (sms_row['id'],))

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
        existing = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if existing:
            return api_err(_('Username already taken'))
        # Check phone uniqueness
        existing_phone = conn.execute('SELECT id FROM users WHERE phone=?', (phone,)).fetchone()
        if existing_phone:
            return api_err('This phone is already registered')
        cur = conn.execute(
            'INSERT INTO users (phone, username, display_name, password_hash, phone_verified, email_verified, last_login) VALUES (?,?,?,?,1,0,?)',
            (phone, username, display_name or username, stored, now))
        user_id = cur.lastrowid
        # Auto-create free-tier authorization
        conn.execute(
            'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
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
            "VALUES (?,?,?,?,?,?,1, datetime('now'))",
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
            'SELECT * FROM sms_codes WHERE phone=? AND code=? AND purpose=? AND used=0 AND expires_at>? ORDER BY id DESC LIMIT 1',
            (phone, code, 'login', now))
        row = cur.fetchone()
        if not row:
            return api_err('Invalid or expired verification code')
        row = dict(row)
        if row['attempts'] >= 5:
            return api_err('Too many attempts, please request a new code')
        conn.execute('UPDATE sms_codes SET used=1 WHERE id=?', (row['id'],))
        # Find or create user
        cur = conn.execute('SELECT * FROM users WHERE phone=?', (phone,))
        user = cur.fetchone()
        if user:
            user = dict(user)
            conn.execute('UPDATE users SET last_login=? WHERE id=?', (now, user['id']))
        else:
            cur = conn.execute(
                'INSERT INTO users (phone, phone_verified, last_login) VALUES (?,1,?)',
                (phone, now))
            user_id = cur.lastrowid
            # Auto-create free-tier authorization for trademind
            conn.execute(
                'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
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
            "VALUES (?,?,?,?,?,?,1, datetime('now'))",
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


# =============================================
# WeChat login
# =============================================
@auth_bp.route('/wechat/login', methods=['POST'])
def wechat_login():
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    if not code:
        return api_err('Missing WeChat authorization code')
    wx = get_openid_by_code(code)
    if 'error' in wx:
        return api_err('WeChat login failed: ' + wx['error'])
    openid = wx['openid']
    now = now_iso()
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM users WHERE wechat_openid=?', (openid,))
        user = cur.fetchone()
        if user:
            user = dict(user)
            conn.execute('UPDATE users SET last_login=? WHERE id=?', (now, user['id']))
        else:
            cur = conn.execute(
                'INSERT INTO users (wechat_openid, wechat_unionid, last_login) VALUES (?,?,?)',
                (openid, wx.get('unionid', ''), now))
            user_id = cur.lastrowid
            conn.execute(
                'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
                (user_id, 'trademind', 'free'))
            user = {'id': user_id, 'wechat_openid': openid}
        conn.commit()
    token = create_token(user['id'], app_name='trademind')
    return api_ok({'token': token, 'user': {'id': user['id']}})


# =============================================
# WeChat QR login — redirect to QR code page
# =============================================
@auth_bp.route('/wechat/qr', methods=['GET'])
def wechat_qr():
    """Show WeChat QR login page (or redirect to WeChat OAuth in production)"""
    from flask import render_template, redirect
    if not is_stub():
        qr_url = get_qr_url()
        if qr_url:
            return redirect(qr_url)
    return render_template('wechat_login.html')


# =============================================
# WeChat callback — after user scans QR code
# =============================================
@auth_bp.route('/wechat/callback', methods=['GET'])
def wechat_callback():
    from flask import redirect as flask_redirect
    from services.jwt_service import create_token
    domain = _get_site_domain()
    code = request.args.get('code', '')
    state = request.args.get('state', 'login')
    if not code:
        return flask_redirect(f'https://{domain}/wechat-login?error=Missing authorization code')
    wx = get_openid_by_code(code)
    if 'error' in wx:
        return flask_redirect(f'https://{domain}/wechat-login?error=' + wx['error'])
    openid = wx['openid']
    access_token = wx.get('access_token', '')
    now = now_iso()
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM users WHERE wechat_openid=?', (openid,))
        user = cur.fetchone()
        if user:
            user = dict(user)
            # Update user info
            conn.execute('UPDATE users SET last_login=? WHERE id=?', (now, user['id']))
            if access_token and user.get('wechat_unionid'):
                try:
                    info = get_user_info(openid, access_token)
                    if 'nickname' in info and info['nickname']:
                        conn.execute('UPDATE users SET wechat_nickname=?, avatar_url=? WHERE id=?',
                                     (info['nickname'], info.get('avatar', ''), user['id']))
                except:
                    pass
        else:
            # Try to get user info
            nickname = ''
            avatar = ''
            unionid = wx.get('unionid', '')
            try:
                info = get_user_info(openid, access_token)
                if 'nickname' in info:
                    nickname = info.get('nickname', '')
                    avatar = info.get('avatar', '')
                    unionid = info.get('unionid', unionid)
            except:
                pass
            cur = conn.execute(
                'INSERT INTO users (wechat_openid, wechat_unionid, wechat_nickname, avatar_url, last_login) '
                'VALUES (?,?,?,?,?)',
                (openid, unionid, nickname, avatar, now))
            user_id = cur.lastrowid
            # Auto-create free-tier authorization
            conn.execute(
                'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
                (user_id, 'trademind', 'free'))
            user = {'id': user_id, 'wechat_openid': openid, 'wechat_nickname': nickname}
        conn.commit()
    token = create_token(user['id'], app_name='trademind')
    # 跳转到主域名首页，传递 token 参数
    main_domain = os.environ.get('DEPLOY_DOMAIN', '')
    return flask_redirect(f'https://{main_domain}/?token={token}')

# =============================================
# Douyin QR login — redirect to Douyin OAuth
# =============================================
def _get_site_domain():
    """从请求中提取域名（多租户支持），统一去掉 www. 前缀"""
    host = request.headers.get('Host', '')
    domain = host.split(':')[0]  # 去掉端口
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def _get_cookie_domain():
    """获取跨子域共享的 cookie domain（带前导点），用于 Set-Cookie。
    优先从 brand_settings.site_domain 获取（可后台配置），
    失败时从当前请求 Host 推导。
    """
    try:
        from services.brand_service import get_brand_settings
        brand = get_brand_settings()
        if brand and brand.get('site_domain', '').strip():
            return '.' + brand['site_domain'].strip().lower()
    except Exception:
        pass
    # fallback: 从当前域名去掉 www 后加前导点
    domain = _get_site_domain()
    if domain:
        return '.' + domain
    return None


@auth_bp.route('/douyin/qr', methods=['GET'])
def douyin_qr():
    """Show Douyin QR login page (or redirect to Douyin OAuth in production)"""
    from flask import render_template, redirect
    domain = _get_site_domain()
    redirect_to = request.args.get('redirect', '') or request.referrer or '/'
    state = f'login:{redirect_to}'
    if not dy_is_stub(domain):
        oauth_url = dy_get_url(site_domain=domain, state=state)
        if oauth_url:
            return redirect(oauth_url)
    return render_template('douyin_login.html', redirect_to=redirect_to)


# =============================================
# Douyin callback — after user scans QR code
# =============================================
@auth_bp.route('/douyin/callback', methods=['GET'])
def douyin_callback():
    from flask import redirect as flask_redirect, make_response
    from services.jwt_service import create_token
    domain = _get_site_domain()
    code = request.args.get('code', '')
    state = request.args.get('state', '')
    print(f'[Douyin callback] domain={domain} code={code[:10] if code else "empty"} state={state[:30] if state else "empty"}')
    # 从 state 提取跳转目标: login:/redirect/path
    redirect_to = '/'
    if ':' in state:
        parts = state.split(':', 1)
        if len(parts) == 2 and parts[0] == 'login':
            redirect_to = parts[1]
    # 不跳回认证页
    if redirect_to in ('/login', '/register', '/reset-password', '/douyin-login', '/wechat-login'):
        redirect_to = '/'
    if not code:
        return flask_redirect(f'https://{domain}/douyin-login?error=Missing authorization code')
    
    if dy_is_stub(domain) and code.startswith('stub_'):
        # Stub mode: simulate success
        open_id = 'stub_open_' + code[5:13]
        nickname = '抖音用户_' + open_id[-4:]
        avatar = ''
    else:
        token_data = dy_get_token(code, site_domain=domain)
        if 'error' in token_data:
            msg = token_data['error']
            print('[Douyin callback] token ERROR:', msg)
            return flask_redirect(f'https://{domain}/douyin-login?error={msg}')
        open_id = token_data['open_id']
        print('[Douyin callback] token OK open_id:', open_id[:10] if open_id else 'none')
        # Get user info
        info = dy_get_user(open_id, token_data['access_token'], site_domain=domain)
        nickname = info.get('nickname', '') if 'error' not in info else ''
        avatar = info.get('avatar', '') if 'error' not in info else ''
    
    now = now_iso()
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM users WHERE douyin_open_id=?', (open_id,))
        user = cur.fetchone()
        if user:
            user = dict(user)
            conn.execute('UPDATE users SET last_login=?, douyin_nickname=?, douyin_avatar=? WHERE id=?',
                         (now, nickname, avatar, user['id']))
        else:
            cur = conn.execute(
                'INSERT INTO users (douyin_open_id, douyin_nickname, douyin_avatar, display_name, last_login) '
                'VALUES (?,?,?,?,?)',
                (open_id, nickname, avatar, nickname or '', now))
            user_id = cur.lastrowid
            conn.execute(
                'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
                (user_id, 'trademind', 'free'))
            user = {'id': user_id, 'douyin_open_id': open_id, 'douyin_nickname': nickname}
        conn.commit()
    
    jwt = create_token(user['id'], app_name='trademind')
    print(f'[Douyin callback] SUCCESS user_id={user["id"]} -> {redirect_to}')
    # 跳转到主域名首页，传递 token 参数 + 设置 cookie（双保险）
    main_domain = os.environ.get('DEPLOY_DOMAIN', '')
    cd_val = '.' + main_domain
    callback_url = f'https://{main_domain}/?token={jwt}'
    resp = make_response(flask_redirect(callback_url))
    resp.set_cookie('sso_token', jwt, domain=cd_val, path='/', max_age=604800,
                    httponly=True, secure=True, samesite='Lax')
    return resp


# =============================================
# OAuth provider list (dynamic frontend rendering)
# =============================================
@auth_bp.route('/oauth/providers', methods=['GET'])
def oauth_providers():
    """Return enabled OAuth providers for the frontend login page (max 2)."""
    from services.oauth_service import get_enabled_oauth_providers
    providers = get_enabled_oauth_providers()
    return jsonify({'success': True, 'data': providers})


# =============================================
# Authlib-based OAuth — 统一第三方登录
# =============================================
@auth_bp.route('/oauth/<provider>/login', methods=['GET'])
def oauth_login(provider):
    """Initiate OAuth login via authlib or provider-specific URL."""
    from flask import redirect as flask_redirect, url_for
    from services.oauth_service import oauth, get_douyin_oauth_url, is_intl_oauth_provider, get_intl_oauth_provider
    import secrets, urllib.parse

    # ── International OAuth providers (Google/GitHub/Facebook) ──
    if is_intl_oauth_provider(provider):
        prov = get_intl_oauth_provider(provider)
        if not prov or not prov.is_configured():
            return flask_redirect(f'/login?error={provider} login not configured')
        redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True, _scheme='https')
        auth_url = prov.get_authorize_url(redirect_uri)
        return flask_redirect(auth_url)

    if provider == 'alipay':
        # 强制使用主站域名（支付宝白名单固定）→ 回调路径为 /auth/oauth/alipay/callback
        from services.alipay_service import _get_config as ali_get_cfg
        cfg = ali_get_cfg(site_domain=deploy.url("platform").replace('https://', ''))
        if not cfg:
            return flask_redirect(f'/{provider}-login?error=Not configured')
        callback = f'{deploy.url("platform")}/auth/oauth/alipay/callback'
        params = urllib.parse.urlencode({
            'app_id': cfg['client_key'],
            'scope': 'auth_user',
            'redirect_uri': callback,
            'state': 'login',
        })
        url = f'https://openauth.alipay.com/oauth2/publicAppAuthorize.htm?{params}'
        return flask_redirect(url)

    if provider == 'douyin':
        # 多租户：按请求域名查凭据 + 记录回调目标
        site_domain = _get_site_domain()
        redirect_to = request.args.get('redirect', '')
        if not redirect_to:
            redirect_to = f'https://{site_domain}/'
        url = get_douyin_oauth_url(site_domain, redirect_to=redirect_to)
        if not url:
            return flask_redirect(f'/login?error=Douyin login not configured')
        return flask_redirect(url)

    client = getattr(oauth, provider, None)
    if not client:
        return flask_redirect(f'/login?error=Unsupported login method')
    redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True, _scheme='https')
    return client.authorize_redirect(redirect_uri)


@auth_bp.route('/oauth/<provider>/callback', methods=['GET'])
def oauth_callback(provider):
    """OAuth callback — handle code exchange, user lookup, JWT creation."""
    from flask import redirect as flask_redirect, url_for
    from services.jwt_service import create_token
    from services.oauth_service import oauth, get_douyin_userinfo, is_intl_oauth_provider, get_intl_oauth_provider

    domain = _get_site_domain()

    # ── Telegram OAuth (special: hash verification, not code exchange) ──
    if provider == 'telegram':
        from flask import make_response
        from services.oauth_service import get_intl_oauth_provider
        prov = get_intl_oauth_provider(provider)
        if not prov:
            return flask_redirect(f'https://{domain}/login?error=telegram not configured')
        # Telegram sends user data as direct query params, not a "code"
        raw_query = request.query_string.decode('utf-8')
        user_info = prov.get_user_by_code(raw_query, '')
        if 'error' in user_info:
            return flask_redirect(f'https://{domain}/login?error={urllib.parse.quote(user_info["error"][:50])}')
        open_id = user_info.get('open_id', '')
        nickname = user_info.get('nickname', '')
        avatar = user_info.get('avatar', '')
        id_field = 'telegram_open_id'
        display_name = nickname or f'Telegram user {open_id[-4:]}'
        now = now_iso()
        with get_db() as conn:
            cur = conn.execute(f'SELECT * FROM users WHERE {id_field}=?', (open_id,))
            user_row = cur.fetchone()
            if user_row:
                user = dict(user_row)
                conn.execute('UPDATE users SET last_login=?, display_name=? WHERE id=?',
                             (now, display_name or user.get('display_name', ''), user['id']))
            else:
                cur = conn.execute(
                    f'INSERT INTO users ({id_field}, display_name, avatar_url, last_login) VALUES (?,?,?,?)',
                    (open_id, display_name, avatar, now))
                user_id = cur.lastrowid
                conn.execute(
                    'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
                    (user_id, 'trademind', 'free'))
                user = {'id': user_id, id_field: open_id, 'display_name': display_name}
            conn.commit()
        jwt = create_token(user['id'], app_name='trademind')
        main_domain = os.environ.get('DEPLOY_DOMAIN', '')
        callback_url = f'https://{main_domain}/?token={jwt}'
        cd_val = '.' + main_domain
        resp = make_response(flask_redirect(callback_url))
        resp.set_cookie('sso_token', jwt, domain=cd_val, path='/', max_age=604800,
                        httponly=True, secure=True, samesite='Lax')
        return resp

    # ── International OAuth providers (Google/GitHub/Facebook) ──
    if is_intl_oauth_provider(provider):
        from flask import make_response
        prov = get_intl_oauth_provider(provider)
        if not prov:
            return flask_redirect(f'https://{domain}/login?error={provider} not configured')
        code = request.args.get('code', '')
        if not code:
            return flask_redirect(f'https://{domain}/login?error=Missing authorization code')
        redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True, _scheme='https')
        user_info = prov.get_user_by_code(code, redirect_uri)
        if 'error' in user_info:
            return flask_redirect(f'https://{domain}/login?error={urllib.parse.quote(user_info["error"][:50])}')
        open_id = user_info.get('open_id', '')
        nickname = user_info.get('nickname', '')
        avatar = user_info.get('avatar', '')
        email = user_info.get('email', '')
        id_field = f'{provider}_open_id'
        # Use email as fallback username for display
        display_name = nickname or email or f'{provider} user {open_id[-4:]}'
        # Find or create user
        now = now_iso()
        with get_db() as conn:
            cur = conn.execute(f'SELECT * FROM users WHERE {id_field}=?', (open_id,))
            user_row = cur.fetchone()
            if user_row:
                user = dict(user_row)
                conn.execute('UPDATE users SET last_login=?, display_name=? WHERE id=?',
                             (now, display_name or user.get('display_name', ''), user['id']))
            else:
                cur = conn.execute(
                    f'INSERT INTO users ({id_field}, display_name, email, avatar_url, last_login) VALUES (?,?,?,?,?)',
                    (open_id, display_name, email, avatar, now))
                user_id = cur.lastrowid
                conn.execute(
                    'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
                    (user_id, 'trademind', 'free'))
                user = {'id': user_id, id_field: open_id, 'display_name': display_name}
            conn.commit()
        jwt = create_token(user['id'], app_name='trademind')
        main_domain = os.environ.get('DEPLOY_DOMAIN', '')
        callback_url = f'https://{main_domain}/?token={jwt}'
        cd_val = '.' + main_domain
        resp = make_response(flask_redirect(callback_url))
        resp.set_cookie('sso_token', jwt, domain=cd_val, path='/', max_age=604800,
                        httponly=True, secure=True, samesite='Lax')
        return resp

    # 从 state 解析回调目标 (格式: random_token|redirect_url)
    state = request.args.get('state', '')
    redirect_to = f'https://{domain}/'
    if '|' in state:
        import urllib.parse
        # state 被 urlencode 两次：quote(redirect) + urlencode(state参数)
        _, encoded_redirect = state.split('|', 1)
        redirect_to = urllib.parse.unquote(urllib.parse.unquote(encoded_redirect))
        if not redirect_to.startswith('http'):
            redirect_to = f'https://{domain}/'

    if provider == 'alipay':
        from services.alipay_service import get_access_token as ali_get_token, get_user_info as ali_get_user
        auth_code = request.args.get('auth_code', '')
        if not auth_code:
            return flask_redirect(f'https://{domain}/login?error=Missing authorization code')
        token_data = ali_get_token(auth_code, site_domain=domain)
        if 'error' in token_data:
            err_msg = token_data['error']
            import urllib.parse as _up
            print(f'[OAuth alipay] token error: {err_msg}')
            # stub 模式：用 auth_code 生成假用户
            if err_msg == 'stub mode':
                alipay_user_id = token_data.get('stub_user_id', 'stub_alipay')
                nickname = '支付宝用户'
                avatar = ''
                id_field = 'alipay_user_id'
                open_id = alipay_user_id
            else:
                return flask_redirect(f'https://{domain}/login?error=Alipay API: {_up.quote(err_msg[:50])}')
        else:
            alipay_user_id = token_data['user_id']
            access_token = token_data['access_token']
            info = ali_get_user(access_token, site_domain=domain)
            nickname = info.get('nickname', '') if 'error' not in info else ''
            avatar = info.get('avatar', '') if 'error' not in info else ''
            id_field = 'alipay_user_id'
            open_id = alipay_user_id

    # 抖音：手动换 token（接口非标准，authlib 不支持 client_key 参数名）
    if provider == 'douyin':
        from services.douyin_service import get_access_token as dy_get_token, get_user_info as dy_get_user
        code = request.args.get('code', '')
        if not code:
            return flask_redirect(f'https://{domain}/login?error=Missing authorization code')
        token_data = dy_get_token(code, site_domain=domain)
        if 'error' in token_data:
            err_msg = token_data['error']
            print(f'[OAuth douyin] token error: {err_msg}')
            return flask_redirect(f'https://{domain}/login?error=Login failed')
        open_id = token_data['open_id']
        access_token = token_data['access_token']
        info = dy_get_user(open_id, access_token, site_domain=domain)
        nickname = info.get('nickname', '') if 'error' not in info else ''
        avatar = info.get('avatar', '') if 'error' not in info else ''
        id_field = 'douyin_open_id'
    now = now_iso()
    with get_db() as conn:
        cur = conn.execute(f'SELECT * FROM users WHERE {id_field}=?', (open_id,))
        user_row = cur.fetchone()
        if user_row:
            user = dict(user_row)
            conn.execute('UPDATE users SET last_login=?, display_name=? WHERE id=?',
                         (now, nickname or user.get('display_name', ''), user['id']))
        else:
            display_name = nickname or f'{provider}用户_{open_id[-4:]}'
            cur = conn.execute(
                f'INSERT INTO users ({id_field}, display_name, last_login) VALUES (?,?,?)',
                (open_id, display_name, now))
            user_id = cur.lastrowid
            conn.execute(
                'INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)',
                (user_id, 'trademind', 'free'))
            user = {'id': user_id, id_field: open_id, 'display_name': display_name}
        conn.commit()

    jwt = create_token(user['id'], app_name='trademind')
    # 强制跳转到主域名，带 token 参数，实现全局登录
    main_domain = os.environ.get('DEPLOY_DOMAIN', '')
    # 从 redirect_to 提取路径部分（去掉域名），用于登录后跳转
    import urllib.parse
    parsed = urllib.parse.urlparse(redirect_to)
    final_path = parsed.path or '/'
    if parsed.query:
        final_path += '?' + parsed.query
    # 构建最终跳转 URL: 主域名 + token 参数 + redirect 参数（用于前端跳转到目标页面）
    callback_url = f'https://{main_domain}/?token={jwt}&redirect={urllib.parse.quote(final_path, safe="")}'
    cd_val = '.' + main_domain  # 跨子域共享 cookie
    print(f'[OAuth {provider}] SUCCESS: user_id={user["id"]} -> {callback_url}')
    print(f'[OAuth {provider}] COOKIE_DOMAIN={cd_val} JWT={jwt[:40]}...')
    from flask import redirect as flask_redirect2, make_response
    resp = make_response(flask_redirect2(callback_url))
    resp.set_cookie('sso_token', jwt, domain=cd_val, path='/', max_age=604800,
                    httponly=True, secure=True, samesite='Lax')
    return resp



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
        conn.execute('INSERT INTO sms_codes (phone, code, purpose, expires_at) VALUES (?,?,?,?)',
                     (email, code, 'email_verify', expires_at))
        conn.commit()
    from plugins.email.services import send_email
    subject = 'VeroRun 邮箱验证码'
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
            'SELECT code, expires_at FROM sms_codes WHERE phone=? AND purpose=? ORDER BY id DESC LIMIT 1',
            (email, 'email_verify')
        ).fetchone()
        if not row:
            return api_err('Please send verification code first')
        if row['expires_at'] < now_iso():
            return api_err('Verification code expired, please resend')
        if row['code'] != code:
            return api_err('Invalid verification code')
        # Check if email already used by another user
        exist = conn.execute('SELECT id FROM users WHERE email=? AND id!=?', (email, payload['user_id'])).fetchone()
        if exist:
            return api_err('This email is already in use')
        conn.execute('UPDATE users SET email=?, email_verified=1 WHERE id=?', (email, payload['user_id']))
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
            conn.execute("UPDATE user_sessions SET is_current=0 WHERE token_hash=?", (token_hash,))
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
