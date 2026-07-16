"""Deep check: data sources, migration status, error details."""
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
print("1. SQLITE DATA CHECK (未迁移的数据)")
print("="*60)
out, _ = run("for f in /home/easykai/easykai-workspace/easykai.cn/data/*.db /home/easykai/easykai-workspace/easykai.cn/shop.db /home/easykai/easykai-workspace/easykai.cn/auth-center/models/*.db; do if [ -f \"$f\" ]; then echo \"$f ($(stat -c%s $f 2>/dev/null || echo 0) bytes)\"; sqlite3 \"$f\" '.tables' 2>/dev/null | head -5; echo '---'; fi; done", 3)
print(out[:1500])

print("\n" + "="*60)
print("2. AUTH LOG ERRORS (排除INFO)")
print("="*60)
out, _ = run("grep -v 'INFO:werkzeug' /tmp/auth_8081.log | grep -iE 'error|traceback|cannot|exception|warning' | head -20", 2)
if out.strip():
    print(out[:1500])
else:
    print("  No real errors (only werkzeug INFO lines)")

print("\n" + "="*60)
print("3. AUTH HTTP ENDPOINT TEST")
print("="*60)
endpoints = [
    ("GET /", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/"),
    ("GET /login", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/login"),
    ("GET /health", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/health"),
    ("GET /api/users", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/api/users"),
]
for label, cmd in endpoints:
    out, _ = run(cmd, 2)
    print(f"  {label}: {out.strip() or 'TIMEOUT'}")

print("\n" + "="*60)
print("4. PG TABLES LIST")
print("="*60)
out, _ = run(r"PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -t -c \"SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name\" 2>&1", 2)
for line in out.split('\n'):
    if line.strip():
        print(f"  {line.strip()}")

print("\n" + "="*60)
print("5. ADMIN LOG ERRORS")
print("="*60)
out, _ = run("grep -v 'INFO:werkzeug' /tmp/admin_8084.log | grep -iE 'error|traceback|cannot|exception' | head -20", 2)
if out.strip():
    print(out[:1500])
else:
    print("  No real errors")

s.close()
print("\nDone.")
