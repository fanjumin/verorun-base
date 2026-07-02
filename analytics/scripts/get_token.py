#!/usr/bin/env python3
import paramiko

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()
sftp.put('/tmp/gen_token.py', '/home/easykai/gen_token.py')
sftp.close()
stdin, stdout, stderr = ssh.exec_command('python3 /home/easykai/gen_token.py 2>&1')
token = stdout.read().decode().strip()
print(token)
ssh.exec_command('rm /home/easykai/gen_token.py')
ssh.close()
