#!/usr/bin/env python3
"""Quick check current state."""
import paramiko, time
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('***REMOVED***',username='easykai',password='***REMOVED***',timeout=15)
def r(c,w=5):
    i,o,e=c.exec_command(c);time.sleep(w)
    return (o.read().decode()+e.read().decode()).strip()

# Start fresh - kill everything
print('Kill all...')
r("pkill -9 -f 'python3.*app\\.py' 2>/dev/null; sleep 2", 3)

JWT='30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT}"
BASE='/home/easykai/easykai-workspace/easykai.cn'

for n,p,a in [('auth',8081,'auth-center/app.py'),('platform',8083,'platform/app.py'),('admin',8084,'admin/app.py')]:
    r(f"cd {BASE} && rm -f /tmp/{n}_{p}.log",1)
    r(f"cd {BASE} && {ENV} nohup python3 -B {a} {p} > /tmp/{n}_{p}.log 2>&1 &",3)

time.sleep(12)

print('\n=== Status ===')
for n,p in [('auth',8081),('platform',8083),('admin',8084)]:
    code = r(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1",2)
    print(f'  {n}: {code}')

for name in ['platform','admin']:
    log = r(f"tail -15 /tmp/{name}_*.log",2)
    if 'Traceback' in log:
        print(f'\n=== {name} ERROR ===')
        for l in log.split('\n'):
            if any(x in l for x in ['Error','error','Traceback','File']):
                print(f'  {l[:200]}')

c.close()
