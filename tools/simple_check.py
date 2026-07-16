#!/usr/bin/env python3
"""Check current server state via single SSH commands."""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

def r(cmd):
    i,o,e = s.exec_command(cmd); time.sleep(3)
    return (o.read().decode(errors='replace') + e.read().decode(errors='replace')).strip()

# Check ports
print('PORTS:')
print(r("ss -tlnp | grep -E '808[134]' || echo 'none'"))

# Check each service
for n,p in [('auth',8081),('platform',8083),('admin',8084)]:
    print(f'\n{n}:')
    print(r(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1 || echo 'fail'"))

# Check admin log for errors  
print('\nADMIN LOG (last 10):')
log = r("tail -10 /tmp/admin_8084.log 2>/dev/null || echo 'no log'")
print(log[:800] if len(log) > 800 else log)

s.close()
