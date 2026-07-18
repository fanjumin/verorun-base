#!/usr/bin/env python3
"""SMS Plugin Services — 验证码发送核心逻辑

Provider 配置从 system_config 表读取（通过主库只读连接）。
与旧 auth-center/services/sms_service.py 兼容，逐步迁移至此。
"""
import os
import secrets
import string
from datetime import datetime

from .models import get_sms_db

# ── 模板映射（与旧系统兼容）──
TEMPLATE_MAP = {
    'register':        'SMS_506135003',
    'change_phone':    'SMS_506380001',
    'reset_password':  'SMS_506285002',
    'modify_password': 'SMS_506190002',
    'login':           'SMS_506330002',
}
DEFAULT_TEMPLATE = 'SMS_506135003'


def get_market():
    """Return current market: 'cn' or 'intl'."""
    return os.environ.get('DEPLOY_MARKET', 'cn')


def get_sms_provider():
    """Return the appropriate SMS provider instance based on market + config.

    Reads Aliyun config from system_config table via main db read-only.
    """
    import sys
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)

    market = get_market()

    if market == 'intl':
        try:
            from providers.sms.twilio import TwilioSMSProvider
            twilio = TwilioSMSProvider()
            if twilio.is_configured():
                return twilio
        except ImportError:
            pass

    # CN market or fallback: try Aliyun
    try:
        from providers.sms.aliyun import AliyunSMSProvider
        aliyun = AliyunSMSProvider()
        if aliyun.is_configured():
            return aliyun
    except ImportError:
        pass

    return None


def generate_code(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def send_sms(phone, code, purpose='login'):
    """Send verification code for a specific purpose.

    Uses market-based provider selection:
      - intl + Twilio -> sends plain-text message
      - CN + Aliyun   -> sends purpose-specific template
      - fallback      -> stub (console log + save to sms_logs)
    """
    provider = get_sms_provider()
    market = get_market()
    template = None

    if provider:
        if market == 'intl' and provider.PROVIDER == 'twilio':
            message = f'Your EasyKai verification code is: {code}. Valid for 10 minutes.'
            result = provider.send(phone, message)
            result['template'] = 'plain_text'
            template = 'plain_text'
        elif provider.PROVIDER == 'aliyun':
            result = _send_aliyun_via_provider(provider, phone, code, purpose)
            template = TEMPLATE_MAP.get(purpose, DEFAULT_TEMPLATE)
    else:
        # Fallback: stub mode
        print(f"[SMS STUB] To: {phone} | Code: {code}")
        result = {'success': True, 'provider': 'stub', 'code': code}

    # 记录发送日志
    _log_send(phone, code, purpose, result.get('provider', 'stub'),
              'sent' if result.get('success') else 'failed',
              result.get('error', ''))

    return result


def _send_aliyun_via_provider(provider, phone, code, purpose='login'):
    """Send SMS via Aliyun provider (uses purpose-specific templates)."""
    return provider.send(phone, '', purpose=purpose, code=code)


def _log_send(phone, code, purpose, provider, status, error=''):
    """记录短信发送日志到 sms.db"""
    try:
        conn = get_sms_db()
        conn.execute(
            'INSERT INTO sms_logs (phone, code, purpose, provider, status, error) VALUES (?,?,?,?,?,?)',
            (phone, code, purpose, provider, status, error)
        )
        conn.commit()
    except Exception as e:
        print(f'[SmsPlugin] Log write failed: {e}')


def check_rate_limit(phone, max_per_hour=5):
    """Check if phone has exceeded SMS rate limit."""
    import sys
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)

    from models import get_db, now_iso
    hour_bucket = datetime.now().strftime('%Y%m%d_%H')
    with get_db() as conn:
        row = conn.execute(
            'SELECT count FROM sms_rate_limits WHERE phone=? AND hour_bucket=?',
            (phone, hour_bucket)
        ).fetchone()
        if row and row['count'] >= max_per_hour:
            return False
        if row:
            conn.execute('UPDATE sms_rate_limits SET count=count+1 WHERE phone=? AND hour_bucket=?',
                         (phone, hour_bucket))
        else:
            conn.execute('INSERT INTO sms_rate_limits (phone, hour_bucket, count) VALUES (?,?,1)',
                         (phone, hour_bucket))
        conn.commit()
    return True


def validate_phone(phone, country_code=''):
    """Validate phone number format based on market."""
    import re
    market = get_market()

    if market == 'intl':
        cleaned = re.sub(r'[\s\-\(\)]+', '', phone)
        digits_only = cleaned.lstrip('+')
        if not digits_only.isdigit() or len(digits_only) < 7 or len(digits_only) > 15:
            return False, phone, 'Invalid phone number'
        if not cleaned.startswith('+'):
            if country_code and country_code.startswith('+'):
                cleaned = country_code + digits_only
            elif country_code:
                cleaned = '+' + country_code.lstrip('+') + digits_only
            else:
                cleaned = '+' + digits_only
        return True, cleaned, ''
    else:
        if not phone or len(phone) != 11 or not phone.isdigit() or not phone.startswith('1'):
            return False, phone, 'Please enter a valid phone number'
        return True, phone, ''
