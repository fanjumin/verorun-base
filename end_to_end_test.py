import re, subprocess, json, hmac, hashlib, base64, urllib.request, time

s = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
def b(d): return base64.urlsafe_b64encode(d).rstrip(b'=').decode()
header = b(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
payload = b(json.dumps({
    'jti': 'tv'+str(time.time()), 'user_id': 7, 'phone': '13910604299',
    'app_name': 'trademind', 'is_admin': True, 'token_type': 'access',
    'iat': int(time.time()), 'exp': int(time.time()) + 3600
}).encode())
sig = b(hmac.new(s.encode(), (header + '.' + payload).encode(), hashlib.sha256).digest())
token = header + '.' + payload + '.' + sig

print('=== 1) Platform page render ===')
req = urllib.request.Request('http://127.0.0.1:8083/')
req.add_header('Cookie', 'sso_token=' + token)
resp = urllib.request.urlopen(req, timeout=10)
html = resp.read().decode('utf-8')

print('HTTP', resp.status, '| HTML size:', len(html))
for name, keyword in [
    ('Init function', 'function initUser'),
    ('Profile API call', 'user/profile'),
    ('Menu handler', 'onclick'),
    ('Token in HTML', 'var serverToken'),
    ('Has loading text', 'loading'),
]:
    found = keyword in html
    print(f'  {name}: {"YES" if found else "NO"}')

print()
print('=== 2) Platform APIs with token ===')
for path in ['/user/profile', '/user/usage-history', '/user/coupons', '/session/list']:
    try:
        req = urllib.request.Request('http://127.0.0.1:8083' + path)
        req.add_header('Authorization', 'Bearer ' + token)
        r = urllib.request.urlopen(req, timeout=10)
        d = json.loads(r.read())
        print(f'  {path}: success={d.get("success")}', end='')
        if not d.get('success'):
            print(f' error={d.get("error","")}', end='')
        print()
    except Exception as e:
        print(f'  {path}: ERROR {e}')

print()
print('=== ALL CHECKS DONE ===')
