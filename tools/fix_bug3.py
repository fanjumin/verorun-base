"""Fix Bug 3: INSERT OR REPLACE/IGNORE -> ON CONFLICT (services + plugins)."""
import os

BASE = r'F:\Sites\VeroRun'

# ── 1. jwt_service.py ──
fp = os.path.join(BASE, 'auth-center', 'services', 'jwt_service.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()
old = "INSERT OR REPLACE INTO system_config (key, value) VALUES (%s, %s)"
new = "INSERT INTO system_config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value"
assert old in c, 'jwt_service.py: pattern not found'
c = c.replace(old, new)
with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)
print('jwt_service.py: OK')

# ── 2. wechat_push_service.py ──
fp = os.path.join(BASE, 'auth-center', 'services', 'wechat_push_service.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()
old = "INSERT OR REPLACE INTO system_config (key, value, description) VALUES (%s, %s, %s)"
new = "INSERT INTO system_config (key, value, description) VALUES (%s, %s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, description=EXCLUDED.description"
assert old in c, 'wechat_push_service.py: pattern not found'
c = c.replace(old, new)
with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)
print('wechat_push_service.py: OK')

# ── 3. oauth_config/routes/auth.py ──
fp = os.path.join(BASE, 'plugins', 'oauth_config', 'routes', 'auth.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()
old = "INSERT OR IGNORE INTO app_authorizations (user_id, app_name, tier) VALUES (?,?,?)"
new = "INSERT INTO app_authorizations (user_id, app_name, tier) VALUES (%s,%s,%s) ON CONFLICT (user_id, app_name) DO NOTHING"
count = c.count(old)
assert count == 6, f'oauth auth.py: expected 6, found {count}'
c = c.replace(old, new)
with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)
print(f'oauth auth.py: {count} replacements')

# ── 4. health_check/routes.py ──
fp = os.path.join(BASE, 'plugins', 'health_check', 'routes.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()

# health_trend
old1 = "INSERT OR REPLACE INTO health_trend (date, total_checks, passed, warnings, errors, avg_response_ms, health_score) "
old1b = "VALUES (?,?,?,?,?,?,?)"
new1 = "INSERT INTO health_trend (date, total_checks, passed, warnings, errors, avg_response_ms, health_score) "
new1b = "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (date) DO UPDATE SET total_checks=EXCLUDED.total_checks, passed=EXCLUDED.passed, warnings=EXCLUDED.warnings, errors=EXCLUDED.errors, avg_response_ms=EXCLUDED.avg_response_ms, health_score=EXCLUDED.health_score"

assert old1 in c, 'health_trend: old1 not found'
assert old1b in c, 'health_trend: old1b not found'
c = c.replace(old1, new1)
c = c.replace(old1b, new1b)

# log_level
old2 = "INSERT OR REPLACE INTO system_config (key, value) VALUES ('log_level', ?)"
new2 = "INSERT INTO system_config (key, value) VALUES ('log_level', %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value"
assert old2 in c, 'system_config log_level (routes): not found'
c = c.replace(old2, new2)

with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)
print('health_check/routes.py: OK')

# ── 5. health_check/checkers.py ──
fp = os.path.join(BASE, 'plugins', 'health_check', 'checkers.py')
with open(fp, 'r', encoding='utf-8') as f:
    c = f.read()
assert old2 in c, 'system_config log_level (checkers): not found'
c = c.replace(old2, new2)
with open(fp, 'w', encoding='utf-8') as f:
    f.write(c)
print('health_check/checkers.py: OK')

print('\nBug 3 fix completed: 11 replacements across 5 files')
