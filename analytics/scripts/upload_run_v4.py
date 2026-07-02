#!/usr/bin/env python3
"""Upload and run check_logs_v3.py on server, show nginx config"""
import paramiko, os

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()

# Upload check script
sftp.put('/path/to/local/project/analytics/scripts/check_logs_v3.py', '/home/easykai/check_logs_v3.py')
sftp.close()

# Run it
stdin, stdout, stderr = ssh.exec_command('cd /home/easykai && python3 check_logs_v3.py 2>&1')
print(stdout.read().decode().strip())
err = stderr.read().decode().strip()
if err:
    print('STDERR:', err)

# Also check nginx config separately
stdin, stdout, stderr = ssh.exec_command('find /etc/nginx -name "*.conf" -o -name "*easykai*" -o -name "*enabled*" 2>/dev/null | head -10')
print('\nNginx config files:', stdout.read().decode().strip())

# Show proxy headers
stdin, stdout, stderr = ssh.exec_command('grep -rn "proxy_set_header\|proxy_pass\|X-Forwarded" /etc/nginx/sites-enabled/ 2>/dev/null | head -30')
print('Nginx proxy settings:')
print(stdout.read().decode().strip() or '(none found)')

# Also check if there's a different nginx config path
stdin, stdout, stderr = ssh.exec_command('ls /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>&1')
print('\nNginx enabled sites:', stdout.read().decode().strip())

ssh.exec_command('rm /home/easykai/check_logs_v3.py')
ssh.close()
