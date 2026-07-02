"""检查数据库中实际的密码哈希"""
import sqlite3, os

db_path = os.path.join('F:\\Sites\\VeroRun', 'data', 'verorun.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT username, is_admin, password_hash FROM users')
users = cur.fetchall()
for u in users:
    ph = u['password_hash']
    print(f'user={u["username"]}, admin={u["is_admin"]}')
    print(f'  hash={ph}')
    parts = ph.split(':') if ph else []
    print(f'  parts={len(parts)}, format_ok={len(parts)==5 and parts[0]=="pbkdf2"}')
    print()
conn.close()
