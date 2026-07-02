"""全面检查页面渲染"""
import urllib.request, json, sys

# Platform首页
try:
    r = urllib.request.urlopen('http://127.0.0.1:8083/', timeout=10)
    html = r.read().decode('utf-8','ignore')
    sys.stdout.write('platform / -> %d (%d bytes)\n' % (r.status, len(html)))
    sys.stdout.write('  开头: ' + html[:120] + '\n')
    sys.stdout.write('  Loading: %d次\n' % html.count('Loading'))
    sys.stdout.write('  服务不可用: %s\n' % ('是' if '服务不可用' in html else '否'))
except Exception as e:
    sys.stdout.write('platform / -> 错误: %s\n' % str(e))

sys.stdout.write('\n')

# Admin login page
try:
    r = urllib.request.urlopen('http://127.0.0.1:8084/admin/login', timeout=10)
    html = r.read().decode('utf-8','ignore')
    sys.stdout.write('admin /admin/login -> %d (%d bytes)\n' % (r.status, len(html)))
    sys.stdout.write('  Loading: %d次\n' % html.count('Loading'))
except Exception as e:
    sys.stdout.write('admin /admin/login -> 错误: %s\n' % str(e))

# Admin dashboard with token (after login)
# First login to get token
try:
    data = json.dumps({'username':'admin','password':'Test1234!','client_type':'browser'}).encode()
    req = urllib.request.Request('http://127.0.0.1:8084/admin/login', data=data,
                                headers={'Content-Type':'application/json'})
    r = urllib.request.urlopen(req, timeout=10)
    body = json.loads(r.read())
    token = body['data']['token']
    sys.stdout.write('\n登录成功, token: %s...\n' % token[:30])
    
    # Try to access admin dashboard with token
    req2 = urllib.request.Request('http://127.0.0.1:8084/admin/',
                                 headers={'Authorization':'Bearer '+token})
    r2 = urllib.request.urlopen(req2, timeout=10)
    html2 = r2.read().decode('utf-8','ignore')
    sys.stdout.write('admin /admin/ (已登录) -> %d (%d bytes)\n' % (r2.status, len(html2)))
    sys.stdout.write('  Loading: %d次\n' % html2.count('Loading'))
    if len(html2) < 200:
        sys.stdout.write('  内容: ' + html2[:200] + '\n')
    else:
        sys.stdout.write('  开头: ' + html2[:120] + '\n')
except Exception as e:
    sys.stdout.write('admin /admin/ (已登录) -> 错误: %s\n' % str(e))

# Site pages
sys.stdout.write('\n=== Site页面 ===\n')
for path in ['/', '/login', '/register', '/pricing', '/knowledge']:
    try:
        r = urllib.request.urlopen('http://127.0.0.1:8081'+path, timeout=10)
        html = r.read().decode('utf-8','ignore')
        sys.stdout.write('site %s -> %d (%d bytes)\n' % (path, r.status, len(html)))
    except Exception as e:
        sys.stdout.write('site %s -> 错误: %s\n' % (path, str(e)))

sys.stdout.flush()
