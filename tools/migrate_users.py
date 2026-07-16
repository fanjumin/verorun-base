"""Migrate users from SQLite to PG with column mapping."""
import paramiko, time, json

def ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15, allow_agent=False, look_for_keys=False)
    return s

def run(c, cmd, wait=3):
    ch = c.get_transport().open_session()
    ch.exec_command(cmd)
    time.sleep(wait)
    out = b''
    while ch.recv_ready(): out += ch.recv(4096)
    while ch.recv_stderr_ready(): err += ch.recv_stderr(4096)
    ch.close()
    return out.decode(errors='replace')

s = ssh()
BASE = '/home/easykai/easykai-workspace/easykai.cn'

# Step 1: Get all SQLite users as JSON
print('Reading SQLite users...')
out = run(s, f"""
python3 -c "
import sqlite3, json
sq = sqlite3.connect('{BASE}/data/x7k2m9a4.db')
sq.row_factory = sqlite3.Row
users = sq.execute('SELECT * FROM users').fetchall()
cols = [d[1] for d in sq.execute('PRAGMA table_info(users)').fetchall()]
result = []
for u in users:
    d = dict(zip(cols, u))
    result.append(d)
print(json.dumps(result, default=str))
" 2>&1
""", 5)

users = json.loads(out.strip())
print(f'Got {len(users)} users')

# Step 2: Insert into PG with column mapping
PG_COLS = ['username', 'phone', 'email', 'password_hash', 'display_name',
           'avatar_url', 'created_at', 'last_login', 'is_admin',
           'wechat_openid', 'wechat_unionid', 'wechat_nickname',
           'phone_verified', 'active', 'email_verified']

def map_user(sq_user):
    """Map SQLite user row to PG columns."""
    return {
        'username': sq_user.get('username', '') or sq_user.get('phone', ''),
        'phone': sq_user.get('phone', ''),
        'email': sq_user.get('email', ''),
        'password_hash': sq_user.get('password_hash', ''),
        'display_name': sq_user.get('nickname') or sq_user.get('username') or sq_user.get('phone', ''),
        'avatar_url': sq_user.get('avatar_url', ''),
        'created_at': sq_user.get('created_at', 'NOW()'),
        'last_login': sq_user.get('last_login', None),
        'is_admin': 1 if sq_user.get('is_admin') else 0,
        'wechat_openid': sq_user.get('wechat_openid', ''),
        'wechat_unionid': sq_user.get('wechat_unionid', ''),
        'wechat_nickname': sq_user.get('wechat_nickname', ''),
        'phone_verified': 1 if sq_user.get('phone_verified') else 0,
        'active': 1 if sq_user.get('active', 1) else 0,
        'email_verified': 1 if sq_user.get('email_verified') else 0,
    }

# Build SQL
col_list = ', '.join(f'"{c}"' for c in PG_COLS)
ph = ', '.join(f'%s' for _ in PG_COLS)
sql = f'INSERT INTO public.users ({col_list}) OVERRIDING SYSTEM VALUE VALUES ({ph}) ON CONFLICT (id) DO NOTHING'

success = 0
for u in users:
    mapped = map_user(u)
    vals = tuple(mapped[c] for c in PG_COLS)
    # Escape strings for shell
    vals_esc = json.dumps(vals)
    
    cmd = f"PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -c \"{sql}\" -v v1='{vals[0]}' 2>&1"
    # Simple approach: use python for each user
    chunk = run(s, f"""
python3 -c "
import psycopg2
pg = psycopg2.connect(host='localhost', port=5432, dbname='verorun', user='easykai', password='***REMOVED***')
cur = pg.cursor()
try:
    cur.execute('''{sql}''', {json.dumps(vals)})
    pg.commit()
    print('OK')
except Exception as e:
    pg.rollback()
    print(f'ERR: {{e}}')
cur.close()
pg.close()
" 2>&1
""", 2)
    if 'OK' in chunk:
        success += 1
    else:
        print(f'  Failed user {u.get("id")}: {chunk[:80]}')

print(f'\nMigrated {success}/{len(users)} users to PG')

# Verify
print('\nVerification:')
out = run(s, "PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -t -c \"SELECT count(*) FROM users\" 2>&1", 3)
print(f'  Users in PG: {out.strip()}')

s.close()
