#!/usr/bin/env python3
import paramiko

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp = ssh.open_sftp()
sftp.put('/path/to/local/project/analytics/scripts/make_token.py', '/home/easykai/make_token.py')
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /path/to/deployment && python3 /home/easykai/make_token.py 2>&1')
token = stdout.read().decode().strip()

html = '<html><body><script>\n'
html += 'localStorage.setItem("sso_token", "' + token + '");\n'
html += 'localStorage.setItem("tm_token", "' + token + '");\n'
html += 'localStorage.setItem("token", "' + token + '");\n'
html += 'window.location.href = "/admin";\n'
html += '</script></body></html>'

ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)
sftp2 = ssh2.open_sftp()
remote_path = '/path/to/deployment/admin/static/token_helper.html'
with sftp2.open(remote_path, 'w') as f:
    f.write(html)
sftp2.close()
ssh2.close()
print("DONE: token_helper.html created at", remote_path)

ssh.exec_command('rm /home/easykai/make_token.py')
ssh.close()
