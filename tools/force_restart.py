#!/usr/bin/env python3
"""Force restart: kill systemd, free ports, restart correctly."""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

JWT = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT} PORT=8081"
BASE = '/home/easykai/easykai-workspace/easykai.cn'

def run(cmd, wait=3):
    c = s.get_transport().open_session()
    c.exec_command(cmd)
    time.sleep(wait)
    out = b''
    while c.recv_ready():
        out += c.recv(4096)
    err = b''
    while c.recv_stderr_ready():
        err += c.recv_stderr(4096)
    c.close()
    return out.decode(errors='replace'), err.decode(errors='replace')

# 1. Stop systemd services properly + disable auto-restart temporarily
print('1. Stopping systemd services...')
run("sudo systemctl stop auth-center.service 2>/dev/null", 2)
run("sudo systemctl stop admin.service 2>/dev/null", 2)
time.sleep(3)

# 2. Kill all user python processes
print('2. Killing all python processes...')
run("pkill -9 -u easykai python3 2>/dev/null", 2)
time.sleep(3)

# 3. Verify ports are free
print('3. Verifying ports free...')
out, _ = run("ss -tlnp | grep -E '808[134]' || echo 'ALL_FREE'", 2)
print(f'   {out.strip()[:100]}')

# 4. Clear logs
print('4. Clearing logs...')
run("rm -f /tmp/auth_8081.log /tmp/platform_8083.log /tmp/admin_8084.log", 1)

# 5. Start auth (creates tables + serves)
print('5. Starting auth (auth_server.py)...')
run(f"cd {BASE} && {ENV} nohup python3 -B auth_server.py > /tmp/auth_8081.log 2>&1 &", 3)
time.sleep(8)

# Check auth
out, _ = run("ss -tlnp | grep 8081 || echo 'NO_AUTH'", 2)
if '8081' in out:
    print('   Auth port 8081 listening')
else:
    print('   Auth NOT listening - checking log')
    out, _ = run("tail -30 /tmp/auth_8081.log", 2)
    print(f'   {out[:500]}')

# 6. Start platform + admin
print('6. Starting platform + admin...')
run(f"cd {BASE} && {ENV} nohup python3 -B platform/app.py 8083 > /tmp/platform_8083.log 2>&1 &", 3)
time.sleep(5)
run(f"cd {BASE} && {ENV} nohup python3 -B admin/app.py 8084 > /tmp/admin_8084.log 2>&1 &", 3)
time.sleep(5)

# 7. Wait and verify
print('7. Waiting 15s...')
time.sleep(15)

out, _ = run("ss -tlnp | grep -E '808[134]' || echo 'NO_PORTS'", 2)
print(f'\n8. PORTS:\n{out.strip()}')

for n, p in [('auth', 8081), ('platform', 8083), ('admin', 8084)]:
    out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1", 2)
    print(f'   {n}: {out.strip()}')

# Check logs
for svc, logfile in [('auth', 'auth_8081.log'), ('platform', 'platform_8083.log'), ('admin', 'admin_8084.log')]:
    out, _ = run(f"tail -10 /tmp/{logfile}", 2)
    has_err = 'Traceback' in out
    print(f'\n   {svc} log (last 10 lines):')
    for l in out.strip().split('\n')[-5:]:
        print(f'     {l[:150]}')

s.close()
print('\n=== Done ===')
