"""Upload do_migrate.py and run on server."""
import paramiko, time, os

def ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=15, allow_agent=False, look_for_keys=False)
    return s

def run(c, cmd, wait=60):
    ch = c.get_transport().open_session()
    ch.exec_command(cmd)
    time.sleep(wait)
    out = b''
    while ch.recv_ready(): out += ch.recv(4096)
    err = b''
    while ch.recv_stderr_ready(): err += ch.recv_stderr(4096)
    ch.close()
    return out.decode(errors='replace'), err.decode(errors='replace')

s = ssh()

# Upload migration script
with s.open_sftp() as sf:
    sf.put(r'F:\Sites\VeroRun\tools\do_migrate.py',
           '/home/easykai/easykai-workspace/easykai.cn/tools/do_migrate.py')
print('Uploaded do_migrate.py')

# Run migration
print('Running migration (60s)...')
out, err = run(s, 'cd /home/easykai/easykai-workspace/easykai.cn && PG_HOST=localhost PG_PORT=5432 PG_DB=verorun PG_USER=easykai PG_PASSWORD=***REMOVED*** python3 -B tools/do_migrate.py 2>&1', 60)
print(out[:3000])
if err: print('ERR:', err[:500])

# Verify data
print('\n=== Verification ===')
for table in ['users', 'system_config', 'cms_posts', 'cms_categories', 'site_configs', 'subscriptions']:
    out, _ = run(s, f'PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun -t -c "select count(*) from {table}" 2>&1', 3)
    print(f'  {table}: {out.strip()}')

s.close()
