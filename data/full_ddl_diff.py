import sqlite3, difflib

conn_old = sqlite3.connect(r'F:\Sites\VeroRun\data\easykai.db')
conn_new = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')

old_tables = set(row[0] for row in conn_old.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall())
new_tables = set(row[0] for row in conn_new.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall())

common = sorted(new_tables & old_tables)

print("=" * 80)
print(f"easykai.db (旧/7月1日): {len(old_tables)} 表")
print(f"verorun.db (新/当前):   {len(new_tables)} 表")
print(f"同名表: {len(common)}")
print("=" * 80)

# === 1. FULL DDL comparison for common tables ===
diff_count = 0
for t in common:
    old_row = conn_old.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    new_row = conn_new.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    if old_row and new_row:
        old_sql = old_row[0].strip()
        new_sql = new_row[0].strip()
        if old_sql != new_sql:
            diff_count += 1
            print(f"\n{'='*60}")
            print(f"⚠️  {t} — DDL 不一致")
            print(f"{'='*60}")
            diff = list(difflib.unified_diff(
                old_sql.splitlines(True),
                new_sql.splitlines(True),
                fromfile=f'easykai.db/{t}',
                tofile=f'verorun.db/{t}',
                lineterm=''
            ))
            for line in diff:
                print(line)

print(f"\n\n总结构差异表数: {diff_count}")

# === 2. Tables in verorun.db but NOT in easykai.db (need CREATE) ===
print(f"\n{'='*60}")
print(f"⚠️  不在 easykai.db 中的新表 (需要 CREATE)")
print(f"{'='*60}")
missing = new_tables - old_tables
for t in sorted(missing):
    sql = conn_new.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
    ).fetchone()
    print(f"\n-- CREATE TABLE {t}")
    if sql:
        print(sql[0])

# === 3. Tables in easykai.db but NOT in verorun.db (need DROP) ===
extra = old_tables - new_tables
print(f"\n{'='*60}")
print(f"⚠️  需要删除的废弃表 (easykai.db 有, verorun.db 无)")
print(f"{'='*60}")
for t in sorted(extra):
    print(f"  DROP TABLE IF EXISTS {t};")

# === 4. Indexes comparison ===
print(f"\n{'='*60}")
print(f"📊 索引差异")
print(f"{'='*60}")
old_indexes = set(row[0] for row in conn_old.execute(
    "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
).fetchall())
new_indexes = set(row[0] for row in conn_new.execute(
    "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
).fetchall())
# Filter out auto-generated indexes (sqlite_autoindex_...)
old_idx = {i for i in old_indexes if not i.startswith('sqlite_autoindex')}
new_idx = {i for i in new_indexes if not i.startswith('sqlite_autoindex')}
missing_idx = new_idx - old_idx
extra_idx = old_idx - new_idx
if missing_idx:
    print(f"需要添加的索引:")
    for i in sorted(missing_idx):
        print(f"  + {i}")
if extra_idx:
    print(f"需要删除的索引:")
    for i in sorted(extra_idx):
        print(f"  - {i}")
if not missing_idx and not extra_idx:
    print("  索引一致 (排除自动索引)")

conn_old.close()
conn_new.close()

print(f"\n{'='*80}")
print("分析完毕")
print(f"{'='*80}")
