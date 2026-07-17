#!/usr/bin/env python3
"""List tables in the DB to find where cms_blocks lives."""
import subprocess
r = subprocess.run(['plink', '-ssh', '-pw', '***REMOVED***', '-batch', 'easykai@***REMOVED***',
    "sqlite3 /home/easykai/easykai-workspace/data/x7k2m9a4.db '.tables' 2>/dev/null; echo '---'; find /home/easykai/easykai-workspace -name '*.db' 2>/dev/null; echo '---'; grep -r 'cms_blocks\|design_tokens' /home/easykai/easykai-workspace/easykai.cn/site_builder/routes.py 2>/dev/null | head -3; echo '---'; grep -r 'get_db\|DB_PATH\|db\.' /home/easykai/easykai-workspace/easykai.cn/admin/app.py 2>/dev/null | head -10"],
    capture_output=True, timeout=30)
print(r.stdout.decode('utf-8', errors='replace'))
print(r.stderr.decode('utf-8', errors='replace')[:500])
