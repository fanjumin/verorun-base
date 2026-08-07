import json, urllib.request, sys

BASE = 'https://agent.verorun.com'

def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        resp = urllib.request.urlopen(req, data=data, timeout=20)
        raw = resp.read().decode()
        try:
            return resp.status, json.loads(raw)
        except Exception:
            return resp.status, raw[:300]
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:300]
    except Exception as e:
        return 0, str(e)

code, r = call('POST', '/user/password/login', body={'phone': '***REMOVED***', 'password': '***REMOVED***'})
print('[1] LOGIN', code)
if code != 200 or not r.get('success'):
    print('    FAIL:', r); sys.exit(1)
token = r['data']['token']
print('    ok, token len', len(token))

# Probe route versions
for path in ['/admin/agent-matrix/prompts',
             '/admin/agent-matrix/prompts/files',
             '/admin/agent-matrix/prompts/db',
             '/admin/agent-matrix/bindings',
             '/admin/agent-matrix/prompts/load?path=prompts/master_prompt.md']:
    code, r = call('GET', path, token)
    if isinstance(r, dict) and isinstance(r.get('data'), list):
        print(f'[R] {path} -> {code}, list len={len(r["data"])}, first keys={list(r["data"][0].keys())[:6] if r["data"] else "-"}')
    else:
        print(f'[R] {path} -> {code}, {str(r)[:160]}')

# Probe DB prompt existence via system_config or direct
code, r = call('GET', '/admin/agent-matrix/agents', token)
print('[AGENTS]', code, 'count=', len(r.get('data', [])) if isinstance(r.get('data'), list) else r)
