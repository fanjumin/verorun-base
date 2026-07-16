#!/usr/bin/env python3
"""Final deployment: upload fixes + clean DB + recreate + start services."""
import paramiko, time, os

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15)

JWT = '30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d'
ENV = f"PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn JWT_SECRET={JWT} FLASK_SECRET_KEY={JWT}"
BASE = '/home/easykai/easykai-workspace/easykai.cn'

# (file list inline in the upload step below)

def run(cmd, wait=3):
    c = s.get_transport().open_session()
    c.exec_command(cmd)
    time.sleep(wait)
    out = b''
    while c.recv_ready():
        out += c.recv(4096)
    err = b''
    while c.recv_stderr_ready():
        err += c.recv_stderr(4096)
    c.close()
    return out.decode(errors='replace'), err.decode(errors='replace')

# ─── Step 1: SFTP upload ────────────────────────────────────
print('1. SFTP uploading...')
# All changed files since migration (local → remote mapping)
UPLOADS = [
    # auth-center models
    (r'F:\Sites\VeroRun\auth-center\models\database.py', f'{BASE}/auth-center/models/database.py'),
    (r'F:\Sites\VeroRun\auth-center\models\cms.py', f'{BASE}/auth-center/models/cms.py'),
    (r'F:\Sites\VeroRun\auth-center\models\__init__.py', f'{BASE}/auth-center/models/__init__.py'),
    # root files (auth entry point)
    (r'F:\Sites\VeroRun\auth_server.py', f'{BASE}/auth_server.py'),
    (r'F:\Sites\VeroRun\run_auth_wsgi.py', f'{BASE}/run_auth_wsgi.py'),
    # auth-center services (? → %s fixes)
    (r'F:\Sites\VeroRun\auth-center\services\ai_content_generator.py', f'{BASE}/auth-center/services/ai_content_generator.py'),
    (r'F:\Sites\VeroRun\auth-center\services\invoice_service.py', f'{BASE}/auth-center/services/invoice_service.py'),
    (r'F:\Sites\VeroRun\auth-center\services\jwt_service.py', f'{BASE}/auth-center/services/jwt_service.py'),
    (r'F:\Sites\VeroRun\auth-center\services\payment_service.py', f'{BASE}/auth-center/services/payment_service.py'),
    (r'F:\Sites\VeroRun\auth-center\services\renewal_reminder.py', f'{BASE}/auth-center/services/renewal_reminder.py'),
    (r'F:\Sites\VeroRun\auth-center\services\sms_service.py', f'{BASE}/auth-center/services/sms_service.py'),
    (r'F:\Sites\VeroRun\auth-center\services\volcengine_client.py', f'{BASE}/auth-center/services/volcengine_client.py'),
    (r'F:\Sites\VeroRun\auth-center\services\wechat_push_service.py', f'{BASE}/auth-center/services/wechat_push_service.py'),
    (r'F:\Sites\VeroRun\auth-center\services\toutiao_service.py', f'{BASE}/auth-center/services/toutiao_service.py'),
    (r'F:\Sites\VeroRun\auth-center\services\weibo_service.py', f'{BASE}/auth-center/services/weibo_service.py'),
    (r'F:\Sites\VeroRun\auth-center\services\verification_service.py', f'{BASE}/auth-center/services/verification_service.py'),
    # admin
    (r'F:\Sites\VeroRun\admin\app.py', f'{BASE}/admin/app.py'),
    (r'F:\Sites\VeroRun\admin\routes\theme_admin.py', f'{BASE}/admin/routes/theme_admin.py'),
    # platform
    (r'F:\Sites\VeroRun\platform\app.py', f'{BASE}/platform/app.py'),
    (r'F:\Sites\VeroRun\platform\cms_public.py', f'{BASE}/platform/cms_public.py'),
    (r'F:\Sites\VeroRun\platform\routes\site_routes.py', f'{BASE}/platform/routes/site_routes.py'),
    (r'F:\Sites\VeroRun\platform\routes\mini_program.py', f'{BASE}/platform/routes/mini_program.py'),
    # site
    (r'F:\Sites\VeroRun\site\app.py', f'{BASE}/site/app.py'),
    # auth-center routes (Bug 3 + Bug 4 fixes)
    (r'F:\Sites\VeroRun\auth-center\routes\auth.py', f'{BASE}/auth-center/routes/auth.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\user.py', f'{BASE}/auth-center/routes/user.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\social_media.py', f'{BASE}/auth-center/routes/social_media.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\shop_admin.py', f'{BASE}/auth-center/routes/shop_admin.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\sessions.py', f'{BASE}/auth-center/routes/sessions.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\header_admin.py', f'{BASE}/auth-center/routes/header_admin.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\footer_admin.py', f'{BASE}/auth-center/routes/footer_admin.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\cleaner_agent.py', f'{BASE}/auth-center/routes/cleaner_agent.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\agents.py', f'{BASE}/auth-center/routes/agents.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\admin.py', f'{BASE}/auth-center/routes/admin.py'),
    (r'F:\Sites\VeroRun\auth-center\routes\subscription\__init__.py', f'{BASE}/auth-center/routes/subscription/__init__.py'),
    # plugins (datetime now + Bug 3 fixes)
    (r'F:\Sites\VeroRun\plugins\sms\routes.py', f'{BASE}/plugins/sms/routes.py'),
    (r'F:\Sites\VeroRun\plugins\ads\ai_tools.py', f'{BASE}/plugins/ads/ai_tools.py'),
    (r'F:\Sites\VeroRun\plugins\oauth_config\routes\auth.py', f'{BASE}/plugins/oauth_config/routes/auth.py'),
    (r'F:\Sites\VeroRun\plugins\health_check\routes.py', f'{BASE}/plugins/health_check/routes.py'),
    (r'F:\Sites\VeroRun\plugins\health_check\checkers.py', f'{BASE}/plugins/health_check/checkers.py'),
]

