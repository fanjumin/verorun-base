#!/usr/bin/env python3
"""Find the real models import path."""
import subprocess
# The site_builder/routes.py imports: from models import get_db
# Let's see what Python actually resolves
r = subprocess.run(['plink', '-ssh', '-pw', '***REMOVED***', '-batch', 'easykai@***REMOVED***',
    "cd /home/easykai/easykai-workspace/easykai.cn/admin && python3 -c 'import sys; sys.path.insert(0,\".\"); sys.path.insert(0,\"..\"); import models; print(models.__file__); print(hasattr(models,\"get_db\"))' 2>&1 | tail -5"],
    capture_output=True, timeout=30)
print(r.stdout.decode('utf-8', errors='replace'))
err = r.stderr.decode('utf-8', errors='replace')
if err: print('ERR:', err[:300])
