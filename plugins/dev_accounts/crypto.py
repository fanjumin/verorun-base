#!/usr/bin/env python3
"""Fernet 加密工具 — 用于加密 developer account 敏感字段。

底层算法：cryptography.fernet = AES-128-CBC + HMAC-SHA256（非 AES-256-GCM）。
密钥派生：DEV_ACCOUNTS_ENCRYPTION_KEY 环境变量 → SHA-256 → base64 urlsafe（Fernet 密钥格式）。
采用懒加载：首次 encrypt/decrypt 调用时才读取密钥并初始化，避免模块导入即崩溃。
"""

import os
import hashlib
import base64


_cipher = None
_HAS_CRYPTO = False


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


def _get_cipher():
    """Lazily initialize the Fernet cipher (P2-1: 懒加载)."""
    global _cipher, _HAS_CRYPTO
    if _cipher is None:
        try:
            from cryptography.fernet import Fernet
            _cipher = Fernet(_get_encryption_key())
            _HAS_CRYPTO = True
        except ImportError:
            _HAS_CRYPTO = False
            raise RuntimeError("cryptography library is required for dev_accounts encryption")
    return _cipher


def encrypt(plaintext: str) -> str:
    """Encrypt a string value. Returns empty string if input is empty."""
    if not plaintext:
        return ''
    return _get_cipher().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string value. Returns empty string if input is empty."""
    if not ciphertext:
        return ''
    return _get_cipher().decrypt(ciphertext.encode()).decode()


def mask(value: str, show_first: int = 4, show_last: int = 4) -> str:
    """Mask a sensitive value for display.

    Example: 'abc123xyz789' → 'abc1****z789'
    """
    if not value or len(value) <= show_first + show_last:
        return '****'
    return value[:show_first] + '****' + value[-show_last:]
