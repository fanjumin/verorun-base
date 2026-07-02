"""检查数据库用户"""
import sqlite3, os
db = os.environ.get('DB_PATH', 'verorun.db')
if not os.path.isabs(db):
    db = os.path.join(os.path.dirname(__file__), db)
db = os.path.abspath(db)
print(f'DB_PATH = {db}')
print(f'文件存在: {os.path.isfile(db)}')

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, username, is_admin, active FROM users')
rows = cur.fetchall()
if not rows:
    print('数据库中无用户!')
else:
    for r in rows:
        print(f'  id={r["id"]}, username={r["username"]}, is_admin={r["is_admin"]}, active={r["active"]}')
conn.close()
