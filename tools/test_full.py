#!/usr/bin/env python3
"""Test Publish -> Version History -> Restore flow."""
import sys, json, urllib.request, urllib.error, os, time
import jwt as pyjwt

os.environ['JWT_SECRET'] = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
JWT_SECRET = os.environ['JWT_SECRET']
BASE = 'http://localhost:8084'

def make_token():
    payload = {'user_id': 7, 'is_admin': True, 'iat': int(time.time()), 'exp': int(time.time()) + 3600}
    return pyjwt.encode(payload, JWT_SECRET, algorithm='HS256')

def api(method, path, data=None):
    token = make_token()
    url = f'{BASE}{path}'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            raw = e.read().decode(errors='replace')[:500]
            return e.code, {'raw': raw}
    except Exception as e:
        return 0, {'error': str(e)}

print('=== FULL FLOW: Publish -> Version History -> Restore ===\n')

print('[1] GET /versions (before):')
code, r = api('GET', '/admin/site-builder/versions')
vers = r.get('data', {}).get('versions', r.get('versions', []))
print(f'  HTTP {code} | {len(vers)} versions')

print('\n[2] POST /publish (v1):')
code, r = api('POST', '/admin/site-builder/publish')
print(f'  HTTP {code}')
print(f'  Response: {json.dumps(r, ensure_ascii=False)[:400]}')

print('\n[3] GET /versions (after v1):')
code, r = api('GET', '/admin/site-builder/versions')
vers = r.get('data', {}).get('versions', r.get('versions', []))
for v in vers:
    print(f'  id={v["id"]} label={v["version_label"]} current={v.get("is_current",0)}')

if len(vers) >= 1:
    print('\n[4] POST /update-tokens (modify):')
    code, r = api('POST', '/admin/site-builder/update-tokens', {'brand': {'site_name': 'NovaTech v2'}})
    print(f'  HTTP {code}: {json.dumps(r, ensure_ascii=False)[:200]}')

    print('\n[5] POST /publish (v2):')
    code, r = api('POST', '/admin/site-builder/publish')
    print(f'  HTTP {code}')
    print(f'  Response: {json.dumps(r, ensure_ascii=False)[:400]}')

    print('\n[6] GET /versions (v1+v2):')
    code, r = api('GET', '/admin/site-builder/versions')
    vers = r.get('data', {}).get('versions', r.get('versions', []))
    for v in vers:
        print(f'  id={v["id"]} label={v["version_label"]} current={v.get("is_current",0)}')

    if len(vers) >= 2:
        restore_id = None
        for v in vers:
            if v.get('is_current') == 0:
                restore_id = v['id']
                break
        if not restore_id:
            restore_id = vers[-1]['id']

        print(f'\n[7] POST /versions/{restore_id}/restore:')
        code, r = api('POST', f'/admin/site-builder/versions/{restore_id}/restore')
        print(f'  HTTP {code}: {json.dumps(r, ensure_ascii=False)[:300]}')

        print('\n[8] GET /versions (verify current):')
        code, r = api('GET', '/admin/site-builder/versions')
        vers = r.get('data', {}).get('versions', r.get('versions', []))
        for v in vers:
            print(f'  id={v["id"]} label={v["version_label"]} current={v.get("is_current",0)}')

print('\n=== DONE ===')
