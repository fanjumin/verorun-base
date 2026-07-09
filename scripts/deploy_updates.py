#!/usr/bin/env python3
"""Upload updated manager.py + routes.py, restart admin, verify"""
import paramiko, time, os

HOST = '***REMOVED***'; USER = 'easykai'; PASS = '***REMOVED***'
ROOT = '/home/easykai/easykai-workspace/easykai.cn'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

local_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in ['plugin_manager/manager.py', 'plugin_manager/routes.py']:
    sftp.put(os.path.join(local_dir, f), os.path.join(ROOT, f))
    print(f'Uploaded {f}')

sftp.close()

ssh.exec_command('pkill -9 -f admin/app.py 2>/dev/null')
time.sleep(2)

stdin, out, err = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep | wc -l')
print(f'After kill: {out.read().decode().strip()} processes')

ssh.exec_command('cd /home/easykai/easykai-workspace/easykai.cn && JWT_SECRET=easykai_jwt_secret_2026 nohup python3 admin/app.py > /tmp/admin5.log 2>&1 &')
time.sleep(6)

stdin, out, err = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep | head -2')
print(f'Running: {out.read().decode().strip()[:200]}')

time.sleep(3)
stdin, out, err = ssh.exec_command('curl -s http://localhost:8084/admin/plugins/discover 2>&1')
disc = out.read().decode().strip()[:500]
print(f'Discover: {disc}')

stdin, out, err = ssh.exec_command('curl -s http://localhost:8084/admin/plugins 2>&1')
lst = out.read().decode().strip()[:300]
print(f'List: {lst}')

stdin, out, err = ssh.exec_command('grep -i "auto_install\\|traceback\\|Error\\|plugin" /tmp/admin5.log | tail -10')
log = out.read().decode().strip()
print(f'Log:\n{log[:600]}')

ssh.close()
