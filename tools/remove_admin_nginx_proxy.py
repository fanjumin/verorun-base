#!/usr/bin/env python3
"""Remove location /admin/ from Nginx config (run on server as root)."""
import sys

CONF = '/etc/nginx/sites-enabled/easykai.conf'
BACKUP = '/etc/nginx/backups/easykai.conf.bak'

import os

with open(CONF, 'r') as f:
    lines = f.readlines()

# Backup
os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
with open(BACKUP, 'w') as f:
    f.writelines(lines)
print(f'Backup saved to {BACKUP}')

new_lines = []
in_block = False
brace_depth = 0
commented = 0

for line in lines:
    stripped = line.strip()

    # Start of /admin/ block (not /admin/static/)
    if not in_block and stripped.startswith('location') and '/admin/' in stripped and '/admin/static/' not in stripped:
        in_block = True
        brace_depth = stripped.count('{') - stripped.count('}')
        new_lines.append('# ' + line.rstrip() + '  # [commented by remove script]\n')
        commented += 1
        if brace_depth <= 0:
            in_block = False
            brace_depth = 0
        continue

    if in_block:
        brace_depth += stripped.count('{') - stripped.count('}')
        new_lines.append('# ' + line.rstrip() + '\n')
        commented += 1
        if brace_depth <= 0:
            in_block = False
            brace_depth = 0
        continue

    new_lines.append(line)

with open(CONF, 'w') as f:
    f.writelines(new_lines)

print(f'Commented {commented} lines')

# Verify Nginx syntax
import subprocess
result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
if result.returncode == 0:
    print('nginx config syntax OK')
    print('Reloading nginx...')
    subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True)
    print('nginx reloaded successfully')
else:
    print(f'nginx config ERROR: {result.stderr}')
    print('Rolling back...')
    with open(BACKUP, 'r') as f:
        orig = f.read()
    with open(CONF, 'w') as f:
        f.write(orig)
    print('Rolled back to backup')
    sys.exit(1)
