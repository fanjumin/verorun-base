#!/usr/bin/env python3
"""Final fix: upload cms.py, kill old processes, restart all services."""
import paramiko, time, os

HOST = '***REMOVED***'
BASE = '/home/easykai/easykai-workspace/easykai.cn'
LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JWT_SECRET = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'

SERVICES = [('auth',8081,'auth-center/app.py'),
            ('platform',8083,'platform/app.py'),
            ('admin',8084,'admin/app.py')]

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username='easykai', password='***REMOVED***', timeout=15)

def run(cmd, wait=5):
    i,o,e = c.exec_command(cmd); time.sleep(wait)
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    return (out+err).strip()

# Upload fixed cms.py
print('=== Upload cms.py ===')
transport = c.get_transport()
sftp = paramiko.SFTPClient.from_transport(transport)
sftp.put(os.path.join(LOCAL, 'auth-center/models/cms.py').replace('\\', '/'),
         os.path.join(BASE, 'auth-center/models/cms.py').replace('\\', '/'))
sftp.close()
run(f"rm -rf {BASE}/auth-center/models/__pycache__", 1)
print('  done')

# Kill ALL python processes (including old auth)
print('\n=== Kill all python processes ===')
run("pkill -9 -f 'python3.*app\\.py' 2>/dev/null; sleep 2; echo killed", 3)
# Verify nothing on our ports
for _,port,_ in SERVICES:
    r = run(f"ss -tlnp | grep ':{port}' || echo 'free'", 1)
    print(f"  port {port}: {r[:80]}")

# Start services
print('\n=== Start services ===')
env = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT_SECRET} FLASK_SECRET_KEY={JWT_SECRET}"
for name, port, app in SERVICES:
    log = f"/tmp/{name}_{port}.log"
    run(f"cd {BASE} && rm -f {log} && {env} nohup python3 -B {app} {port} > {log} 2>&1 &", 3)
    time.sleep(4)

time.sleep(10)

# Check status
print('\n=== Service Status ===')
for name, port, _ in SERVICES:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}/ 2>&1", 2)
    status = "OK" if code.strip() in ('200','302','301','401') else f"FAIL({code.strip()})"
    print(f"  {name} (:{port}): {status}")

# Check admin/platform logs for remaining errors
for name in ['platform', 'admin']:
    log = run(f"tail -20 /tmp/{name}_*.log 2>/dev/null", 2)
    if 'Traceback' in log:
        print(f"\n=== {name.upper()} ERROR ===")
        # Extract just the traceback
        for line in log.split('\n'):
            if any(x in line for x in ['Traceback','Error','Error:','FAILED']):
                print(f"  {line[:200]}")

c.close()
