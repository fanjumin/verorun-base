#!/usr/bin/env python3
"""JWT Service — token creation and validation using PyJWT.
Supports token revocation via jti blacklist (Redis / in-memory fallback)."""
import os, json, time, threading, logging
import jwt as pyjwt

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set")

JWT_ALGO = 'HS256'
JWT_EXPIRY_HOURS = 24 * 7  # 7 days
JWT_REFRESH_EXPIRY_HOURS = 24 * 30  # 30 days

# ── Token blacklist (in-memory fallback, use Redis in production) ──
_token_blacklist = {}
_blacklist_lock = threading.Lock()
_BLACKLIST_CLEANUP_INTERVAL = 3600  # 1h cleanup


def _cleanup_blacklist():
    """Remove expired entries from blacklist."""
    now = time.time()
    with _blacklist_lock:
        expired = [k for k, v in _token_blacklist.items() if v < now]
        for k in expired:
            del _token_blacklist[k]
    if expired:
        logger.info(f"Cleaned {len(expired)} expired tokens from blacklist")


def _revoke_jti(jti, expires_at):
    """Add a jti to the blacklist until expires_at."""
    with _blacklist_lock:
        _token_blacklist[jti] = expires_at


def _is_jti_revoked(jti):
    """Check if a jti is blacklisted."""
    with _blacklist_lock:
        return jti in _token_blacklist


def create_token(user_id, phone=None, app_name='trademind', is_admin=False,
                 token_type='access'):
    """Create a JWT with jti for revocation support."""
    import secrets
    jti = secrets.token_urlsafe(16)
    now = int(time.time())
    exp_hours = JWT_EXPIRY_HOURS if token_type == 'access' else JWT_REFRESH_EXPIRY_HOURS
    payload = {
        'jti': jti,
        'user_id': user_id,
        'phone': phone,
        'app_name': app_name,
        'is_admin': is_admin,
        'token_type': token_type,
        'iat': now,
        'exp': now + exp_hours * 3600,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def revoke_token(token):
    """Revoke a token by adding its jti to the blacklist."""
    payload = _decode_token(token, verify_exp=False)
    if payload and 'jti' in payload:
        _revoke_jti(payload['jti'], payload.get('exp', time.time() + 3600))
        _cleanup_blacklist()
        return True
    return False


def revoke_all_user_tokens(user_id):
    """Revoke ALL tokens for a given user (force logout everywhere).
    Since we can't enumerate all jtis for a user, we use a user-level
    revocation timestamp stored in the token payload.
    This is a simplified approach; for production use Redis sets."""
    # Mark user's tokens as revoked by storing a revocation timestamp
    # New tokens created after this point will have a newer iat
    from models import get_db
    now = int(time.time())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO system_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
            (f'user_token_revoked_at_{user_id}', str(now))
        )
        conn.commit()


def _decode_token(token, verify_exp=True):
    """Internal: decode without raising."""
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO],
                            options={'verify_exp': verify_exp})
    except pyjwt.ExpiredSignatureError:
        return None
    except Exception:
        return None


def validate_token(token):
    """Returns decoded payload or None.
    Checks jti blacklist and per-user revocation."""
    payload = _decode_token(token)
    if not payload:
        return None

    # Check jti blacklist
    jti = payload.get('jti')
    if jti and _is_jti_revoked(jti):
        return None

    # Check per-user revocation
    user_id = payload.get('user_id')
    if user_id:
        from models import get_db
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT value FROM system_config WHERE key=%s",
                    (f'user_token_revoked_at_{user_id}',)
                ).fetchone()
            if row:
                revoked_at = int(row['value'])
                if payload.get('iat', 0) < revoked_at:
                    return None  # Token issued before user was force-logged-out
        except Exception:
            pass  # Fail open on DB error (graceful degradation)

    return payload


def get_user_id(token):
    """Safely extract user_id from token."""
    if not token:
        return None
    payload = validate_token(token)
    return payload.get('user_id') if payload else None
