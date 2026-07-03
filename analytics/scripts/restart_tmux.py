#!/usr/bin/env python3
import paramiko, time

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

for name, cmd in [
    ('admin-8084', 'cd /path/to/deployment/admin && python3 -B app.py 8084'),
    ('platform', 'cd /path/to/deployment/platform && python3 -B app.py'),
]:
    stdin, stdout, stderr = ssh.exec_command('tmux kill-session -t ' + name + ' 2>&1')
    time.sleep(0.5)
    stdin, stdout, stderr = ssh.exec_command('tmux new-session -d -s ' + name + ' "' + cmd + '"')
    print('Recreated', name)
    time.sleep(4)

for name, port in [('admin',8084),('platform',8083),('trademind',8081)]:
    stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:' + str(port) + '/ 2>&1')
    code = stdout.read().decode().strip()
    print(f'{name}:{port} -> HTTP {code}')

stdin, stdout, stderr = ssh.exec_command('tmux list-sessions')
print('TMUX:', stdout.read().decode().strip())

ssh.close()
