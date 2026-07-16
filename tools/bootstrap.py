#!/usr/bin/env python3
"""Single-shot deploy via base64 bash script on server."""
import paramiko, time, os, base64

LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Build a self-contained server-side script
server_script = r'''#!/bin/bash
set -e
BASE=/home/easykai/easykai-workspace/easykai.cn
JWT=30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d
ENV="PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET=$JWT FLASK_SECRET_KEY=$JWT"

echo "=== PHASE 1: Kill ==="
sudo systemctl stop auth-center.service admin.service 2>/dev/null || true
pkill -9 -f 'python3' 2>/dev/null || true
sleep 2

echo "=== PHASE 2: Clear cache ==="
rm -rf $BASE/auth-center/models/__pycache__
rm -f /tmp/auth_8081.log /tmp/platform_8083.log /tmp/admin_8084.log

echo "=== PHASE 3: Start auth ==="
cd $BASE && $ENV nohup python3 -B auth-center/app.py 8081 > /tmp/auth_8081.log 2>&1 &
sleep 5

echo "=== PHASE 4: Start platform ==="
cd $BASE && $ENV nohup python3 -B platform/app.py 8083 > /tmp/platform_8083.log 2>&1 &
sleep 5

echo "=== PHASE 5: Start admin ==="
cd $BASE && $ENV nohup python3 -B admin/app.py 8084 > /tmp/admin_8084.log 2>&1 &
sleep 5

echo "=== PHASE 6: Wait ==="
sleep 12

echo "=== PHASE 7: Check ==="
for n in auth platform admin; do
  case $n in
    auth) p=8081 ;;
    platform) p=8083 ;;
    admin) p=8084 ;;
  esac
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:$p/ 2>&1)
  echo "$n ($p): $code"
done

echo "=== ADMIN LOG ==="
tail -20 /tmp/admin_8084.log 2>/dev/null || echo "no log"

echo "=== DONE ==="
'''

b64 = base64.b64encode(server_script.encode()).decode('ascii')

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

print('Running deploy script...')
stdin, stdout, stderr = s.exec_command(f"python3 -c \"import base64; exec(base64.b64decode('{b64}').decode())\"")
import time; time.sleep(45)

out = stdout.read().decode(errors='replace')
err = stderr.read().decode(errors='replace')
print(out[-2000:] if len(out) > 2000 else out)
if err:
    print('STDERR:', err[:500])

s.close()
