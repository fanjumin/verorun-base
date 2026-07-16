#!/usr/bin/env python3
"""Restart admin service and check."""
import paramiko, time

HOST = '***REMOVED***'
BASE = '/home/easykai/easykai-workspace/easykai.cn'
JWT_SECRET = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username='easykai', password='***REMOVED***', timeout=15)

def r(cmd,w=3):
    i,o,e = c.exec_command(cmd); time.sleep(w)
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    result = (out+err).strip()
    if result: print(result[:500])
    print('---')
    return out, err

# Start admin specifically
env = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT_SECRET} FLASK_SECRET_KEY={JWT_SECRET}"
print('=== Starting admin ===')
r(f"cd {BASE} && {env} nohup python3 -B admin/app.py 8084 > /tmp/admin_8084.log 2>&1 &", 2)
time.sleep(5)

print('=== Admin status ===')
r("curl -s -o /dev/null -w '%{http_code}' http://localhost:8084/ 2>&1", 2)

print('\n=== Admin log ===')
r("cat /tmp/admin_8084.log", 3)

# Final status
print('\n=== Final ports ===')
r("ss -tlnp | grep -E '808[134]'")

print('\n=== Final HTTP ===')
for n,p in [('auth',8081),('platform',8083),('admin',8084)]:
    code = r(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1", 2)[0].strip()
    print(f'  {n} ({p}): {code}')

c.close()
