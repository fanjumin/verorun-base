#!/usr/bin/env python3
import paramiko

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Test geoip_lookup with a real external IP (Google DNS, 8.8.8.8 is US)
stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment && python3 -B -c \'from analytics.geoip import init_geoip, geoip_lookup; init_geoip(); print(geoip_lookup("8.8.8.8")); print(geoip_lookup("114.114.114.114"))\' 2>&1'
)
print('GeoIP test:', stdout.read().decode().strip())

# Verify the admin app.py has GeoIP init in its logs (check startup message)
stdin, stdout, stderr = ssh.exec_command(
    'grep -i "geoip\|geo" /proc/$(pgrep -f "app.py 8084")/fd/1 2>/dev/null; '
    'echo "---"; '
    'ps aux | grep app.py | grep -v grep'
)
print(f'Process check:\n{stdout.read().decode().strip()}')

ssh.close()
