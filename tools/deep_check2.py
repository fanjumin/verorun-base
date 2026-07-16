"""Deep dive into login 500 and error details."""
import paramiko, time

HOST = '***REMOVED***'
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(HOST, username='easykai', password='***REMOVED***', timeout=15, allow_agent=False, look_for_keys=False)

def run(cmd, wait=3):
    c2 = s.get_transport().open_session()
    c2.exec_command(cmd)
    time.sleep(wait)
    out = b''
    while c2.recv_ready(): out += c2.recv(4096)
    err = b''
    while c2.recv_stderr_ready(): err += c2.recv_stderr(4096)
    c2.close()
    return out.decode(errors='replace'), err.decode(errors='replace')

print("="*60)
print("1. LOGIN 500 — full traceback")
print("="*60)
out, _ = run("grep -A 50 '500' /tmp/auth_8081.log | head -60", 2)
print(out[:2000])

# Check if it's a route issue
print("\n" + "="*60)
print("2. AUTH ROUTES (login endpoint)")
print("="*60)
out, _ = run("grep -n 'def login\|@.*route.*login\|route.*login' /home/easykai/easykai-workspace/easykai.cn/auth-center/routes/auth.py 2>/dev/null | head -10", 2)
print(out[:1000])

print("\n" + "="*60)
print("3. Admin stack trace (executescript error)")
print("="*60)
out, _ = run("grep -A 30 'executescript' /tmp/admin_8084.log | head -40", 2)
print(out[:1500])

print("\n" + "="*60)
print("4. Admin syntax error at or near ','")
print("="*60)
out, _ = run("grep -B 5 -A 15 'syntax error at or near' /tmp/admin_8084.log | head -40", 2)
print(out[:1500])

print("\n" + "="*60)
print("5. Login request details")
print("="*60)
out, _ = run("curl -s -w '\nHTTP: %{http_code}\n' -X POST http://localhost:8081/login -H 'Content-Type: application/json' -d '{\"phone\":\"13800138000\",\"password\":\"admin123\"}' 2>&1", 3)
print(out[:500])

s.close()
