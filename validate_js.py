import re, subprocess, json, hmac, hashlib, base64, urllib.request, time, sys

# Create a valid JWT token
s = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'

def b(d): return base64.urlsafe_b64encode(d).rstrip(b'=').decode()
header = b(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
payload_data = {
    'jti': 'tv' + str(time.time()),
    'user_id': 7,
    'phone': '13910604299',
    'app_name': 'trademind',
    'is_admin': True,
    'token_type': 'access',
    'iat': int(time.time()),
    'exp': int(time.time()) + 3600
}
payload = b(json.dumps(payload_data).encode())
signature = b(hmac.new(s.encode(), (header + '.' + payload).encode(), hashlib.sha256).digest())
token = header + '.' + payload + '.' + signature

# Render the platform page by making HTTP request with cookie
req = urllib.request.Request('http://127.0.0.1:8083/')
req.add_header('Cookie', 'sso_token=' + token)
resp = urllib.request.urlopen(req, timeout=10)
html = resp.read().decode('utf-8')

# Extract JS blocks from rendered HTML (no Jinja tags)
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f'Rendered HTML: {len(html)} bytes, {len(scripts)} script blocks')

all_ok = True
for i, s in enumerate(scripts):
    clean = s.strip()
    if len(clean) > 50:  # skip empty/trivial scripts
        js_file = f'/tmp/rjs_{i}.js'
        open(js_file, 'w', encoding='utf-8').write(clean)
        result = subprocess.run(['node', '--check', js_file], capture_output=True, text=True)
        status = 'OK' if result.returncode == 0 else 'SYNTAX ERROR'
        if result.returncode != 0:
            all_ok = False
        print(f'  Script {i} ({len(clean)} chars): {status}', end='')
        if result.returncode != 0:
            # Show the exact problematic spot
            err_line = ''
            for line in result.stderr.split('\n'):
                if '^' in line:
                    err_line = line.strip()
                    break
            print(f'  Error detail: {result.stderr[:300]}')
        else:
            print()

if all_ok:
    print('\n=== ALL JS BLOCKS VALID ===')
    sys.exit(0)
else:
    print('\n=== JS SYNTAX ERRORS DETECTED ===')
    sys.exit(1)
