#!/usr/bin/env python3
"""Upload and run check script on server via paramiko"""
import paramiko, os

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

local_path = '/tmp/check_geo_data.py'
remote_path = '/home/easykai/check_geo_data.py'
sftp.put(local_path, remote_path)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment && python3 /home/easykai/check_geo_data.py 2>&1'
)
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out)
if err:
    print('STDERR:', err)

ssh.exec_command('rm /home/easykai/check_geo_data.py')
ssh.close()
