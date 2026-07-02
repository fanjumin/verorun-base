#!/bin/bash
# Generate token, curl admin page, extract inline JS, node --check
set -e

# Create token using Python
JWT_SECRET=30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d
cd /home/easykai/easykai-workspace/easykai.cn/admin

# Generate token
TOKEN=$(python3 -c "
import sys, os
os.environ['JWT_SECRET'] = '$JWT_SECRET'
sys.path = ['/home/easykai/easykai-workspace/easykai.cn/admin',
            '/home/easykai/easykai-workspace/easykai.cn/auth-center',
            '/home/easykai/easykai-workspace/easykai.cn'] + sys.path
os.chdir('/home/easykai/easykai-workspace/easykai.cn/admin')
from services.jwt_service import create_token
print(create_token(1, phone='13910604299', is_admin=True))
")

echo "TOKEN OK: ${#TOKEN} chars"

# Curl admin page
HTML=$(curl -s -m 15 -b "sso_token=$TOKEN" http://127.0.0.1:8084/admin 2>&1)
echo "HTML SIZE: ${#HTML} bytes"

# Extract inline JS - find <script> without src=, extract until next </script>
JS=$(python3 -c "
import re
html = '''$HTML'''
# Find inline script tag
for m in re.finditer(r'<script[^>]*>', html):
    if 'src=' not in m.group():
        start = m.end()
        end = html.find('</script>', start)
        if end > start:
            js = html[start:end]
            print(js, end='')
            break
")

echo "JS SIZE: ${#JS} bytes"

# Save and check
echo "$JS" > /tmp/admin_rendered.cjs
node --check /tmp/admin_rendered.cjs 2>&1
RC=$?
echo "NODE_CHECK EXIT: $RC"
