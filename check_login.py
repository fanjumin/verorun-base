"""Check admin login page resources"""
import urllib.request, re
r = urllib.request.urlopen('http://127.0.0.1:8084/admin/login', timeout=10)
html = r.read().decode('utf-8','ignore')
links = re.findall(r'(src|href)=[\"']([^\"']+)[\"']', html)
for attr, url in links:
    if not url.startswith('data:') and not url.startswith('#'):
        print(f'{attr:5s} {url}')
