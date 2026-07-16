#!/usr/bin/env python3
"""Simple restart script."""
import paramiko, time, os

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

BASE = '/home/easykai/easykai-workspace/easykai.cn'
LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JWT = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'

def run(cmd, wait=5):
    i, o, e = s.exec_command(cmd)
    time.sleep(wait)
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    result = (out + err).strip()
    if result:
        lines = result.split('\n')
        for l in lines[-3:]:
            if l.strip():
                print(f'  {l.strip()[:150]}')
    return out, err

# 1. Upload fixed cms.py
print('=== Upload cms.py ===')
t = s.get_transport()
f = paramiko.SFTPClient.from_transport(t)
f.put(os.path.join(LOCAL, 'auth-center/models/cms.py'),
      os.path.join(BASE, 'auth-center/models/cms.py'))
f.close()
run(f'rm -rf {BASE}/auth-center/models/__pycache__', 1)
print('  done')

# 2. Kill all
print('\n=== Kill ===')
run("pkill -9 -f 'python3' 2>/dev/null", 2)
time.sleep(3)
run("ss -tlnp | grep -E '808[134]' || echo 'all free'", 1)

# 3. Start
print('\n=== Start ===')
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT}"
for n, p, a in [('auth',8081,'auth-center/app.py'),('platform',8083,'platform/app.py'),('admin',8084,'admin/app.py')]:
    run(f"cd {BASE} && {ENV} nohup python3 -B {a} {p} > /tmp/{n}_{p}.log 2>&1 &", 3)
    time.sleep(3)

time.sleep(12)

# 4. Check
print('\n=== Status ===')
ok = True
for n, p in [('auth',8081),('platform',8083),('admin',8084)]:
    code, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1", 2)
    status = "OK" if code.strip() in ('200','302','301','401') else f"FAIL({code.strip()})"
    if 'FAIL' in status: ok = False
    print(f'  {n}: {status}')

if not ok:
    for n in ['platform','admin']:
        out, _ = run(f"tail -15 /tmp/{n}_*.log", 2)
        if 'Traceback' in out or 'Error' in out or 'error' in out:
            print(f'\n=== {n} ERRORS ===')
            for line in out.split('\n'):
                if any(x in line for x in ['Traceback','Error','error','File']):
                    print(f'  {line[:200]}')

s.close()
print('\nDone')
