#!/usr/bin/env python3
import paramiko, time

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Step 1: Send test requests (quick)
print("Sending test requests...")
for url in [
    'https://your-server.com/',
    'https://your-server.com/',
]:
    stdin, stdout, stderr = ssh.exec_command(f'curl -sk -o /dev/null -w "%{{http_code}}" --connect-timeout 5 --max-time 10 {url} 2>&1')
    code = stdout.read().decode().strip()
    print(f'  {url} -> HTTP {code}')
    time.sleep(0.5)

# Step 2: Wait + check logs
time.sleep(2)
cmd = "sqlite3 /path/to/deployment/data/site.db \"SELECT id, datetime(timestamp,'unixepoch','localtime'), ip_prefix, country, city, path FROM analytics_logs ORDER BY id DESC LIMIT 5;\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print('\n=== 最新日志 ===')
print(stdout.read().decode().strip())

cmd2 = "sqlite3 /path/to/deployment/data/site.db \"SELECT COUNT(*) FROM analytics_logs WHERE country != '';\""
stdin, stdout, stderr = ssh.exec_command(cmd2)
print('\n有Geo数据的记录:', stdout.read().decode().strip())

# Step 3: Check if community or platform have middleware registered (by looking at app.py)
for svc in ['platform']:
    stdin, stdout, stderr = ssh.exec_command(f'grep -n "AnalyticsMiddleware" /path/to/deployment/{svc}/app.py 2>&1')
    out = stdout.read().decode().strip()
    print(f'\n{svc}/app.py middleware: {out or "(not found)"}')

ssh.close()
