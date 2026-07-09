import sqlite3, re

# === Local easykai.db (the OLD database, July 1) ===
conn_old = sqlite3.connect(r'F:\Sites\VeroRun\data\easykai.db')
old_tables = set(row[0] for row in conn_old.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall())
conn_old.close()

# === Local verorun.db (the NEW reference database) ===
conn_new = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')
new_tables = set(row[0] for row in conn_new.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall())
conn_new.close()

print('=' * 60)
print('本地 easykai.db (旧库) 表数:', len(old_tables))
print('本地 verorun.db (新库参考) 表数:', len(new_tables))
print('=' * 60)

# === 1. Tables in verorun.db but NOT in easykai.db ===
missing = new_tables - old_tables
print(f'\n=== 需要添加的表 (verorun.db有，easykai.db没有) ===')
print(f'共 {len(missing)} 张')
for t in sorted(missing):
    print(f'  + {t}')

# === 2. Tables in easykai.db but NOT in verorun.db ===
extra = old_tables - new_tables
print(f'\n=== 需要删除的表 (easykai.db有，verorun.db没有) ===')
print(f'共 {len(extra)} 张')
for t in sorted(extra):
    print(f'  - {t}')

# === 3. Structure comparison for common tables ===
conn_old2 = sqlite3.connect(r'F:\Sites\VeroRun\data\easykai.db')
conn_new2 = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')

print(f'\n\n=== 同名表结构差异对比 ===')
diff_count = 0
common_tables = sorted(new_tables & old_tables)
for t in common_tables:
    old_ddl = conn_old2.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    new_ddl = conn_new2.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    if old_ddl and new_ddl:
        # Extract column definitions
        old_cols = set(re.findall(r'(\w+)\s+(INTEGER|TEXT|REAL|DECIMAL|BLOB)', old_ddl[0], re.IGNORECASE))
        new_cols = set(re.findall(r'(\w+)\s+(INTEGER|TEXT|REAL|DECIMAL|BLOB)', new_ddl[0], re.IGNORECASE))
        added = new_cols - old_cols
        removed = old_cols - new_cols
        if added or removed:
            diff_count += 1
            print(f'\n  ⚠️  {t}:')
            if added:   print(f'     新表中新增列: {sorted([c[0] for c in added])}')
            if removed: print(f'     旧表中多出列: {sorted([c[0] for c in removed])}')
if diff_count == 0:
    print('  ✅ 所有同名表结构一致')

# === 4. Generate CREATE TABLE SQL for missing tables ===
print(f'\n\n=== 缺失表 DDL (从 verorun.db 提取) ===')
conn_new3 = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')
for t in sorted(missing):
    sql = conn_new3.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    if sql:
        print(f'\n-- {t}')
        print(sql[0])
conn_new3.close()

conn_old2.close()
conn_new2.close()
