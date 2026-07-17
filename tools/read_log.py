import paramiko, time

HOST = '***REMOVED***'
USER = 'easykai'
PASS = '***REMOVED***'

t = paramiko.Transport((HOST, 22))
t.connect(username=USER, password=PASS)
s = t.open_session()
s.exec_command('tail -20 /tmp/admin_8084.log 2>/dev/null; echo "==="; lsof -i :8084 2>/dev/null')
time.sleep(2)
out = s.makefile('rb').read().decode()
print(out)
s.close(); t.close()
