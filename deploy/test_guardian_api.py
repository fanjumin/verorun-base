#!/usr/bin/env python3
"""生成测试 JWT token 并调用 guardian-log 端点"""
import jwt, time, urllib.request, urllib.error, json

SECRET = 'prod-jwt-secret-2026-64charsrequired'
payload = {
    'is_admin': True,
    'user_id': 1,
    'username': 'admin',
    'exp': int(time.time()) + 3600,
    'iat': int(time.time()),
}
token = jwt.encode(payload, SECRET, algorithm='HS256')
print(f'Token: {token[:50]}...')

req = urllib.request.Request(
    'http://127.0.0.1:8085/admin/health/api/guardian-log?lines=5',
    headers={'Authorization': f'Bearer {token}'}
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    print(f'Status: {resp.status}')
    print(f'Total lines: {data.get("total")}')
    for line in data.get('data', []):
        print(f'  {line}')
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()}')
