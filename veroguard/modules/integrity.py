#!/usr/bin/env python3
"""
VeroGuard — 文件完整性校验模块（Phase 2）
=============================================
从加密的 manifest.json.enc 加载基准清单，
SHA256 逐一比对核心文件，返回违规列表。

违反级别:
  critical — 核心认证/授权/守护进程文件
  high     — 关键业务逻辑
  warning  — 其他受保护文件
"""
import hashlib
import json
import logging
import os
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .. import config


def _derive_key(secret: str, purpose: str) -> bytes:
    """从预共享密钥派生 AES 密钥（与 build_manifest.py 一致）"""
    return hashlib.sha256(f"{secret}:{purpose}".encode()).digest()


def load_manifest() -> dict:
    """加载并解密完整性基准清单"""
    manifest_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'manifest.json.enc'
    )
    if not os.path.exists(manifest_path):
        logging.warning("Manifest not found: %s — skipping integrity check",
                        manifest_path)
        return {'files': []}

    key = _derive_key(config.PROBE_SECRET, 'integrity_manifest')
    with open(manifest_path, 'rb') as f:
        nonce = f.read(12)
        ciphertext = f.read()

    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext)
    except Exception as e:
        logging.error("Failed to decrypt manifest: %s", e)
        return {'files': []}


def run() -> list:
    """
    校验核心文件，返回违规列表。

    返回值:
        [
            {
                'file': 'auth_server.py',
                'type': 'modified',     # modified | deleted
                'severity': 'critical',
                'expected_hash': 'abc123...',
                'actual_hash': 'def456...'   # 仅 modified 有
            },
            ...
        ]
    """
    if not config.PROBE_SECRET:
        logging.warning("PROBE_SECRET not set — skipping integrity check")
        return []

    manifest = load_manifest()
    if not manifest.get('files'):
        return []

    violations = []
    for entry in manifest['files']:
        path = os.path.join(config.PROJECT_DIR, entry['path'])
        if not os.path.exists(path):
            violations.append({
                'file': entry['path'],
                'type': 'deleted',
                'severity': entry.get('severity', 'warning'),
                'expected_hash': entry['hash'],
            })
            logging.warning("Integrity violation: %s DELETED", entry['path'])
            continue

        with open(path, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()

        if actual_hash != entry['hash']:
            violations.append({
                'file': entry['path'],
                'type': 'modified',
                'severity': entry.get('severity', 'warning'),
                'expected_hash': entry['hash'],
                'actual_hash': actual_hash,
            })
            logging.warning("Integrity violation: %s MODIFIED", entry['path'])

    return violations
