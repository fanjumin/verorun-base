#!/usr/bin/env python3
"""Kill all, clear cache, start fresh."""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

def r(cmd, wait=3):
    i, o, e = s.exec_command(cmd); time.sleep(wait)
    return (o.read().decode(errors='replace') + e.read().decode(errors='replace')).strip()

BASE = '/home/easykai/easykai-workspace/easykai.cn'
JWT = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT}"

# Kill
r("sudo systemctl stop auth-center.service admin.service 2>/dev/null", 2)
r("pkill -9 -f 'python3' 2>/dev/null", 2)
time.sleep(3)
r("rm -rf /home/easykai/easykai-workspace/easykai.cn/auth-center/models/__pycache__", 2)
r("rm -f /tmp/auth_8081.log /tmp/platform_8083.log /tmp/admin_8084.log", 1)

# Start
for n, p, a in [('auth',8081,'auth-center/app.py'),('platform',8083,'platform/app.py'),('admin',8084,'admin/app.py')]:
    r(f"cd {BASE} && {ENV} nohup python3 -B {a} {p} > /tmp/{n}_{p}.log 2>&1 &", 3)
    time.sleep(5)

time.sleep(12)

# Status
print('=== STATUS ===')
for n, p in [('auth',8081),('platform',8083),('admin',8084)]:
    code = r(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1", 2)
    print(f'  {n}: {code}')

# Admin log if failed
for n in ['platform','admin']:
    log = r(f"tail -15 /tmp/{n}_808*.log", 2)
    if 'Traceback' in log:
        print(f'\n=== {n} ERRORS ===')
        print(log[:1500])

s.close()
