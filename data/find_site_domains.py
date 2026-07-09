import sqlite3

# Check verorun.db
db = sqlite3.connect(r'F:\Sites\VeroRun\data\verorun.db')
tables = [r[0] for r in db.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')]
if 'site_domains' in tables:
    schema = db.execute('SELECT sql FROM sqlite_master WHERE name="site_domains"').fetchone()
    print('=== site_domains 表 DDL ===')
    print(schema[0])
    
    # Also check if there's data
    count = db.execute('SELECT COUNT(*) FROM site_domains').fetchone()[0]
    print(f'\n已有数据: {count} 条')
    if count > 0:
        for row in db.execute('SELECT * FROM site_domains LIMIT 10'):
            print(f'  {row}')
else:
    print('❌ verorun.db 中也没有 site_domains 表')

# Also check if in easykai.db
db2 = sqlite3.connect(r'F:\Sites\VeroRun\data\easykai.db')
tables2 = [r[0] for r in db2.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')]
if 'site_domains' in tables2:
    print('\n✅ easykai.db 中有 site_domains 表')
    schema2 = db2.execute('SELECT sql FROM sqlite_master WHERE name="site_domains"').fetchone()
    print(schema2[0])
else:
    print('\n❌ easykai.db 中也没有 site_domains 表')

# Also check verorun.db for any other tables that old easykai.db might be missing
print('\n=== verorun.db 特有表（不在 easykai.db 中）===')
for t in tables:
    if t not in tables2:
        print(f'  {t}')

db.close()
db2.close()
