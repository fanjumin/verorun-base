#!/usr/bin/env python3
"""Restart admin service via plink."""
import subprocess
r = subprocess.run(['plink', '-ssh', '-pw', '***REMOVED***', '-batch', 'easykai@***REMOVED***',
    'echo ***REMOVED*** | sudo -S systemctl restart admin 2>&1 && sleep 2 && systemctl is-active admin 2>&1 && echo "---" && ls -la /home/easykai/easykai-workspace/data/x7k2m9a4.db 2>&1'],
    capture_output=True, timeout=30)
print(r.stdout.decode('utf-8', errors='replace'))
err = r.stderr.decode('utf-8', errors='replace')
if err: print('ERR:', err[:300])
