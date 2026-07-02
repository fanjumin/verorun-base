#!/usr/bin/env python3
"""Test all 3 services."""
import urllib.request, urllib.error, sys

results = []
for name, port in [('site', 8081), ('platform', 8083), ('admin', 8084)]:
    try:
        resp = urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=5)
        results.append((name, port, resp.status, 'OK'))
    except urllib.error.HTTPError as e:
        results.append((name, port, e.code, str(e)))
    except Exception as e:
        results.append((name, port, 'ERR', str(e)))

for name, port, status, msg in results:
    print(f'{name:10s} :{port} -> {status} {msg}')

# Also test site home page
try:
    resp = urllib.request.urlopen('http://127.0.0.1:8081/', timeout=5)
    body = resp.read()[:100]
    print(f'\nSite /: 200 OK ({body[:50]}...)')
except urllib.error.HTTPError as e:
    print(f'\nSite /: {e.code}')
    print(e.read()[:200])
except Exception as e:
    print(f'\nSite /: ERR - {e}')
