#!/usr/bin/env python3
"""
i18n 翻译方向翻转：中文源 → 英文源
用逐行解析替代 yaml.safe_load，避免特殊字符问题。

Flip i18n source from Chinese→Chinese to English→Chinese.
Outputs new zh-CN.yml and en.yml with English keys.
"""
import os, shutil, sys

# 强制 UTF-8 输出（Windows 兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_yaml_lines(filepath):
    """
    逐行解析简单 YAML (key: value)，跳过注释和空行。
    返回 dict{key: value}
    """
    result = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            # 找第一个 ': ' 作为 key-value 分隔符
            idx = stripped.find(': ')
            if idx == -1:
                continue
            key = stripped[:idx]
            value = stripped[idx + 2:]
            result[key] = value
    return result


# ─── 1. 加载 ───
zh = parse_yaml_lines(os.path.join(HERE, 'zh-CN.yml'))
en = parse_yaml_lines(os.path.join(HERE, 'en.yml'))

print(f'zh-CN keys: {len(zh)}')
print(f'en keys:    {len(en)}')

# ─── 2. 分析 ───
zh_no_en = [k for k in zh if k not in en or not en[k]]
zh_with_en = [k for k in zh if k in en and en[k]]
en_only = [k for k in en if k not in zh]

print(f'有英文翻译: {len(zh_with_en)}')
print(f'无英文翻译: {len(zh_no_en)}')
print(f'en.yml独有的: {len(en_only)}')

# ─── 3. 打印报告 ───
print(f'\n=== 无翻译的中文key ({len(zh_no_en)}条) ===')
for k in zh_no_en:
    print(f'  {k[:100]}')

# ─── 4. 翻转 ───
new_zh = {}  # 英文key → 中文翻译
new_en = {}  # 英文key → 英文翻译
unchanged = []

for k in zh:
    if k in en and en[k]:
        en_key = en[k]
        new_zh[en_key] = zh[k]
        new_en[en_key] = en_key
    else:
        # 保持原 key（没有英文翻译），这是需要后续补充的
        new_zh[k] = zh[k]
        new_en[k] = k
        unchanged.append(k)

for k in en_only:
    new_zh[k] = en[k]
    new_en[k] = k

# 排序
def sort_by_key(d):
    return dict(sorted(d.items(), key=lambda x: str(x[0]).lower()))

new_zh = sort_by_key(new_zh)
new_en = sort_by_key(new_en)

# ─── 5. 备份 ───
backup_dir = os.path.join(HERE, '_backup')
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(os.path.join(HERE, 'zh-CN.yml'), os.path.join(backup_dir, 'zh-CN.yml'))
shutil.copy2(os.path.join(HERE, 'en.yml'), os.path.join(backup_dir, 'en.yml'))
print(f'\n备份: {backup_dir}/')

def write_yaml_lines(filepath, data):
    """写 YAML，对含冒号的值加双引号"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for k, v in data.items():
            # 如果值中包含 ': '（冒号+空格），用双引号包裹
            val_str = str(v)
            if ': ' in val_str and not val_str.startswith('"'):
                val_str = f'"{val_str}"'
            f.write(f'{k}: {val_str}\n')

# ─── 6. 写入 ───
write_yaml_lines(os.path.join(HERE, 'zh-CN.yml'), new_zh)
write_yaml_lines(os.path.join(HERE, 'en.yml'), new_en)

print(f'\n=== 翻转完成 ===')
print(f'新 zh-CN.yml: {len(new_zh)} keys (英文→中文)')
print(f'新 en.yml:    {len(new_en)} keys (英文→英文)')
print(f'成功翻转:     {len(zh_with_en)}')
print(f'保持原key:    {len(unchanged)} (无英文翻译，需后续补充)')
print(f'en.yml独有:   {len(en_only)}')

# ─── 7. 抽样 ───
print(f'\n=== 抽样验证 (前5条) ===')
for i, k in enumerate(list(new_zh.keys())[:5]):
    print(f'  [{k[:60]}]')
    print(f'  ZH: {str(new_zh[k])[:60]}')
    print()

print(f'\n=== 无翻译条目已保存到上方报告 ===')
print(f'共 {len(unchanged)} 条需要在后续手动补充英文翻译。')
