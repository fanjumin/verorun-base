#!/usr/bin/env python3
"""Simple status check."""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

def run(c, w=3):
    i,o,e = s.exec_command(c); time.sleep(w)
    return (o.read().decode() + e.read().decode()).strip()

BASE = '/home/easykai/easykai-workspace/easykai.cn'
JWT = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT}"

# Kill old processes
run("sudo systemctl stop auth-center.service admin.service 2>/dev/null", 2)
run("pkill -9 -f 'python3' 2>/dev/null", 2)
time.sleep(2)

# Start all 3 services  
for n, p, a in [('auth',8081,'auth-center/app.py'),('platform',8083,'platform/app.py'),('admin',8084,'admin/app.py')]:
    run(f"cd {BASE} && rm -f /tmp/{n}_{p}.log && {ENV} nohup python3 -B {a} {p} > /tmp/{n}_{p}.log 2>&1 &", 3)
    time.sleep(4)

time.sleep(10)

# Check
print('=== STATUS ===')
for n, p in [('auth',8081),('platform',8083),('admin',8084)]:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1", 2)
    print(f'  {n}: {code}')

# Admin log
print('\n=== ADMIN LOG (last 15) ===')
print(run("tail -15 /tmp/admin_8084.log", 2)[:1000])

s.close()
