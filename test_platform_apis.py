import urllib.request, json, hmac, hashlib, base64, time

# Create token using the known JWT_SECRET from systemd
s = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
def b(d): return base64.urlsafe_b64encode(d).rstrip(b'=').decode()
h = b(json.dumps({'alg':'HS256','typ':'JWT'}).encode())
p = json.dumps({
    'jti': 't'+str(time.time()),
    'user_id': 7,
    'phone': '13910604299',
    'app_name': 'trademind',
    'is_admin': True,
    'token_type': 'access',
    'iat': int(time.time()),
    'exp': int(time.time())+3600
}).encode()
pb = b(p)
sg = hmac.new(s.encode(), (h+'.'+pb).encode(), hashlib.sha256).digest()
t = h+'.'+pb+'.'+b(sg)
print("Token created, len:", len(t))

# 1) Test platform index page with cookie
req = urllib.request.Request("http://127.0.0.1:8083/")
req.add_header("Cookie", "sso_token="+t)
resp = urllib.request.urlopen(req, timeout=10)
data = resp.read().decode()
has_serverToken = 'var serverToken' in data
has_mainContent = 'mainContent' in data
print("1) Platform / (8083): HTTP", resp.status, "serverToken:", has_serverToken)

# 2) Test user/profile
req2 = urllib.request.Request("http://127.0.0.1:8083/user/profile")
req2.add_header("Authorization", "Bearer "+t)
resp2 = urllib.request.urlopen(req2, timeout=10)
d2 = json.loads(resp2.read())
print("2) /user/profile (8083): success=", d2.get("success"))

# 3) Test user/usage-history
req3 = urllib.request.Request("http://127.0.0.1:8083/user/usage-history")
req3.add_header("Authorization", "Bearer "+t)
resp3 = urllib.request.urlopen(req3, timeout=10)
d3 = json.loads(resp3.read())
print("3) /user/usage-history: success=", d3.get("success"))

# 4) Test user/coupons
req4 = urllib.request.Request("http://127.0.0.1:8083/user/coupons")
req4.add_header("Authorization", "Bearer "+t)
try:
    resp4 = urllib.request.urlopen(req4, timeout=10)
    d4 = json.loads(resp4.read())
    print("4) /user/coupons: success=", d4.get("success"))
except Exception as e:
    print("4) /user/coupons ERROR:", e)

# 5) Test session/list
req5 = urllib.request.Request("http://127.0.0.1:8083/session/list")
req5.add_header("Authorization", "Bearer "+t)
resp5 = urllib.request.urlopen(req5, timeout=10)
d5 = json.loads(resp5.read())
print("5) /session/list: success=", d5.get("success"))

# 6) Test user/orders
req6 = urllib.request.Request("http://127.0.0.1:8083/user/orders")
req6.add_header("Authorization", "Bearer "+t)
resp6 = urllib.request.urlopen(req6, timeout=10)
d6 = json.loads(resp6.read())
print("6) /user/orders: success=", d6.get("success"))

# 7) Test user/tickets
req7 = urllib.request.Request("http://127.0.0.1:8083/user/tickets")
req7.add_header("Authorization", "Bearer "+t)
resp7 = urllib.request.urlopen(req7, timeout=10)
d7 = json.loads(resp7.read())
print("7) /user/tickets: success=", d7.get("success"))
