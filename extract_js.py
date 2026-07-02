import re, os
html = open('/tmp/platform.html').read()
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f'Found {len(scripts)} script blocks')
for i, s in enumerate(scripts):
    if s.strip():
        f = f'/tmp/js_{i}.js'
        open(f, 'w').write(s.strip())
        print(f'Script {i}: {len(s)} chars -> {f}')
