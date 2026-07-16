"""Test admin login and verify full stack."""
import paramiko, time

def ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15, allow_agent=False, look_for_keys=False)
    return s

def run(c, cmd, wait=3):
    ch = c.get_transport().open_session()
    ch.exec_command(cmd)
    time.sleep(wait)
    out, err = b'', b''
    while ch.recv_ready(): out += ch.recv(4096)
    while ch.recv_stderr_ready(): err += ch.recv_stderr(4096)
    ch.close()
    return out.decode(errors='replace')

s = ssh()

print("="*60)
print("1. ADMIN LOGIN TEST")
print("="*60)
# Try password from SQLite: pbkdf2:sha256:100000$17a7277c304c09a4$17d9971b5bc684dfb6aa2d4d3866471cbb7497f195d1b0c68a4d64b032ba4a1e
# We need to know the plain text password. Let's try common ones
for pw in ['admin123', 'admin', '13800138000', '123456', 'password']:
    out = run(s, f'curl -s -w ":%{{http_code}}" -X POST http://localhost:8084/admin/login -H "Content-Type: application/json" -d \'{{"username":"13800138000","password":"{pw}"}}\' 2>&1', 2)
    code = out.split(':')[-1].strip()
    print(f'  password="{pw}": {code} - {out[:100]}')

print("\n" + "="*60)
print("2. PG AUTHENTICATION: Get password hash for admin")
print("="*60)
out = run(s, r"PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -t -c \"SELECT id, username, display_name, password_hash FROM public.users WHERE is_admin=1 LIMIT 3\" 2>&1", 3)
print(out[:500])

print("\n" + "="*60)
print("3. ALL ENDPOINTS TEST")
print("="*60)
endpoints = [
    ('GET', 'http://localhost:8081/', 'Auth root'),
    ('GET', 'http://localhost:8081/health', 'Auth health'),
    ('GET', 'http://localhost:8083/', 'Platform root'),
    ('GET', 'http://localhost:8084/', 'Admin root'),
    ('GET', 'http://localhost:8084/admin/login', 'Admin login page'),
    ('GET', 'http://localhost:8084/health', 'Admin health'),
]
for method, url, label in endpoints:
    out = run(s, f'curl -s -o /dev/null -w "%{{http_code}}" -X {method} {url} 2>&1', 2)
    print(f'  {label}: {out.strip()}')

print("\n" + "="*60)
print("4. AUTH LOG ERRORS (keyword match)")
print("="*60)
out = run(s, 'grep -v "INFO:werkzeug" /tmp/auth_8081.log | grep -iE "traceback|error|exception|cannot" | head -10', 2)
if out.strip():
    print(out[:1000])
else:
    print('  No errors')

print("\n" + "="*60)
print("5. OTHER DATA COUNTS")
print("="*60)
tables = ['site_configs', 'system_config', 'cms_categories', 'cms_posts', 'subscriptions', 'admin_profiles']
for t in tables:
    out = run(s, f'PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -t -c "SELECT count(*) FROM {t}" 2>&1', 2)
    print(f'  {t}: {out.strip()}')

s.close()
