#!/usr/bin/env python3
"""Fetch rendered admin page, extract inline JS, save to file (don't delete)"""
import sys, subprocess, re, os, urllib.request

os.environ['JWT_SECRET'] = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
BASE = '/home/easykai/easykai-workspace/easykai.cn'
sys.path = [BASE + '/admin', BASE + '/auth-center', BASE] + sys.path
os.chdir(BASE + '/admin')

from services.jwt_service import create_token
token = create_token(1, phone='13910604299', is_admin=True)

req = urllib.request.Request(
    'http://127.0.0.1:8084/admin',
    headers={'Cookie': f'sso_token={token}', 'User-Agent': 'Mozilla/5.0'}
)
resp = urllib.request.urlopen(req, timeout=30)
html = resp.read().decode()

matches = list(re.finditer(r'<script[^>]*>', html))
for m in matches:
    tag = m.group()
    if 'src=' not in tag:
        start = m.end()
        end = html.find('</script>', start)
        js = html[start:end]

        # Save the full JS for analysis
        outpath = '/tmp/admin_rendered_full.cjs'
        with open(outpath, 'w') as f:
            f.write(js)
        print(f'JS: {len(js)} bytes saved to {outpath}')

        # Also save the HTML for reference
        htmlpath = '/tmp/admin_page.html'
        with open(htmlpath, 'w') as f:
            f.write(html)
        print(f'HTML: {len(html)} bytes saved to {htmlpath}')

        # Check syntax
        r = subprocess.run(['node', '--check', outpath], capture_output=True, text=True)
        if r.returncode == 0:
            print('SYNTAX: OK')
        else:
            print('SYNTAX ERROR:')
            print(r.stderr)

        # Now try to actually evaluate it with Node to find runtime errors
        # Wrap in try-catch to catch first runtime error
        wrapped = (
            'try {\n'
            + js +
            '\n} catch(e) {\n'
            '  console.log("RUNTIME_ERROR:" + e.message);\n'
            '  console.log("STACK:" + e.stack);\n'
            '}\n'
        )
        testpath = '/tmp/admin_runtime_test.cjs'
        with open(testpath, 'w') as f:
            f.write(wrapped)
        r2 = subprocess.run(['node', testpath], capture_output=True, text=True, timeout=10)
        if r2.stdout:
            print('NODE OUTPUT:')
            print(r2.stdout)
        if r2.stderr:
            print('NODE STDERR:')
            print(r2.stderr[:2000])
        break
