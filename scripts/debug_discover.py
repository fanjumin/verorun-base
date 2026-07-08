#!/usr/bin/env python3
"""Debug discover on remote server - step by step"""
import paramiko, time, json

HOST = '***REMOVED***'
USER = 'easykai'
PASS = '***REMOVED***'
ROOT = '/home/easykai/easykai-workspace/easykai.cn'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

# Kill everything
ssh.exec_command('fuser -k 8084/tcp 2>/dev/null')
ssh.exec_command('pkill -9 -f admin/app.py 2>/dev/null')
time.sleep(2)

# Check no process
stdin, out, err = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep | wc -l')
print(f'Processes: {out.read().decode().strip()}')

# Port check
stdin, out, err = ssh.exec_command('ss -tlnp | grep 8084 || echo FREE')
print(f'Port 8084: {out.read().decode().strip()}')

# Plugin directory listing
stdin, out, err = ssh.exec_command(f'ls -la {ROOT}/plugins/')
print(f'\nPlugins dir:\n{out.read().decode().strip()}')

# Check each plugin's files
for p in ['ali_api', 'coupons', 'reviews', 'wishlist', 'order_notify']:
    stdin, out, err = ssh.exec_command(f'ls -la {ROOT}/plugins/{p}/__init__.py {ROOT}/plugins/{p}/plugin.json 2>&1')
    files = out.read().decode().strip()
    ok = 'No such' not in files
    print(f'  {p}: {"OK" if ok else "MISSING"}')
    if not ok:
        print(f'    {files[:200]}')

# Direct discover test with python3 via heredoc
discover_script = """
import sys, os
sys.path.insert(0, '/home/easykai/easykai-workspace/easykai.cn')
from plugin_manager.discovery import PluginDiscovery

d = PluginDiscovery()
# Test without dir
r1 = d.discover()
print(f'TEST1 (no dir): {r1}')

# Set dir
d.set_plugins_dir('/home/easykai/easykai-workspace/easykai.cn/plugins')
r2 = d.discover()
print(f'TEST2 (with dir): count={len(r2)}')
for p in r2:
    print(f'  - {p.identifier} v{p.version}')
""".strip()

stdin, out, err = ssh.exec_command(f'cd {ROOT} && python3 << "EOF"\n{discover_script}\nEOF')
print(f'\nDirect discover test:')
print(out.read().decode().strip())
err_out = err.read().decode().strip()
if err_out:
    print(f'STDERR: {err_out[:500]}')

# Start fresh admin
stdin, out, err = ssh.exec_command(
    f'cd {ROOT} && JWT_SECRET=easykai_jwt_secret_2026 nohup python3 admin/app.py > /tmp/admin3.log 2>&1 &'
)
time.sleep(5)

# Check process
stdin, out, err = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep')
proc = out.read().decode().strip()
print(f'\nAdmin: {"RUNNING" if proc else "DEAD"}')
if proc:
    print(f'  {proc[:200]}')

# Test API
time.sleep(2)
stdin, out, err = ssh.exec_command('curl -s http://localhost:8084/admin/plugins/discover 2>&1')
disc = out.read().decode().strip()[:500]
print(f'Discover API: {disc}')

stdin, out, err = ssh.exec_command('curl -s http://localhost:8084/admin/plugins 2>&1')
lst = out.read().decode().strip()[:300]
print(f'List API: {lst}')

# Check log
stdin, out, err = ssh.exec_command('grep -i plugin /tmp/admin3.log | tail -10')
print(f'\nPlugin log:\n{out.read().decode().strip()[:500]}')

ssh.close()
