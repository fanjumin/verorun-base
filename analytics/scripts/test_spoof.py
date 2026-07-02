#!/usr/bin/env python3
import paramiko, time

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Send request to trademind with spoofed X-Forwarded-For (simulating a real user from CN)
# trademind uses ProxyFix which reads X-Forwarded-For
# We connect directly to trademind's port (8081), not through nginx
# Use X-Forwarded-For to simulate a real client IP
print("1. Sending request with spoofed client IP (not 127.0.0.1)...")
stdin, stdout, stderr = ssh.exec_command(
    'curl -s -o /dev/null -w "HTTP %{http_code}\n" '
    '-H "X-Forwarded-For: 114.114.114.114" '
    '-H "X-Forwarded-Proto: https" '
    'http://127.0.0.1:8081/ 2>&1'
)
print('Result:', stdout.read().decode().strip())

time.sleep(1)
stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT id, datetime(timestamp,'unixepoch','localtime'), ip_prefix, country, city, path FROM analytics_logs ORDER BY id DESC LIMIT 3;\""
)
print('\nLatest logs:')
print(stdout.read().decode().strip())

# 2. Also try through nginx (more realistic)
print('\n2. Through nginx with real-looking IP...')
stdin, stdout, stderr = ssh.exec_command(
    'curl -sk -o /dev/null -w "HTTP %{http_code}\n" '
    '-H "X-Forwarded-For: 114.114.114.114" '
    '--resolve "your-server.com:443:127.0.0.1" '
    'https://your-server.com/ 2>&1'
)
print('Result:', stdout.read().decode().strip())

time.sleep(1)
stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT id, datetime(timestamp,'unixepoch','localtime'), ip_prefix, country, city, path FROM analytics_logs ORDER BY id DESC LIMIT 5;\""
)
print('\nLatest logs:')
print(stdout.read().decode().strip())

# Count geo records
stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT COUNT(*) FROM analytics_logs WHERE country != '';\""
)
print('\n有Geo数据的记录:', stdout.read().decode().strip())

# 3. If still no geo, force-test geoip on a real IP from the server directly
print('\n3. Force GeoIP lookup on server...')
stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment && python3 -c \'from analytics.geoip import init_geoip, geoip_lookup; init_geoip(); print(geoip_lookup("114.114.114.114")); print(geoip_lookup("8.8.8.8"))\' 2>&1'
)
print(stdout.read().decode().strip())

ssh.close()
