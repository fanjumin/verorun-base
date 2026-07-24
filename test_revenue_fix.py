#!/usr/bin/env python3
"""Verify monthly_revenue shows properly (should still be raw float from DB, 
but .toFixed(2) will handle display in the frontend)"""
import urllib.request
import json

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJFNGJKR3V0LWRpMWhpSVp6YUxZaGNBIiwidXNlcl9pZCI6NywicGhvbmUiOiIxMzkxMDYwNDI5OSIsImFwcF9uYW1lIjoiYWRtaW4iLCJpc19hZG1pbiI6dHJ1ZSwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImlhdCI6MTc4NDU1MTg2NywiZXhwIjoxNzg1MTU2NjY3fQ.EOUICe8gw4tbtkTpXLyv4_P3K3n13w-OgdfFOrV8omk'

req = urllib.request.Request('http://127.0.0.1:8084/admin/dashboard',
                              headers={'Authorization': 'Bearer ' + token})
resp = urllib.request.urlopen(req)
d = json.loads(resp.read().decode()).get('data', {})

mr = d.get('monthly_revenue')
print(f'Raw value from API: {mr}')
print(f'With .toFixed(2):   {(mr or 0):.2f}')
print(f'Expected display: ¥{(mr or 0):.2f}')
