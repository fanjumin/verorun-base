#!/usr/bin/env python3
"""Check final deploy status."""
import paramiko, time

HOST = '***REMOVED***'
BASE = '/home/easykai/easykai-workspace/easykai.cn'
JWT_SECRET = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username='easykai', password='***REMOVED***', timeout=15)

def run(cmd, wait=3):
    i,o,e = c.exec_command(cmd); time.sleep(wait)
    return (o.read().decode(errors='replace') + e.read().decode(errors='replace')).strip()

# Data counts
print('=== DATA COUNTS ===')
for label, sql in [("users", "SELECT count(*) FROM users"),
                    ("shop.products", "SELECT count(*) FROM shop.products"),
                    ("site_configs", "SELECT count(*) FROM site_configs"),
                    ("system_config", "SELECT count(*) FROM system_config")]:
    out = run(f"PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -c \"{sql}\" 2>&1", 2)
    count = [l.strip() for l in out.split('\n') if l.strip().isdigit()]
    print(f"  {label}: {count[0] if count else '?'}")

# Start services
print('\n=== START SERVICES ===')
env = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT_SECRET} FLASK_SECRET_KEY={JWT_SECRET}"
for name, port, app in [('auth',8081,'auth-center/app.py'), ('platform',8083,'platform/app.py'), ('admin',8084,'admin/app.py')]:
    run(f"cd {BASE} && {env} nohup python3 -B {app} {port} > /tmp/{name}_{port}.log 2>&1 &", 2)
    time.sleep(3)

time.sleep(10)

# Check services
print('\n=== SERVICE STATUS ===')
for name, port in [('auth',8081),('platform',8083),('admin',8084)]:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}/ 2>&1", 2)
    status = "OK" if code.strip() in ('200','302','301','401') else f"FAIL({code.strip()})"
    print(f"  {name} (:{port}): {status}")

# If admin/platform failed, show logs
for name in ['platform', 'admin']:
    log = run(f"tail -20 /tmp/{name}_*.log 2>/dev/null", 2)
    if log and 'Traceback' in log:
        print(f"\n=== {name.upper()} ERROR ===")
        print(log[:1000])

c.close()
