#!/usr/bin/env python3
"""API Key encryption/decryption using Fernet symmetric encryption.
   Requires ENCRYPTION_KEY env var (32-byte hex string, set once)."""
import os, base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def _get_key():
    raw = os.environ.get('ENCRYPTION_KEY')
    if not raw:
        raise RuntimeError("ENCRYPTION_KEY environment variable is not set")
    # 使用密钥本身作为salt（密钥已足够随机），避免硬编码salt
    salt = raw[:16].encode()  # 使用密钥的前16字节作为salt
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    return base64.urlsafe_b64encode(kdf.derive(raw.encode()))

_fernet = Fernet(_get_key())

def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ''
    return _fernet.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    return _fernet.decrypt(ciphertext.encode()).decode()
