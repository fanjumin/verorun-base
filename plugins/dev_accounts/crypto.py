#!/usr/bin/env python3
"""AES-256 encryption for developer account credentials.

Uses cryptography.fernet to encrypt/decrypt sensitive fields
(app_secret, bot_token, channel_secret, access_token).

Encryption key is derived from DEV_ACCOUNTS_ENCRYPTION_KEY environment variable.
"""

import os
import hashlib
import base64


def _get_encryption_key() -> bytes:
    """Derive a Fernet-compatible key from the environment variable.
    
    Raises RuntimeError if DEV_ACCOUNTS_ENCRYPTION_KEY is not set.
    """
    raw_key = os.environ.get('DEV_ACCOUNTS_ENCRYPTION_KEY')
    if not raw_key:
        raise RuntimeError(
            "DEV_ACCOUNTS_ENCRYPTION_KEY environment variable is required. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    key_bytes = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


try:
    from cryptography.fernet import Fernet
    _cipher = Fernet(_get_encryption_key())
    _HAS_CRYPTO = True
except ImportError:
    _cipher = None
    _HAS_CRYPTO = False


def encrypt(plaintext: str) -> str:
    """Encrypt a string value. Returns empty string if input is empty."""
    if not plaintext:
        return ''
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography library is required for dev_accounts encryption")
    return _cipher.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string value. Returns empty string if input is empty."""
    if not ciphertext:
        return ''
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography library is required for dev_accounts encryption")
    return _cipher.decrypt(ciphertext.encode()).decode()


def mask(value: str, show_first: int = 4, show_last: int = 4) -> str:
    """Mask a sensitive value for display.

    Example: 'abc123xyz789' → 'abc1****z789'
    """
    if not value or len(value) <= show_first + show_last:
        return '****'
    return value[:show_first] + '****' + value[-show_last:]