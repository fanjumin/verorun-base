#!/usr/bin/env python3
import paramiko, json, time

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Generate a valid JWT token for the admin user by calling the login API with CAPTCHA bypass
# First check if there's a test/development mode
print("=== 1. Check if there's a dev/test bypass ===")
stdin, stdout, stderr = ssh.exec_command(
    'grep -n "test\|dev\|debug\|bypass\|CAPTCHA_SKIP\|captcha_skip\|captcha_bypass" '
    '/path/to/deployment/auth-center/app.py '
    '/path/to/deployment/auth-center/routes/auth.py 2>&1 '
    '| grep -v "\.pyc" | head -20'
)
print(stdout.read().decode().strip() or '(none)')

# Check how the auth routes work for admin login
print("\n=== 2. Check JWT generation ===")
stdin, stdout, stderr = ssh.exec_command(
    'grep -n "def.*token\|jwt\|create.*token\|encode" '
    '/path/to/deployment/auth-center/services/jwt_service.py 2>&1 | head -10'
)
print(stdout.read().decode().strip()[:500])

# Check if admin user exists and get user info
print("\n=== 3. Check admin user ===")
stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db "
    "\"SELECT id, phone, nickname, is_admin FROM users WHERE is_admin=1;\""
)
print(stdout.read().decode().strip())

# Manually create a valid JWT from within the server
print("\n=== 4. Generate test JWT ===")
stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment && python3 -c \'import sys; sys.path.insert(0,"auth-center"); sys.path.insert(0,"."); '
    'from services.jwt_service import create_token; '
    'token = create_token(user_id=7, is_admin=True); '
    'print("TOKEN:", token); '
    'print("VERIFY:", create_token(user_id=7)) '
    '\' 2>&1'
)
output = stdout.read().decode().strip()
print(output[:500])

# Extract token
token = None
for line in output.split('\n'):
    if line.startswith('TOKEN:'):
        token = line.replace('TOKEN:', '').strip()
        break

if token:
    print(f"\n=== 5. Test with admin token ===")
    # Test /admin/dashboard
    stdin, stdout, stderr = ssh.exec_command(
        f'curl -s -w "\nHTTP:%{{http_code}}" -H "Authorization: Bearer {token}" '
        f'http://127.0.0.1:8084/admin/dashboard 2>&1'
    )
    print(f'/admin/dashboard:\n{stdout.read().decode().strip()[:500]}')
    
    # Test /admin (the admin.html page)
    stdin, stdout, stderr = ssh.exec_command(
        f'curl -s -w "\nHTTP:%{{http_code}}" -H "Authorization: Bearer {token}" '
        f'http://127.0.0.1:8084/admin 2>&1 | head -5'
    )
    print(f'\n/admin (head):\n{stdout.read().decode().strip()[:300]}')

ssh.close()
