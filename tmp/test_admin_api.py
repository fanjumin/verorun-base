#!/usr/bin/env python3
"""Test admin API endpoints"""
import sys, os, json, urllib.request

BASE = '/home/easykai/easykai-workspace/easykai.cn'
os.environ['JWT_SECRET'] = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
os.environ['DB_PATH'] = BASE + '/instance/x7k2m9a4.db'
sys.path = [BASE + '/admin', BASE + '/auth-center', BASE] + sys.path
os.chdir(BASE + '/admin')

from services.jwt_service import create_token

token = create_token(1, phone='13910604299', is_admin=True)
print('TOKEN:', token[:40], '...')
print('TOKEN_LEN:', len(token))

# Test dashboard
req = urllib.request.Request(
    'http://127.0.0.1:8084/admin/dashboard',
    headers={'Authorization': 'Bearer ' + token}
)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    body = json.loads(resp.read().decode())
    ok = body.get('success')
    print('DASHBOARD: status=%d success=%s' % (resp.status, ok))
    if not ok:
        print('  error:', body.get('error'))
    else:
        d = body.get('data', {})
        print('  users=%d' % d.get('total_users', -1))
except Exception as e:
    print('DASHBOARD FAILED:', str(e)[:200])

# Test users
req2 = urllib.request.Request(
    'http://127.0.0.1:8084/admin/users',
    headers={'Authorization': 'Bearer ' + token}
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=10)
    body2 = json.loads(resp2.read().decode())
    ok2 = body2.get('success')
    print('USERS: status=%d success=%s' % (resp2.status, ok2))
    if not ok2:
        print('  error:', body2.get('error'))
except Exception as e:
    print('USERS FAILED:', str(e)[:200])

# Test page
req3 = urllib.request.Request(
    'http://127.0.0.1:8084/admin',
    headers={'Cookie': 'sso_token=' + token}
)
try:
    resp3 = urllib.request.urlopen(req3, timeout=10)
    html = resp3.read().decode()
    print('ADMIN_PAGE: status=%d size=%d' % (resp3.status, len(html)))
except Exception as e:
    print('ADMIN_PAGE FAILED:', str(e)[:200])
