#!/usr/bin/env python3
"""
i18n English Source — 源码替换 + YAML 翻转
=============================================
使用 build_map.py 生成的精确映射表：
  1. 替换 .py / .html 中的 _('Chinese') → _('English')
  2. 翻转 YAML (key=英文)
"""

import os, sys, re, shutil, json
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
I18N_DIR = ROOT / 'i18n'

# ═══════════════════════════════════════════════════════════
# 1. 加载映射表
# ═══════════════════════════════════════════════════════════

with open(I18N_DIR / '_zh_to_en_map.json', 'r', encoding='utf-8') as f:
    zh_to_en = json.load(f)

print(f'Loaded {len(zh_to_en)} mappings')

# 按中文文本长度降序排列（长文本先匹配，避免短文本部分匹配）
sorted_keys = sorted(zh_to_en.keys(), key=len, reverse=True)

# ═══════════════════════════════════════════════════════════
# 2. 源码替换
# ═══════════════════════════════════════════════════════════

SKIP_DIRS = {'__pycache__', '.git', 'node_modules', 'venv', 'env',
             '.trae', 'PLANS', 'data', 'images', 'captcha-service/images',
             'i18n/_backup', 'i18n/__pycache__'}

stats = {'py_files': 0, 'py_repl': 0, 'html_files': 0, 'html_repl': 0}


def replace_in_source(filepath):
    """对文件做 _('Chinese') → _('English') 和 {{ _('Chinese') }} → {{ _('English') }} 替换"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return 0

    original = content
    replaced = 0

    # 匹配 _('...') 或 _("...")
    # 使用逐步替换而非正则，因为中文文本可能包含特殊字符
    for zh_text in sorted_keys:
        en_text = zh_to_en[zh_text]
        if zh_text == en_text:
            continue  # 中英相同，跳过

        # 模式1: _('zh_text') → _('en_text')
        needle = f"_('{zh_text}')"
        replacement = f"_('{en_text}')"
        cnt = content.count(needle)
        if cnt > 0:
            content = content.replace(needle, replacement)
            replaced += cnt

        # 模式2: _("zh_text") → _("en_text")
        needle = f'_\x28"{zh_text}"\x29'
        replacement = f'_\x28"{en_text}"\x29'
        cnt = content.count(needle)
        if cnt > 0:
            content = content.replace(needle, replacement)
            replaced += cnt

        # 模式3: {{ _('zh_text') }} → {{ _('en_text') }}
        needle = f"{{{{ _('{zh_text}') }}}}"
        replacement = f"{{{{ _('{en_text}') }}}}"
        cnt = content.count(needle)
        if cnt > 0:
            content = content.replace(needle, replacement)
            replaced += cnt

        # 模式4: {{ _("zh_text") }} → {{ _("en_text") }}
        needle = f'{{{{ _("{zh_text}") }}}}'
        replacement = f'{{{{ _("{en_text}") }}}}'
        cnt = content.count(needle)
        if cnt > 0:
            content = content.replace(needle, replacement)
            replaced += cnt

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return replaced


for root, dirs, files in os.walk(str(ROOT)):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]

    for fname in files:
        fpath = os.path.join(root, fname)
        rel = os.path.relpath(fpath, str(ROOT)).replace('\\', '/')

        # 跳过 i18n 目录自身（除了脚本）
        if '/i18n/' in rel and not fname.endswith('.py'):
            continue

        if fname.endswith('.py'):
            c = replace_in_source(fpath)
            if c > 0:
                stats['py_files'] += 1
                stats['py_repl'] += c
                print(f'  [py ] {rel}: +{c}')
        elif fname.endswith('.html'):
            c = replace_in_source(fpath)
            if c > 0:
                stats['html_files'] += 1
                stats['html_repl'] += c
                print(f'  [html] {rel}: +{c}')

# ═══════════════════════════════════════════════════════════
# 3. 翻转 YAML
# ═══════════════════════════════════════════════════════════

from i18n.build_map import parse_yaml_enhanced

zh = parse_yaml_enhanced(I18N_DIR / 'zh-CN.yml')
en = parse_yaml_enhanced(I18N_DIR / 'en.yml')

backup_dir = I18N_DIR / '_backup'
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(I18N_DIR / 'zh-CN.yml', backup_dir / 'zh-CN.yml')
shutil.copy2(I18N_DIR / 'en.yml', backup_dir / 'en.yml')

new_zh = {}
new_en = {}
unchanged = []

for k in zh:
    if k in en and en[k]:
        en_key = en[k]
        new_zh[en_key] = zh[k]
        new_en[en_key] = en_key
    else:
        new_zh[k] = zh[k]
        new_en[k] = k
        unchanged.append(k)

en_only = [k for k in en if k not in zh]
for k in en_only:
    new_zh[k] = en[k]
    new_en[k] = k

def sort_dict(d):
    return dict(sorted(d.items(), key=lambda x: str(x[0]).lower()))

new_zh = sort_dict(new_zh)
new_en = sort_dict(new_en)

def write_yaml(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        for k, v in data.items():
            val = str(v)
            if ': ' in val and not val.startswith('"'):
                val = f'"{val}"'
            f.write(f'{k}: {val}\n')

write_yaml(I18N_DIR / 'zh-CN.yml', new_zh)
write_yaml(I18N_DIR / 'en.yml', new_en)

print(f'\nYAML: {len(new_zh)} keys (英文源), {len(unchanged)} 未翻转')

# ═══════════════════════════════════════════════════════════
# 4. 验证
# ═══════════════════════════════════════════════════════════

print(f'\n=== 验证 auth.py ===')
# 检查还有没有中文在 _() 中
import subprocess

# 抽样验证
print(f'\n总计: {stats["py_files"]} py files ({stats["py_repl"]} repl), '
      f'{stats["html_files"]} html files ({stats["html_repl"]} repl)')

# 检查残留中文 _()
print('\n残留中文 _() 检查...')
for root, dirs, files in os.walk(str(ROOT)):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
    for fname in files:
        fpath = os.path.join(root, fname)
        rel = os.path.relpath(fpath, str(ROOT)).replace('\\', '/')
        if '/i18n/' in rel:
            continue
        if not fname.endswith(('.py', '.html')):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            # 查找 _(' 后跟中文字符
            matches = re.findall(r"_\(['\"]([\u4e00-\u9fff][^'\"]{2,})['\"]\)", content)
            if matches:
                for m in matches[:3]:
                    print(f'  {rel}: {m[:60]}')
        except Exception:
            pass

print('\nDone.')