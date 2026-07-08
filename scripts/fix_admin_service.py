#!/usr/bin/env python3
"""Fix admin service: force sync files, install deps, restart"""
import paramiko, os, time

HOST = '***REMOVED***'
USER = 'easykai'
PASS = '***REMOVED***'
ROOT = '/home/easykai/easykai-workspace/easykai.cn'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

# 1. Force sync admin/app.py
local_admin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'app.py')
sftp.put(local_admin, f'{ROOT}/admin/app.py')
print(f'1. Uploaded admin/app.py ({os.path.getsize(local_admin)} bytes)')

# 2. Force sync plugin_manager/base.py + event_bus.py (new files that deploy may have missed)
local_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin_manager', 'base.py')
local_eb = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin_manager', 'event_bus.py')
sftp.put(local_base, f'{ROOT}/plugin_manager/base.py')
sftp.put(local_eb, f'{ROOT}/plugin_manager/event_bus.py')
print(f'2. Uploaded plugin_manager/base.py + event_bus.py')

# 3. Fix platform/__init__.py shadowing stdlib
ssh.exec_command(f'rm -f {ROOT}/platform/__init__.py')
print('3. Deleted platform/__init__.py (was shadowing stdlib)')

# 4. Kill old admin
ssh.exec_command('pkill -f "admin/app.py" 2>/dev/null')
time.sleep(1)

# 5. Install flask-cors if needed (system Python with PEP 668)
stdin, stdout, stderr = ssh.exec_command('pip3 install --break-system-packages flask-cors flask-limiter 2>&1 | tail -3')
print(f'4. Install deps: {stdout.read().decode().strip()}')

# 6. Restart with JWT_SECRET
cmd = f'export JWT_SECRET=easykai_jwt_secret_2026 && cd {ROOT} && nohup python3 admin/app.py > /tmp/admin.log 2>&1 &'
ssh.exec_command(cmd)
time.sleep(5)

# 7. Check process
stdin, stdout, stderr = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep')
proc = stdout.read().decode().strip()
print(f'5. Admin process: {"RUNNING" if proc else "NOT RUNNING"}')

# 8. Check log
stdin, stdout, stderr = ssh.exec_command('tail -15 /tmp/admin.log')
log = stdout.read().decode().strip()
print(f'6. Log tail:\n{log}')

sftp.close()
ssh.close()
