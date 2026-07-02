import urllib.request, json, hmac, hashlib, base64, time
s = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
def b(d): return base64.urlsafe_b64encode(d).rstrip(b'=').decode()
h = b(json.dumps({'alg':'HS256','typ':'JWT'}).encode())
p = json.dumps({'jti':'t'+str(time.time()),'user_id':7,'phone':'13910604299','app_name':'trademind','is_admin':True,'token_type':'access','iat':int(time.time()),'exp':int(time.time())+3600}).encode()
pb = b(p)
sg = hmac.new(s.encode(),(h+'.'+pb).encode(),hashlib.sha256).digest()
t = h+'.'+pb+'.'+b(sg)

# 1) Verify home page with ?token= sets the cross-subdomain cookie
req = urllib.request.Request('http://127.0.0.1:8081/?token='+t)
resp = urllib.request.urlopen(req, timeout=10)
ck = resp.getheader('Set-Cookie','NONE')
print('1) Home page ?token=:')
print('   Set-Cookie:', ck[:200] if ck != 'NONE' else 'NONE')
print('   HTTP:', resp.status, '\n')

# 2) Verify platform page reads the cookie properly
req2 = urllib.request.Request('http://127.0.0.1:8083/')
req2.add_header('Cookie', 'sso_token='+t)
resp2 = urllib.request.urlopen(req2, timeout=10)
data = resp2.read().decode()
has_serverToken = 'var serverToken' in data
has_token_in_html = t[:30] in data
print('2) Platform with cookie:')
print('   HTTP:', resp2.status)
print('   Has var serverToken:', has_serverToken)
print('   Token embedded:', has_token_in_html)
print('   URL:', resp2.geturl())
