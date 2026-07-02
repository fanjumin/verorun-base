import json, hmac, hashlib, base64, time
s = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
def b(d): return base64.urlsafe_b64encode(d).rstrip(b'=').decode()
h = b(json.dumps({'alg':'HS256','typ':'JWT'}).encode())
p = json.dumps({'jti':'t'+str(time.time()),'user_id':7,'phone':'13910604299','app_name':'trademind','is_admin':True,'token_type':'access','iat':int(time.time()),'exp':int(time.time())+3600})
pb = b(p.encode())
sg = b(hmac.new(s.encode(),(h+'.'+pb).encode(),hashlib.sha256).digest())
t = h+'.'+pb+'.'+sg
print(t)
