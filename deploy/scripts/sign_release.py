#!/usr/bin/env python3
"""审计 D10：发版签名工具 —— 计算 common.sh 的 LF 归一化 SHA-256 并回填 install.sh。

用法（发布新版前在项目根目录执行）：
    python3 deploy/scripts/sign_release.py

说明：
    raw.githubusercontent.com 上的 common.sh 为 LF 行尾；Windows 检出为 CRLF。
    此处统一按 LF 归一化计算哈希，与 curl 拉取到的内容一致。
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # verorun-code 仓库根目录
COMMON = ROOT / "deploy" / "lib" / "common.sh"
INSTALL = ROOT / "deploy" / "install.sh"


def lf_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    digest = lf_sha256(COMMON)
    text = INSTALL.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r'(_COMMON_SHA256="\$\{COMMON_SHA256:-)[0-9a-f]{64}(\}")',
        lambda m: f"{m.group(1)}{digest}{m.group(2)}",
        text,
        count=1,
    )
    if n == 0:
        print(f"[FAIL] install.sh 中未找到 _COMMON_SHA256 占位，无法回填: {digest}")
        return 1
    if new_text == text:
        print(f"[SKIP] _COMMON_SHA256 已是最新: {digest}")
        return 0
    INSTALL.write_text(new_text, encoding="utf-8")
    print(f"[OK] common.sh SHA-256 = {digest}")
    print(f"[OK] 已回填 {INSTALL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
