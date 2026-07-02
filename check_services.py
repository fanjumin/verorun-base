"""Test all 4 services"""
import urllib.request, urllib.error
for port, name in [(8081,'site'),(8083,'platform'),(8084,'admin'),(8090,'captcha')]:
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=5)
        print(f'{name}:{port} -> ✅ {r.status}')
    except urllib.error.HTTPError as e:
        print(f'{name}:{port} -> ⚠️ HTTP {e.code}')
    except Exception as e:
        print(f'{name}:{port} -> ❌ 不可用')

print()
# test admin login page
try:
    r = urllib.request.urlopen('http://127.0.0.1:8084/admin/login', timeout=5)
    print(f'admin /admin/login -> ✅ {r.status} ({len(r.read())} bytes)')
except Exception as e:
    print(f'admin /admin/login -> ❌ {type(e).__name__}')

# test site home
try:
    r = urllib.request.urlopen('http://127.0.0.1:8081/', timeout=5)
    print(f'site / -> ✅ {r.status} ({len(r.read())} bytes)')
except Exception as e:
    print(f'site / -> ❌ {type(e).__name__}')
