#!/usr/bin/env python3
"""Verify GeoIP is working after service restart"""
import paramiko

HOST = '100.124.0.103'
USER = 'easykai'
PASS = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Trigger a request to admin to generate a log entry
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null http://127.0.0.1:8084/analytics/ 2>&1')
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null http://127.0.0.1:8083/ 2>&1')
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null http://127.0.0.1:8082/ 2>&1')

import time
time.sleep(2)

# Check if geo data is now being recorded
stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment && python3 -B -c \'from analytics.models import get_db; db=get_db(); r1=db.execute("SELECT COUNT(*) FROM analytics_logs WHERE country!=\\\"\\\"").fetchone(); r2=db.execute("SELECT COUNT(*) FROM analytics_logs WHERE country=\\\"\\\"").fetchone(); r3=db.execute("SELECT COUNT(*) FROM analytics_logs").fetchone(); print(f"有Geo: {r1[0]}  无Geo: {r2[0]}  总计: {r3[0]}\")'
)
print('Geo data:', stdout.read().decode().strip())

# Also test geoip directly from the admin service dir
stdin, stdout, stderr = ssh.exec_command(
    'cd /path/to/deployment/admin && python3 -B -c \'from analytics.geoip import _find_db, init_geoip; print("DB:",_find_db()); print("Init:",init_geoip())\' 2>&1'
)
print('Admin GeoIP:', stdout.read().decode().strip())

echo_stdin, echo_stdout, echo_stderr = ssh.exec_command('curl -s http://127.0.0.1:8084/admin/analytics/api/v1/geo?days=30 2>&1')
geo_api = echo_stdout.read().decode().strip()
print(f'Geo API: {geo_api[:300] if geo_api else "(empty)"}')

ssh.close()
