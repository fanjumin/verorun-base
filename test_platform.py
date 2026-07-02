#!/usr/bin/env python3
"""Test platform service."""
import urllib.request, urllib.error

req = urllib.request.Request('http://127.0.0.1:8083/', method='GET')
try:
    resp = urllib.request.urlopen(req, timeout=5)
    print('platform /:', resp.status)
except urllib.error.HTTPError as e:
    loc = e.headers.get('Location', '')
    print('platform /:', e.code, '->', loc)
except Exception as e:
    print('platform /: FAILED -', e)
