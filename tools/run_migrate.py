"""Upload and run data migration on server."""
import paramiko, time, os

HOST = '***REMOVED***'
BASE = '/home/easykai/easykai-workspace/easykai.cn'
PASS = '***REMOVED***'

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username='easykai', password=PASS, timeout=15, allow_agent=False, look_for_keys=False)

# Upload migration script
local_script = r'F:\Sites\VeroRun\tools\do_migrate.py'
remote_script = f'{BASE}/tools/do_migrate.py'

with s.open_sftp() as sf:
    sf.put(local_script, remote_script)
print(f'Uploaded do_migrate.py to server')

# Run migration on server
print('\n=== Running migration ===')
c = s.get_transport().open_session()
c.exec_command(
    f'cd {BASE} && PG_HOST=localhost PG_PORT=5432 PG_DB=verorun PG_USER=easykai PG_PASSWORD={PASS} '
    f'python3 -B tools/do_migrate.py 2>&1'
)
time.sleep(30)  # Give it time for the migration
out = b''
while c.recv_ready():
    out += c.recv(4096)
err = b''
while c.recv_stderr_ready():
    err += c.recv_stderr(4096)
c.close()

print(out.decode(errors='replace'))
if err:
    print(f'Stderr:\n{err.decode(errors="replace")[:1000]}')

# Verify data
print('\n=== Verification ===')
c = s.get_transport().open_session()
c.exec_command(f"PGPASSWORD={PASS} psql -h localhost -U easykai -d verorun -t -c \"SELECT count(*) FROM users\" 2>&1")
time.sleep(3)
out, err = b'', b''
while c.recv_ready(): out += c.recv(4096)
while c.recv_stderr_ready(): err += c.recv_stderr(4096)
c.close()
print(f"Users in PG: {out.decode(errors='replace').strip()}")

# Restart all services
print('\n=== Restarting services ===')
env = f"PG_PASSWORD={PASS} PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET=30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d FLASK_SECRET_KEY=30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d"

c = s.get_transport().open_session()
c.exec_command(f"cd {BASE} && {env} nohup python3 -B auth_server.py 8081 > /tmp/auth_8081.log 2>&1 &")
time.sleep(3)
out, err = b'', b''
while c.recv_ready(): out += c.recv(4096)
while c.recv_stderr_ready(): err += c.recv_stderr(4096)
c.close()

c = s.get_transport().open_session()
c.exec_command(f"cd {BASE} && {env} nohup python3 -B platform/app.py 8083 > /tmp/platform_8083.log 2>&1 &")
time.sleep(3)
c.close()

c = s.get_transport().open_session()
c.exec_command(f"cd {BASE} && {env} nohup python3 -B admin/app.py 8084 > /tmp/admin_8084.log 2>&1 &")
time.sleep(3)
c.close()

time.sleep(10)

# Final check
print('\n=== Final Status ===')
c = s.get_transport().open_session()
c.exec_command("""for p in 8081 8083 8084; do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:$p/ 2>&1)
  echo ":$p -> $code"
done""")
time.sleep(3)
out, err = b'', b''
while c.recv_ready(): out += c.recv(4096)
while c.recv_stderr_ready(): err += c.recv_stderr(4096)
c.close()
print(out.decode(errors='replace'))

# Login test
print('\n=== Login Test ===')
for endpoint in ['/sms/login', '/login', '/auth/sms/login']:
    c = s.get_transport().open_session()
    c.exec_command(f"""curl -s -w ':%{{http_code}}' -X POST http://localhost:8081{endpoint} \
      -H 'Content-Type: application/json' \
      -d '{{"phone":"13800138000","password":"admin123"}}' 2>&1""")
    time.sleep(3)
    out, err = b'', b''
    while c.recv_ready(): out += c.recv(4096)
    while c.recv_stderr_ready(): err += c.recv_stderr(4096)
    c.close()
    resp = out.decode(errors='replace')
    print(f'  POST {endpoint}: {resp[:200]}')

s.close()
