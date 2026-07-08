#!/usr/bin/env python3
"""Force sync admin/app.py and restart service with JWT_SECRET"""
import paramiko, os, time

HOST = '***REMOVED***'
USER = 'easykai'
PASS = '***REMOVED***'
LOCAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'app.py')
REMOTE = '/home/easykai/easykai-workspace/easykai.cn/admin/app.py'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

sftp = ssh.open_sftp()
sftp.put(LOCAL, REMOTE)
print(f'Uploaded admin/app.py ({os.path.getsize(LOCAL)} bytes)')
sftp.close()

# Check current JWT_SECRET
stdin, stdout, stderr = ssh.exec_command('echo $JWT_SECRET')
jwt = stdout.read().decode().strip()
print(f'Current JWT_SECRET: {"SET" if jwt else "NOT SET"}')

# Kill old admin if any
ssh.exec_command('pkill -f "admin/app.py" 2>/dev/null')
time.sleep(1)

# Fix: delete empty platform/__init__.py that shadows stdlib platform module
ssh.exec_command('rm -f /home/easykai/easykai-workspace/easykai.cn/platform/__init__.py')
print('Deleted empty platform/__init__.py (was shadowing stdlib)')

# Restart with JWT_SECRET using python3
cmd = 'export JWT_SECRET=easykai_jwt_secret_2026 && cd /home/easykai/easykai-workspace/easykai.cn && nohup python3 admin/app.py > /tmp/admin.log 2>&1 &'
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(3)

# Check process
stdin2, stdout2, stderr2 = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep')
proc = stdout2.read().decode().strip()
print(f'Admin process: {"RUNNING" if proc else "NOT RUNNING"}')
if proc:
    print(proc)

# Check log
stdin3, stdout3, stderr3 = ssh.exec_command('tail -5 /tmp/admin.log')
print('--- log tail ---')
print(stdout3.read().decode())

ssh.close()
