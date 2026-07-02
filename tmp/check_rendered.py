#!/usr/bin/env python3
"""Generate token, curl /admin, extract ONLY inline js, node --check"""
import os, subprocess, re, sys

BASE = '/home/easykai/easykai-workspace/easykai.cn'
os.environ['JWT_SECRET'] = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'

sys.path = [BASE + '/admin', BASE + '/auth-center', BASE] + sys.path
os.chdir(BASE + '/admin')

from services.jwt_service import create_token
token = create_token(1, phone='13910604299', is_admin=True)

# curl the page
import urllib.request
req = urllib.request.Request(
    'http://127.0.0.1:8084/admin',
    headers={'Cookie': f'sso_token={token}', 'User-Agent': 'Mozilla/5.0'}
)
resp = urllib.request.urlopen(req, timeout=30)
html = resp.read().decode()

# Extract inline JS only (not <script src=...>)
# Find <script> tag WITHOUT src attribute
matches = list(re.finditer(r'<script[^>]*>', html))
inline = None
for m in matches:
    tag = m.group()
    if 'src=' not in tag:
        inline = m
        break
if not inline:
    print('FAIL: no inline script', file=sys.stderr)
    sys.exit(1)

start = inline.end()
end = html.find('</script>', start)  # first </script> after </script>, not last
js = html[start:end]

path = '/tmp/admin_rendered.cjs'
with open(path, 'w') as f:
    f.write(js)
print(f'JS: {len(js)} bytes')

r = subprocess.run(['node', '--check', path], capture_output=True, text=True)
if r.returncode == 0:
    print('NODE_CHECK: OK')
    os.remove(path)
else:
    print('SYNTAX ERROR')
    print(r.stderr)
    # Show context
    for line in r.stderr.split('\n'):
        if path in line:
            parts = line.split('.cjs:')
            if len(parts) > 1:
                lineno = parts[1].split(':')[0]
                try:
                    ln = int(lineno)
                    ctx = js.split('\n')
                    for i in range(max(0,ln-3), min(len(ctx), ln+2)):
                        mark = '>>' if i == ln-1 else '  '
                        print(f'  {mark} {i+1}: {ctx[i][:250]}')
                except:
                    pass
