#!/usr/bin/env python3
import paramiko, time

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Hit non-excluded paths on all services to generate logs
print("Sending test requests...")
for url in [
    'https://your-server.com/',
    'https://your-server.com/',
    'https://your-server.com/',
    'https://your-server.com/',
]:
    cmd = f'curl -sk -o /dev/null -w "%{{http_code}}" {url} 2>&1'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    code = stdout.read().decode().strip()
    print(f'  {url} -> HTTP {code}')

# Wait for middleware to write logs
time.sleep(3)

# Check new log entries
stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT id, datetime(timestamp,'unixepoch','localtime'), ip_prefix, country, city, path FROM analytics_logs ORDER BY id DESC LIMIT 5;\""
)
print("\n=== 最新日志 ===")
print(stdout.read().decode().strip())

# Check geo data specifically
stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT COUNT(*) FROM analytics_logs WHERE country != '';\""
)
count = stdout.read().decode().strip()
print(f"\n有Geo数据的记录: {count}")

# Now let's directly test the middleware behavior by checking 
# whether the middleware is actually calling geoip_lookup
# Check service startup logs for GeoIP init message
stdin, stdout, stderr = ssh.exec_command("""
for p in 8084 8083 8082 8081; do
  pid=$(ss -tlnp | grep ":$p" | grep -oP 'pid=\\K[0-9]+' | head -1)
  if [ -n "$pid" ]; then
    echo "Service :$p (pid=$pid) - analytics GeoIP check:"
    # Check fd/1 for GeoIP messages
    grep -a 'GeoIP' /proc/$pid/fd/1 2>/dev/null || echo "  (no GeoIP message in stdout)"
    grep -a 'GeoIP' /proc/$pid/fd/2 2>/dev/null || echo "  (no GeoIP message in stderr)"
  fi
done
""")
print("\n=== 各服务 GeoIP 启动日志 ===")
print(stdout.read().decode().strip() or "(empty)")
err = stderr.read().decode().strip()
if err: print('STDERR:', err)

# Check if the middleware even loaded (look for "中间件已注册" message)
stdin, stdout, stderr = ssh.exec_command("""
for p in 8084 8083 8082 8081; do
  pid=$(ss -tlnp | grep ":$p" | grep -oP 'pid=\\K[0-9]+' | head -1)
  if [ -n "$pid" ]; then
    echo "Service :$p (pid=$pid):"
    grep -a 'Analytics' /proc/$pid/fd/1 2>/dev/null | head -3
  fi
done
""")
print("\n=== Analytics 中间件启动日志 ===")
print(stdout.read().decode().strip() or "(empty)")

ssh.close()
