#!/usr/bin/env python3
"""Minimal deploy - no helper functions."""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

JWT='30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT}"
BASE='/home/easykai/easykai-workspace/easykai.cn'

# Step 1: Kill all, clear cache
i,o,e = s.exec_command("sudo systemctl stop auth-center.service admin.service 2>/dev/null; pkill -9 -f python3 2>/dev/null; rm -rf " + BASE + "/auth-center/models/__pycache__; rm -f /tmp/auth_8081.log /tmp/platform_8083.log /tmp/admin_8084.log; echo done")
time.sleep(3)
print('Kill:', o.read().decode(errors='replace')[:200])

# Step 2: Start auth
i,o,e = s.exec_command(f"cd {BASE} && {ENV} nohup python3 -B auth-center/app.py 8081 > /tmp/auth_8081.log 2>&1 & echo STARTED_AUTH")
time.sleep(5)
print('Auth:', o.read().decode(errors='replace')[:200])

# Step 3: Start platform
i,o,e = s.exec_command(f"cd {BASE} && {ENV} nohup python3 -B platform/app.py 8083 > /tmp/platform_8083.log 2>&1 & echo STARTED_PLATFORM")
time.sleep(5)
print('Platform:', o.read().decode(errors='replace')[:200])

# Step 4: Start admin
i,o,e = s.exec_command(f"cd {BASE} && {ENV} nohup python3 -B admin/app.py 8084 > /tmp/admin_8084.log 2>&1 & echo STARTED_ADMIN")
time.sleep(5)
print('Admin:', o.read().decode(errors='replace')[:200])

# Step 5: Wait
time.sleep(15)

# Step 6: Check status
print('\n=== CHECK ===')
for n,p in [('auth',8081),('platform',8083),('admin',8084)]:
    i,o,e = s.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1")
    time.sleep(3)
    print(f'  {n}: {o.read().decode(errors="replace").strip()}')

# Step 7: Admin log
i,o,e = s.exec_command("tail -20 /tmp/admin_8084.log")
time.sleep(3)
log = o.read().decode(errors='replace')
print('\nADMIN LOG:')
if 'Traceback' in log:
    for line in log.split('\n'):
        if 'Error' in line or 'Traceback' in line or 'File' in line:
            print(f'  {line[:200]}')
else:
    print(log[:500])

s.close()
