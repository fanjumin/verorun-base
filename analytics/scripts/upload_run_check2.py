#!/usr/bin/env python3
"""Upload and run check script"""
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.124.0.103', username='easykai', password='***REMOVED***', look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()
sftp.put('/tmp/check_tmux.py', '/home/easykai/check_tmux.py')
sftp.close()
stdin, stdout, stderr = ssh.exec_command('python3 /home/easykai/check_tmux.py 2>&1')
print(stdout.read().decode().strip())
err = stderr.read().decode().strip()
if err: print('ERR:', err)
ssh.exec_command('rm /home/easykai/check_tmux.py')
ssh.close()
