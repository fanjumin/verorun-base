"""测试管理员登录 - 写入文件版"""
import urllib.request, json, hashlib, hmac, sqlite3, os

log = []

# 1. 检查数据库路径
db = os.path.join('F:\\Sites\\VeroRun', 'data', 'verorun.db')
log.append(f'数据库: {db}')
log.append(f'文件存在: {os.path.isfile(db)}')

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id, username, phone, is_admin, password_hash FROM users WHERE username=?', ('admin',))
u = cur.fetchone()
if u:
    log.append(f'用户: id={u["id"]}, username={u["username"]}, phone={u["phone"]}, is_admin={u["is_admin"]}')
    log.append(f'password_hash={u["password_hash"]}')
    
    stored = u['password_hash']
    parts = stored.split(':') if stored else []
    if len(parts) == 5 and parts[0] == 'pbkdf2' and parts[1] == 'sha256':
        salt = parts[3]
        pw_hash = parts[4]
        check = hashlib.pbkdf2_hmac('sha256', 'Test1234!'.encode(), salt.encode(), 100000).hex()
        match = hmac.compare_digest(pw_hash, check)
        log.append(f'本地验证密码: 通过' if match else '本地验证密码: 失败')
    else:
        log.append(f'格式不正确, parts={len(parts)}')
else:
    log.append('admin 用户不存在')
conn.close()

log.append('')

# 2. API测试
url = 'http://127.0.0.1:8084/admin/login'
data = json.dumps({'username': 'admin', 'password': 'Test1234!', 'client_type': 'browser'}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    body = json.loads(resp.read())
    log.append(f'API: {resp.status}')
    log.append(f'响应: {json.dumps(body, indent=2, ensure_ascii=False)[:500]}')
except urllib.error.HTTPError as e:
    body = e.read().decode()
    log.append(f'API: HTTP {e.code}')
    log.append(f'响应: {body[:500]}')
except Exception as e:
    log.append(f'API 错误: {e}')

with open('F:\\Sites\\VeroRun\\test_login_result.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(log))
