#!/usr/bin/env python3
import paramiko

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Test the full login flow: login, get token, access /admin/dashboard
# 1. Login with SMS (phone login) 
print("=== 1. Login to get token ===")
stdin, stdout, stderr = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8084/user/sms/login '
    '-H "Content-Type: application/json" '
    '-d \'{"phone":"13910604299","code":"test123"}\' 2>&1'
)
print(stdout.read().decode().strip()[:500])

# 2. Test /admin/dashboard with a token - need to get a valid one first
# Let me check the login endpoint to understand the auth flow
print("\n=== 2. Check login endpoint ===")
stdin, stdout, stderr = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8084/user/password/login '
    '-H "Content-Type: application/json" '
    '-d \'{"phone":"13910604299","password":"admin123"}\' 2>&1'
)
login_resp = stdout.read().decode().strip()
print(login_resp[:500])

# Extract token if available
import json
try:
    data = json.loads(login_resp)
    if data.get('success') and data.get('data', {}).get('token'):
        token = data['data']['token']
        print(f"\nToken: {token[:50]}...")
        
        # Test /admin/dashboard with this token
        print("\n=== 3. Test /admin/dashboard ===")
        stdin, stdout, stderr = ssh.exec_command(
            f'curl -s -H "Authorization: Bearer {token}" http://127.0.0.1:8084/admin/dashboard 2>&1'
        )
        print(stdout.read().decode().strip()[:500])
        
        # Test /admin/analytics/ with this token
        print("\n=== 4. Test /admin/analytics/ ===")
        stdin, stdout, stderr = ssh.exec_command(
            f'curl -s -H "Authorization: Bearer {token}" http://127.0.0.1:8084/admin/analytics/ 2>&1 | head -5'
        )
        print(stdout.read().decode().strip()[:500])
        
        # Test /admin/analytics/api/v1/geo with this token
        print("\n=== 5. Test /admin/analytics/api/v1/geo ===")
        stdin, stdout, stderr = ssh.exec_command(
            f'curl -s -H "Authorization: Bearer {token}" http://127.0.0.1:8084/admin/analytics/api/v1/geo?days=30 2>&1'
        )
        print(stdout.read().decode().strip()[:500])
except:
    pass

ssh.close()
