#!/usr/bin/env python3
"""
从代码中提取所有中文字符串，生成待翻译的 YAML 文件。

用法:
    python i18n/extract_strings.py
    # 生成 i18n/zh-CN.yml（更新基准文件）
    # 然后: cp i18n/zh-CN.yml i18n/en.yml（手动翻译）
"""
import os
import re
import yaml

CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


def extract_from_file(file_path: str) -> list[str]:
    """从单个文件中提取所有中文字符串"""
    strings = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 从 _('...') 或 _("...") 中提取
            matches = re.findall(r"_\(['\"](.+?)['\"]\)", line)
            for m in matches:
                if CHINESE_PATTERN.search(m):
                    strings.append(m)
            # 从 return '...' / 'error': '...' 中提取
            matches = re.findall(
                r"['\"]([^'\"]*[\u4e00-\u9fff][^'\"]*)['\"]", line
            )
            for m in matches:
                if len(m) < 100:  # 忽略太长的字符串（可能是文章内容）
                    strings.append(m)
    return strings


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_strings = set()

    # 扫描目录
    scan_dirs = [
        'auth-center/routes/',
        'auth-center/services/',
        'platform/templates/',
        'platform/app.py',
        'admin/templates/',
    ]

    for scan_path in scan_dirs:
        full_path = os.path.join(base_dir, scan_path)
        if os.path.isdir(full_path):
            for root, _, files in os.walk(full_path):
                for f in files:
                    if f.endswith(('.py', '.html', '.js')):
                        file_full_path = os.path.join(root, f)
                        try:
                            strings = extract_from_file(file_full_path)
                            all_strings.update(strings)
                        except Exception as e:
                            print(f'[i18n] Warning: error reading {file_full_path}: {e}')

    # 读取已有 zh-CN.yml
    existing = {}
    zh_path = os.path.join(os.path.dirname(__file__), 'zh-CN.yml')
    if os.path.exists(zh_path):
        with open(zh_path, 'r', encoding='utf-8') as f:
            existing = yaml.safe_load(f) or {}

    # 合并新提取的字符串（中文基准：原文即翻译）
    for s in sorted(all_strings):
        if s not in existing:
            existing[s] = s

    # 写回 zh-CN.yml
    with open(zh_path, 'w', encoding='utf-8') as f:
        yaml.dump(existing, f, allow_unicode=True, sort_keys=True)

    print(f'[i18n] Extracted {len(all_strings)} strings → {zh_path}')
    print(f'[i18n] Total entries: {len(existing)}')
    print(f'[i18n] Run: copy {zh_path} {os.path.join(os.path.dirname(zh_path), "en.yml")} and translate')


if __name__ == '__main__':
    main()
