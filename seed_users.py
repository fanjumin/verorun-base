"""重新 seed 用户到指定数据库"""
import hashlib, secrets, sqlite3, os

DB = os.environ.get('DB_PATH', 'verorun.db')
if not os.path.isabs(DB):
    DB = os.path.abspath(os.path.join(os.path.dirname(__file__), DB))

PASSWORD = 'Test1234!'

def make_password(password):
    salt = secrets.token_hex(8)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f'pbkdf2:sha256:100000:{salt}:{pw_hash}'

pw_stored = make_password(PASSWORD)

print(f'数据库: {DB}')
print(f'文件存在: {os.path.isfile(DB)}')

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 检查 users 表是否存在
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchall()
if not tables:
    print('users 表不存在，创建...')
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            phone TEXT UNIQUE,
            phone_verified INTEGER DEFAULT 0,
            email TEXT UNIQUE,
            password_hash TEXT,
            display_name TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT
        )
    """)

# 管理员
cur.execute("SELECT id FROM users WHERE username=?", ('admin',))
r = cur.fetchone()
if r:
    cur.execute("UPDATE users SET password_hash=?, is_admin=1, active=1 WHERE id=?", (pw_stored, r['id']))
    admin_id = r['id']
    print(f'管理员已更新 (id={admin_id})')
else:
    cur.execute("INSERT INTO users (username, phone, display_name, password_hash, is_admin, active, phone_verified) VALUES (?,?,?,?,1,1,1)",
                ('admin', '13800000000', 'System Admin', pw_stored))
    admin_id = cur.lastrowid
    print(f'管理员已创建 (id={admin_id})')

# 确保 admin_profiles
try:
    cur.execute("CREATE TABLE IF NOT EXISTS admin_profiles (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, role TEXT, permissions TEXT)")
    cur.execute("SELECT id FROM admin_profiles WHERE user_id=?", (admin_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO admin_profiles (user_id, role, permissions) VALUES (?, 'super_admin', '[\"users\",\"content\",\"finance\",\"system\",\"matrix\",\"admins\"]')",
                    (admin_id,))
        print(f'admin_profiles 已创建')
except Exception as e:
    print(f'admin_profiles 跳过: {e}')

# 普通用户
cur.execute("SELECT id FROM users WHERE username=?", ('testuser',))
r = cur.fetchone()
if r:
    cur.execute("UPDATE users SET password_hash=?, active=1 WHERE id=?", (pw_stored, r['id']))
    tid = r['id']
    print(f'testuser 已更新 (id={tid})')
else:
    cur.execute("INSERT INTO users (username, phone, display_name, password_hash, is_admin, active, phone_verified) VALUES (?,?,?,?,0,1,1)",
                ('testuser', '13800000001', 'Test User', pw_stored))
    print(f'testuser 已创建 (id={cur.lastrowid})')

conn.commit()
conn.close()
print()
print(f'✅ 完成！用户名 admin / 密码 {PASSWORD}')
