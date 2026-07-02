#!/usr/bin/env python3
import paramiko

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# 1. Direct access to /admin/analytics/ without auth → should redirect
print("1. 无鉴权访问 /admin/analytics/")
stdin, stdout, stderr = ssh.exec_command(
    'curl -sk -o /dev/null -w "HTTP %{http_code}  Redirect:%{redirect_url}" https://your-server.com/admin/analytics/ 2>&1'
)
print(' ', stdout.read().decode().strip())

# 2. Direct access to API without auth → should return 401
print("\n2. 无鉴权访问 API")
stdin, stdout, stderr = ssh.exec_command(
    'curl -sk https://your-server.com/admin/analytics/api/v1/geo?days=30 2>&1'
)
print(' ', stdout.read().decode().strip())

# 3. Check if admin page still works (should need auth)
print("\n3. 无鉴权访问 /admin")
stdin, stdout, stderr = ssh.exec_command(
    'curl -sk -o /dev/null -w "HTTP %{http_code}  Redirect:%{redirect_url}" https://your-server.com/admin 2>&1'
)
print(' ', stdout.read().decode().strip())

ssh.close()
