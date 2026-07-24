#!/usr/bin/env python3
"""Test Dashboard API - check all analytics data"""
import urllib.request, urllib.parse, json, http.cookiejar, sys

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
login_data = json.dumps({"username":"***REMOVED***","password":"***REMOVED***"}).encode()
req = urllib.request.Request('http://127.0.0.1:8084/admin/login',
    data=login_data, headers={'Content-Type':'application/json'})
resp = opener.open(req)
print('Login:', resp.read().decode()[:100])

# Dashboard
resp2 = opener.open('http://127.0.0.1:8084/admin/dashboard')
raw = json.loads(resp2.read())
d = raw.get('data', raw)  # API returns {"data": {...}, "success": true}
print('---')
print('today_pv:', d.get('today_pv'))
print('today_uv:', d.get('today_uv'))
print('online_now:', d.get('online_now'))
print('revenue_trend_30d count:', len(d.get('revenue_trend_30d', [])))
print('today_tokens:', d.get('today_tokens'))
print('top_token_agents:', d.get('top_token_agents'))
if d.get('revenue_trend_30d'):
    print('First:', d['revenue_trend_30d'][0])
    print('Last:', d['revenue_trend_30d'][-1])
    print('SUCCESS - revenue_trend_30d has data!')
else:
    print('revenue_trend_30d is EMPTY')
    # Print all available dashboard keys
    print('Dashboard keys:', list(d.keys()))
    sys.exit(1)
