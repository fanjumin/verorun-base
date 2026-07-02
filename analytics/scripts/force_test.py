#!/usr/bin/env python3
import paramiko, time

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Check server time
stdin, stdout, stderr = ssh.exec_command('date +%s && date')
print("Server time:", stdout.read().decode().strip())

# Check which subdomain routes to which service
stdin, stdout, stderr = ssh.exec_command('grep -n "server_name\|proxy_pass\|listen" /etc/nginx/sites-enabled/easykai.conf | head -40')
print("\nNginx server blocks:")
print(stdout.read().decode().strip())

# Force a request to admin through nginx (your-server.com)
# First check if admin service is responding correctly
stdin, stdout, stderr = ssh.exec_command(
    'curl -sk -w "\nHTTP:%{http_code} Time:%{time_total}s\n" https://your-server.com/admin/analytics/ 2>&1 | tail -5'
)
print("\nRequest to admin/analytics:")
out = stdout.read().decode().strip()
print(out)

# Wait and check for new log entries
time.sleep(1)

stdin, stdout, stderr = ssh.exec_command(
    "sqlite3 /path/to/deployment/data/site.db \"SELECT id, datetime(timestamp,'unixepoch','localtime'), ip_prefix, country, city, path FROM analytics_logs ORDER BY id DESC LIMIT 3;\""
)
print("\nLatest logs:")
print(stdout.read().decode().strip())

# Check if the admin process actually has geoip loaded
stdin, stdout, stderr = ssh.exec_command(
    "grep -a 'GeoIP' /proc/$(pgrep -f 'app.py 8084')/fd/1 2>/dev/null | head -5"
)
print("\nAdmin GeoIP logs:")
out = stdout.read().decode().strip()
print(out or "(no GeoIP messages in admin stderr)")

# Force geoip init and lookup from within the admin service directory
stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment/admin && python3 -c \'import sys; sys.path.insert(0,".."); from analytics.geoip import init_geoip, geoip_lookup; print("GeoIP init:", init_geoip()); print("8.8.8.8:", geoip_lookup("8.8.8.8"))\' 2>&1'
)
print("\nAdmin dir GeoIP test:")
print(stdout.read().decode().strip())

ssh.close()
