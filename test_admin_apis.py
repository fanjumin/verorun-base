import json, hmac, hashlib, base64, time, urllib.request

s = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
def b(d): return base64.urlsafe_b64encode(d).rstrip(b'=').decode()
h = b(json.dumps({'alg':'HS256','typ':'JWT'}).encode())
p = json.dumps({'jti':'t'+str(time.time()),'user_id':7,'phone':'13910604299','app_name':'trademind','is_admin':True,'token_type':'access','iat':int(time.time()),'exp':int(time.time())+3600})
pb = b(p.encode())
sg = b(hmac.new(s.encode(),(h+'.'+pb).encode(),hashlib.sha256).digest())
t = h+'.'+pb+'.'+sg

# Test: admin page via Authorization header (which admin_page also checks)
req = urllib.request.Request('http://127.0.0.1:8084/admin')
req.add_header('Authorization', 'Bearer '+t)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode('utf-8')
    print(f'HTTP {resp.status}, HTML: {len(html)} bytes')
    
    # Check for token in response
    if len(html) > 500:
        print('Admin page rendered successfully!')
        
        # Validate JS
        import re, subprocess
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        errors = []
        for i, s in enumerate(scripts):
            clean = s.strip()
            if len(clean) > 50:
                f = '/tmp/ajs2_'+str(i)+'.js'
                open(f, 'w', encoding='utf-8').write(clean)
                r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
                status = 'OK' if r.returncode == 0 else 'SYNTAX ERROR'
                print(f'  Script {i} ({len(clean)} chars): {status}')
                if r.returncode != 0:
                    errors.append((i, r.stderr))
        if not errors:
            print('\n=== ALL ADMIN JS BLOCKS VALID ===')
        else:
            for i, err in errors:
                for line in err.split('\n'):
                    if 'SyntaxError' in line:
                        print(f'  [{i}] {line.strip()}')
    else:
        print(f'  Redirect target: {html[:200]}')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {str(e)[:200]}')
