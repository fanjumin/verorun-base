#!/usr/bin/env python3
"""Test Publish → Version History → Restore flow via API."""
import urllib.request, urllib.error, json, sys

BASE = "http://localhost:8084"
JWT_SECRET = "30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d"
ADMIN_USER = 7  # ***REMOVED***

def make_token():
    import hmac, hashlib, base64, time
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b'=').decode()
    payload = base64.urlsafe_b64encode(json.dumps({
        "user_id": ADMIN_USER, "role": "super_admin",
        "exp": int(time.time()) + 3600
    }).encode()).rstrip(b'=').decode()
    msg = f"{header}.{payload}"
    sig = base64.urlsafe_b64encode(
        hmac.new(JWT_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    ).rstrip(b'=').decode()
    return f"{msg}.{sig}"

def api(method, path, data=None):
    token = make_token()
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read()) if e.code != 500 else {"error": str(e), "code": e.code}

print("=" * 60)
print("TEST: Publish → Version History → Restore")
print("=" * 60)

# Step 1: List versions (should be empty or have some)
print("\n[1] GET /versions (before publish)")
versions = api("GET", "/admin/site-builder/versions")
print(f"    Response: {json.dumps(versions, indent=2, ensure_ascii=False)[:200]}")

# Step 2: First publish - should create v1
print("\n[2] POST /publish (first)")
pub1 = api("POST", "/admin/site-builder/publish")
print(f"    Response: {json.dumps(pub1, indent=2, ensure_ascii=False)[:300]}")

# Step 3: List versions (should have v1)
print("\n[3] GET /versions (after first publish)")
versions = api("GET", "/admin/site-builder/versions")
vers = versions.get("data", {}).get("versions", versions.get("versions", []))
print(f"    {len(vers)} version(s):")
for v in vers:
    print(f"      - {v['version_label']} (id={v['id']}, current={v.get('is_current',0)})")

# Step 4: Modify a token (change brand name)
print("\n[4] POST /update-tokens (modify draft)")
mod = api("POST", "/admin/site-builder/update-tokens", {"colors": {"primary": "#7c3aed"}})
print(f"    Response: {json.dumps(mod, indent=2, ensure_ascii=False)[:200]}")

# Step 5: Second publish - should create v2
print("\n[5] POST /publish (second)")
pub2 = api("POST", "/admin/site-builder/publish")
print(f"    Response: {json.dumps(pub2, indent=2, ensure_ascii=False)[:300]}")

# Step 6: List versions (should have v1 and v2)
print("\n[6] GET /versions (after second publish)")
versions = api("GET", "/admin/site-builder/versions")
vers = versions.get("data", {}).get("versions", versions.get("versions", []))
print(f"    {len(vers)} version(s):")
for v in vers:
    print(f"      - {v['version_label']} (id={v['id']}, current={v.get('is_current',0)})")

if len(vers) >= 2:
    v1_id = vers[-1]["id"]  # oldest first in sort? No, newest first.
    v2_id = vers[0]["id"]
    print(f"    v1 id={v1_id}, v2 id={v2_id} (newest first ordering)")

    # Step 7: Restore v1
    print(f"\n[7] POST /versions/{v1_id}/restore")
    rst = api("POST", f"/admin/site-builder/versions/{v1_id}/restore")
    print(f"    Response: {json.dumps(rst, indent=2, ensure_ascii=False)[:300]}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
