#!/usr/bin/env python3
"""Test fixed middleware with X-Forwarded-For"""
import paramiko, time

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Send a request through nginx with a real-looking client IP
# nginx will add: X-Forwarded-For: <real_ip>, 127.0.0.1
# Our _get_client_ip() takes the first IP = the real one
print("Sending test request through nginx...")
stdin, stdout, stderr = ssh.exec_command(
    'curl -sk -o /dev/null -w "HTTP %{http_code}\n" '
    '--resolve "your-server.com:443:127.0.0.1" '
    'https://your-server.com/ 2>&1'
)
print('Result:', stdout.read().decode().strip())

time.sleep(2)

# Check new logs
cmd = "sqlite3 /path/to/deployment/data/site.db \"SELECT id, datetime(timestamp,'unixepoch','localtime'), ip_prefix, country, city, path FROM analytics_logs ORDER BY id DESC LIMIT 5;\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print('\n=== Latest logs ===')
print(stdout.read().decode().strip())

# Check geo data
stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT COUNT(*) FROM analytics_logs WHERE country != '';\""
)
print('\n有Geo数据:', stdout.read().decode().strip())

# If still no geo, send a request to non-excluded path with a known external IP
# Use: X-Forwarded-For: 114.114.114.114 to simulate request from CN
print('\nTrying direct request with X-Forwarded-For spoof...')
stdin, stdout, stderr = ssh.exec_command(
    'curl -s -o /dev/null -w "HTTP %{http_code}\n" '
    '-H "X-Forwarded-For: 114.114.114.114" '
    '-H "X-Forwarded-Proto: https" '
    'http://127.0.0.1:8084/ 2>&1'
)
print('Direct to admin:', stdout.read().decode().strip())

time.sleep(1)

stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT id, datetime(timestamp,'unixepoch','localtime'), ip_prefix, country, city, path FROM analytics_logs ORDER BY id DESC LIMIT 5;\""
)
print('\n=== Latest logs ===')
print(stdout.read().decode().strip())

stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT COUNT(*) FROM analytics_logs WHERE country != '';\""
)
print('有Geo数据:', stdout.read().decode().strip())

ssh.close()