with s.open_sftp() as sf:
    for local, remote in UPLOADS:
        sf.put(local, remote)
        print(f'   -> {os.path.basename(local)}')

# ─── Step 2: Kill services & clean DB ───────────────────────
print('2. Killing services + cleaning DB...')
run("sudo systemctl stop auth-center.service admin.service 2>/dev/null", 2)
run("pkill -9 -f python3 2>/dev/null", 1)
time.sleep(2)

# Drop all tables using CASCADE to handle FK constraints
sql = """
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO easykai;
GRANT ALL ON SCHEMA public TO public;
"""
run(f'PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -c "{sql.strip()}"', 3)
print('   DB cleaned (public schema recreated)')

# Clear __pycache__
run(f'rm -rf {BASE}/auth-center/models/__pycache__', 1)
run(f'rm -rf {BASE}/admin/__pycache__ {BASE}/platform/__pycache__', 1)
run('rm -f /tmp/auth_8081.log /tmp/platform_8083.log /tmp/admin_8084.log', 1)
print('   Cache + logs cleared')

# ─── Step 3: Start auth (creates all tables) ─────────────────
print('3. Starting auth (creates tables)...')
run(f"cd {BASE} && {ENV} nohup python3 -B auth_server.py > /tmp/auth_8081.log 2>&1 &", 3)
time.sleep(10)

# Check auth started + tables created
out, _ = run("ss -tlnp | grep 8081", 2)
if '8081' in out:
    print('   Auth port 8081 listening')
else:
    print('   WARNING: Auth port NOT listening')
    out, _ = run("tail -30 /tmp/auth_8081.log", 2)
    print(f'   Auth log:\n{out[:500]}')

# ─── Step 4: Start platform & admin ──────────────────────────
print('4. Starting platform + admin...')
run(f"cd {BASE} && {ENV} nohup python3 -B platform/app.py 8083 > /tmp/platform_8083.log 2>&1 &", 3)
time.sleep(5)
run(f"cd {BASE} && {ENV} nohup python3 -B admin/app.py 8084 > /tmp/admin_8084.log 2>&1 &", 3)
time.sleep(5)

# ─── Step 5: Wait & verify ───────────────────────────────────
print('5. Waiting 15s for startup...')
time.sleep(15)

out, _ = run("ss -tlnp | grep -E '808[134]' || echo 'none'", 2)
print(f'\n6. Ports:\n{out.strip()}')

for n, p in [('auth', 8081), ('platform', 8083), ('admin', 8084)]:
    out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{p}/ 2>&1", 2)
    print(f'   {n}: {out.strip()}')

# Check logs for errors
for svc, logfile in [('auth', 'auth_8081.log'), ('platform', 'platform_8083.log'), ('admin', 'admin_8084.log')]:
    out, _ = run(f"tail -30 /tmp/{logfile}", 2)
    has_err = 'Traceback' in out or 'Error' in out
    if has_err:
        print(f'\n   {svc.upper()} ERRORS:')
        for l in out.split('\n'):
            if any(x in l for x in ['Error', 'Traceback', 'error']):
                print(f'     {l[:200]}')
    else:
        print(f'\n   {svc} log OK')

s.close()
print('\n=== Done ===')
