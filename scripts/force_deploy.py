#!/usr/bin/env python3
"""Force upload manager.py and routes.py then restart"""
import paramiko, time

HOST = '***REMOVED***'; USER = 'easykai'; PASS = '***REMOVED***'
ROOT = '/home/easykai/easykai-workspace/easykai.cn'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

# Read local files and write directly
files = {
    'plugin_manager/manager.py': r'F:\Sites\VeroRun\plugin_manager\manager.py',
    'plugin_manager/routes.py': r'F:\Sites\VeroRun\plugin_manager\routes.py',
}

for remote_name, local_path in files.items():
    remote_path = ROOT + '/' + remote_name
    with open(local_path, 'rb') as f:
        sftp.putfo(f, remote_path)
    print(f'Uploaded {remote_name} ({remote_path})')

sftp.close()

# Kill and restart
ssh.exec_command('fuser -k 8084/tcp 2>/dev/null')
ssh.exec_command('pkill -9 -f admin/app.py 2>/dev/null')
time.sleep(3)
stdin, out, err = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep | wc -l')
print(f'After kill: {out.read().decode().strip()} processes')

cmd = f'cd {ROOT} && JWT_SECRET=easykai_jwt_secret_2026 nohup python3 admin/app.py > /tmp/admin6.log 2>&1 &'
stdin, out, err = ssh.exec_command(cmd)
time.sleep(6)

stdin, out, err = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep | head -2')
proc = out.read().decode().strip()
print(f'Process: {"RUNNING" if proc else "DEAD"}')
if proc: print(proc[:200])

time.sleep(3)
stdin, out, err = ssh.exec_command('curl -s http://localhost:8084/admin/plugins/discover')
print(f'Discover: {out.read().decode()[:500]}')

stdin, out, err = ssh.exec_command('tail -15 /tmp/admin6.log')
print(f'Log:\n{out.read().decode()[:800]}')

ssh.close()
