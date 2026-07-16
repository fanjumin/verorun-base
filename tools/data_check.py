"""Final data check on server."""
import paramiko, time

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15, allow_agent=False, look_for_keys=False)

def run(cmd, wait=3):
    ch = s.get_transport().open_session()
    ch.exec_command(cmd)
    time.sleep(wait)
    out, err = b'', b''
    while ch.recv_ready(): out += ch.recv(4096)
    while ch.recv_stderr_ready(): err += ch.recv_stderr(4096)
    ch.close()
    return out.decode(errors='replace')

print('=== DATA COUNTS ===')
tables = ['site_configs', 'system_config', 'cms_categories', 'cms_posts', 'subscriptions', 'admin_profiles', 'social_media_links', 'header_nav', 'footer_links', 'knowledge_blocks']
for t in tables:
    out = run('PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -t -A -c "select count(*) from ' + t + '" 2>&1', 2)
    print(f'  {t}: {out.strip()}')

print('\n=== AUTH LOG ERRORS ===')
out = run('grep -v INFO:werkzeug /tmp/auth_8081.log | grep -iE "traceback|error|exception|cannot" | head -10', 2)
out2 = run('head -5 /tmp/auth_8081.log', 2)
# Combine
for line in out.split('\n')[:10]:
    if line.strip(): print(f'  {line}')

if not out.strip():
    print('  No errors in auth log')

print('\n=== SERVICE STATUS ===')
for port in [8081, 8083, 8084]:
    out = run('curl -s -o /dev/null -w "%{http_code}" http://localhost:' + str(port) + '/ 2>&1', 2)
    print(f'  :{port} -> {out.strip()}')

s.close()
print('\nDone')
