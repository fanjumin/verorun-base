#!/usr/bin/env python3
"""
build_manifest.py — 生成加密的完整性基准清单（修正点 4）
============================================================
用法:
    python3 veroguard/tools/build_manifest.py \
        --project-dir /opt/verorun \
        --output veroguard/data/manifest.json.enc \
        --secret YOUR_PROBE_SECRET

扫描指定目录下的核心文件，计算 SHA256，AES-256-GCM 加密输出。
由开发者在每次发版打包时手动运行。
"""
import os
import sys
import json
import hashlib
import secrets
import argparse
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── 需要保护的核心文件（相对于 PROJECT_DIR） ──
PROTECTED_FILES = [
    # Python 核心源代码
    "auth_server.py",
    "auth-center/models/database.py",
    "auth-center/services/jwt_service.py",
    "auth-center/services/unified_auth_service.py",
    "auth-center/services/license_service.py",
    "auth-center/routes/deployment_api.py",
    "main_site/app.py",
    "admin/app.py",
    "plugin_manager/manager.py",
    "plugin_manager/license.py",
    # 守护进程自身
    "veroguard/guardian.py",
    "veroguard/config.py",
    "veroguard/modules/health.py",
    "veroguard/modules/integrity.py",
    "veroguard/modules/fingerprint.py",
    "veroguard/modules/communicator.py",
    "veroguard/modules/executor.py",
    "veroguard/modules/runtime.py",
    "veroguard/modules/self_protect.py",
    # 关键插件核心
    "plugins/health_check/checkers.py",
    "plugins/health_check/ai_fixer.py",
    "plugins/health_check/models.py",
    "plugins/vault/dumper.py",
    # 部署脚本
    "deploy/install.sh",
]

# ── 各文件前缀的严重级别 ──
SEVERITY_MAP = [
    ("auth_server.py", "critical"),
    ("auth-center/", "critical"),
    ("plugin_manager/", "critical"),
    ("veroguard/", "critical"),
    ("deploy/", "critical"),
]


def get_severity(filepath: str) -> str:
    for prefix, level in SEVERITY_MAP:
        if filepath.startswith(prefix):
            return level
    return "warning"


def derive_key(secret: str, purpose: str) -> bytes:
    """从预共享密钥派生 AES 密钥"""
    return hashlib.sha256(f"{secret}:{purpose}".encode()).digest()


def build_manifest(project_dir: str) -> dict:
    """扫描 PROJECT_DIR 下的 PROTECTED_FILES，生成清单"""
    files = []
    for rel_path in PROTECTED_FILES:
        abs_path = os.path.join(project_dir, rel_path)
        if not os.path.exists(abs_path):
            print(f"  [SKIP] {rel_path} — 文件不存在")
            continue
        with open(abs_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        files.append({
            "path": rel_path,
            "hash": file_hash,
            "severity": get_severity(rel_path),
        })
        print(f"  [OK] {rel_path} → {file_hash[:16]}...")

    return {
        "version": 1,
        "generated_at": datetime.now().isoformat(),
        "project_dir": project_dir,
        "total_files": len(files),
        "files": files,
    }


def encrypt_manifest(manifest: dict, secret: str) -> bytes:
    """AES-256-GCM 加密清单"""
    key = derive_key(secret, "integrity_manifest")
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    plaintext = json.dumps(manifest, ensure_ascii=False).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def main():
    parser = argparse.ArgumentParser(
        description="生成 VeroGuard 完整性基准清单（修正点 4）"
    )
    parser.add_argument("--project-dir", required=True,
                        help="项目根目录")
    parser.add_argument("--output", required=True,
                        help="输出文件路径")
    parser.add_argument("--secret", required=True,
                        help="PROBE_SECRET 密钥（需与运行时一致）")
    args = parser.parse_args()

    print(f"扫描目录: {args.project_dir}")
    manifest = build_manifest(args.project_dir)
    print(f"共 {manifest['total_files']} 个文件")

    encrypted = encrypt_manifest(manifest, args.secret)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(encrypted)
    print(f"清单已加密保存至: {args.output}")


if __name__ == "__main__":
    main()
