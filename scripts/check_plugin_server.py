#!/usr/bin/env python3
"""Check plugin system state on remote server"""
import paramiko, json

HOST = '***REMOVED***'
USER = 'easykai'
PASS = '***REMOVED***'
ROOT = '/home/easykai/easykai-workspace/easykai.cn'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

results = {}

# 1. Admin process
stdin, out, err = ssh.exec_command('ps aux | grep admin/app.py | grep -v grep')
proc = out.read().decode().strip()
results['admin_running'] = bool(proc)
print(f'1. Admin process: {"RUNNING" if proc else "NOT RUNNING"}')

# 2. Plugin files on server
stdin, out, err = ssh.exec_command(f'ls -la {ROOT}/plugin_manager/')
results['plugin_manager_files'] = out.read().decode().strip()
print(f'2. Plugin manager dir:\n{results["plugin_manager_files"][:400]}')

# 3. Old plugins __init__.py deleted?
stdin, out, err = ssh.exec_command(f'ls -la {ROOT}/plugins/__init__.py 2>&1')
old_init = out.read().decode().strip()
results['old_init_deleted'] = 'No such' in old_init
print(f'3. Old plugins/__init__.py: {"DELETED OK" if results["old_init_deleted"] else "STILL EXISTS"}')

# 4. plugins_dir in app.py
stdin, out, err = ssh.exec_command(f'grep -n "plugins_dir" {ROOT}/admin/app.py')
pd = out.read().decode().strip()
results['plugins_dir_in_app'] = pd[:200]
print(f'4. plugins_dir in app.py: {pd[:200] if pd else "NOT FOUND"}')

# 5. load_plugins in app.py
stdin, out, err = ssh.exec_command(f'grep -n "load_plugins" {ROOT}/admin/app.py')
lp = out.read().decode().strip()
results['load_plugins_removed'] = not lp
print(f'5. load_plugins in app.py: {"REMOVED OK" if not lp else f"STILL: {lp[:200]}"}')

# 6. Discover API
stdin, out, err = ssh.exec_command('curl -s http://localhost:8084/admin/plugins/discover 2>&1')
disc_raw = out.read().decode().strip()
try:
    disc = json.loads(disc_raw)
    results['discover_plugins'] = [p.get('identifier') or p.get('name', '?') for p in (disc if isinstance(disc, list) else disc.get('plugins', []))]
except:
    results['discover_raw'] = disc_raw[:500]
print(f'6. Discover: {results.get("discover_plugins", disc_raw[:200])}')

# 7. List API
stdin, out, err = ssh.exec_command('curl -s http://localhost:8084/admin/plugins 2>&1')
list_raw = out.read().decode().strip()
try:
    lst = json.loads(list_raw)
    results['installed_plugins'] = [p.get('identifier') or p.get('name', '?') for p in (lst if isinstance(lst, list) else lst.get('plugins', []))]
except:
    results['list_raw'] = list_raw[:500]
print(f'7. List: {results.get("installed_plugins", list_raw[:200])}')

# 8. Database check
stdin, out, err = ssh.exec_command("python3 -c \"import sqlite3; c=sqlite3.connect('/home/easykai/easykai-workspace/easykai.cn/instance/verorun.db'); print([r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type=\\'table\\'')])")
print(f'8. DB tables: {out.read().decode()[:300]}')

# 9. App startup log
stdin, out, err = ssh.exec_command(f'tail -30 {ROOT}/admin.log 2>/dev/null || tail -30 /tmp/admin.log 2>/dev/null')
log = out.read().decode().strip()
results['startup_log'] = log[-1000:]
print(f'9. App log tail:\n{log[-1000:]}')

ssh.close()
