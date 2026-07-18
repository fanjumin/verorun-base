"""最终验证：API 端点 + 数据完整性"""
import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('***REMOVED***', username='easykai', password='***REMOVED***', timeout=30)

def run(cmd, wait=3):
    i, o, e = c.exec_command(cmd)
    time.sleep(wait)
    r = (o.read().decode(errors='replace') + e.read().decode(errors='replace')).strip()
    if r: print(r[:1200])
    return r

PG = 'PGPASSWORD=***REMOVED*** psql -h localhost -U easykai -d verorun'

# 1. Model Management API（admin:8084）
print('=== 1. Model Management API ===')
run("curl -s http://localhost:8084/admin/providers 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print('success:', d.get('success')); print('providers:', len(d.get('data',[]))); [print(f'  {p[\"slug\"]}: {len(p.get(\"models\",[]))} models') for p in d.get('data',[])]\"", 4)

# 2. 所有缺失表最终确认
print('\n=== 2. 最终表确认 ===')
for tbl in ['voice_templates','chatbot_sessions','invoices','notification_templates','notification_logs','user_interests','knowledge_blocks','providers','provider_models']:
    r = run(f"{PG} -t -c \"SELECT count(*) FROM {tbl}\" 2>&1", 2)
    ok = 'OK' if r.strip().isdigit() else 'FAIL'
    print(f'  {tbl}: {ok}')

# 3. 服务状态
print('\n=== 3. 服务状态 ===')
for name, port in [('auth',8081),('platform',8083),('admin',8084)]:
    i, o, e = c.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:{port}/ 2>&1')
    time.sleep(1)
    print(f'  {name}:{port} -> {o.read().decode().strip()}')

# 4. 检查 init_db 是否完整运行（查看最后一条 Migration 消息）
print('\n=== 4. init_db 完整性 ===')
run("cd /home/easykai/easykai-workspace/easykai.cn/auth-center ; PG_PASSWORD=***REMOVED*** PG_DB=verorun PG_USER=easykai PG_HOST=localhost PG_PORT=5432 DEPLOY_MARKET=cn DEPLOY_DOMAIN=easykai.cn python3 -c \"from models.database import init_db; init_db()\" 2>&1 | tail -5", 10)

c.close()
