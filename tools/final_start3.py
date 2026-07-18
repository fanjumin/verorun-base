#!/usr/bin/env python3
"""Check and fix admin."""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

def run(c, w=5):
    i,o,e = s.exec_command(c); time.sleep(w)
    return (o.read().decode(errors='replace') + e.read().decode(errors='replace')).strip()

# Check cms.py content
print('=== cms.py line 133-136 ===')
print(run("sed -n '133,136p' /home/easykai/easykai-workspace/easykai.cn/auth-center/models/cms.py"))

# If still has OVERRIDING, fix with sed
has_override = run("grep -c 'OVERRIDING' /home/easykai/easykai-workspace/easykai.cn/auth-center/models/cms.py 2>/dev/null")
if has_override.strip() != '0':
    print('\n=== Fixing via sed ===')
    run("sed -i 's/OVERRIDING SYSTEM VALUE //' /home/easykai/easykai-workspace/easykai.cn/auth-center/models/cms.py", 2)
    run("rm -rf /home/easykai/easykai-workspace/easykai.cn/auth-center/models/__pycache__(", 1)
    print('  fixed!')
    run(")sed -n '133,136p' /home/easykai/easykai-workspace/easykai.cn/auth-center/models/cms.py")
else:
    print('  already fixed')

# Kill auth (systemd keeps restarting it)
print('\n=== Kill ALL ===')
run("sudo systemctl stop auth-center.service admin.service 2>/dev/null", 2)
run("pkill -9 -f 'python3' 2>/dev/null", 2)
time.sleep(3)
print(run("ss -tlnp | grep -E '808[134]' || echo 'all free'", 1))

# Start
JWT = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT}"
BASE = '/home/easykai/easykai-workspace/easykai.cn'

print('\n=== Start ===')
for n, p, a in [('auth',8081,'auth-center/app.py'),('platform',8083,'platform/app.py'),('admin',8084,'admin/app.py')]:
    run(f"cd {BASE} && {ENV} nohup python3 -B {a} {p} > /tmp/{n}_{p}.log 2>&1 &", 3)
    time.sleep(3)

time.sleep(12)

# Check
print('\n=== Status ===')
for n, p in [('auth',8081),('platform',8083),('admin',8084)]:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1", 2)
    print(f'  {n}: {code}')

# Errors
for n in ['platform','admin']:
    log = run(f"tail -20 /tmp/{n}_*.log", 2)
    if 'Traceback' in log or 'Error' in log:
        print(f'\n=== {n} ===')
        for l in log.split('\n'):
            if any(x in l for x in ['Error','error','Traceback']):
                print(f'  {l[:200]}')

s.close()
