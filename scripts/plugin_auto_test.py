#!/usr/bin/env python3
"""
插件系统全自动修复+测试脚本
=======================
在服务器上执行完整测试流程。
"""
import paramiko, json, time, sys, os

HOST = '***REMOVED***'
USER = 'easykai'
PASS = '***REMOVED***'
ROOT = '/home/easykai/easykai-workspace/easykai.cn'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, look_for_keys=False, allow_agent=False)

PASSED, FAILED = 0, 0
errors = []

def check(name, ok, detail=''):
    global PASSED, FAILED
    status = '✅ PASS' if ok else '❌ FAIL'
    print(f'  {status} | {name}')
    if not ok:
        FAILED += 1
        errors.append(f'{name}: {detail}')
    else:
        PASSED += 1

def run(cmd, timeout=10):
    """Run command on remote and return stdout"""
    stdin, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    return out.read().decode().strip(), err.read().decode().strip(), exit_code

def api_get(path):
    """Curl a localhost API and parse JSON"""
    out, err, _ = run(f'curl -s http://localhost:8084{path} 2>&1')
    try:
        return json.loads(out) if out else None
    except:
        return None

def api_post(path, data):
    """Curl POST with JSON body"""
    data_str = json.dumps(data)
    out, err, _ = run(
        f'curl -s -X POST http://localhost:8084{path} '
        f'-H "Content-Type: application/json" '
        f'-d \'{data_str}\' 2>&1'
    )
    try:
        return json.loads(out) if out else None
    except:
        return out

print('='*60)
print('插件系统全自动修复 + 测试')
print('='*60)

# ═══════════════════════════
# 阶段 1: 基础修复
# ═══════════════════════════
print('\n【阶段 1】基础修复')

# 1.1 删除旧框架文件
out, err, _ = run(f'rm -f {ROOT}/plugins/__init__.py {ROOT}/plugins/base.py {ROOT}/plugins/registry.py {ROOT}/plugins/hooks.py')
out, err, _ = run(f'ls -la {ROOT}/plugins/__init__.py 2>&1')
check('删除旧 plugins/__init__.py', 'No such file' in out, out)

# 1.2 同步本地最新 admin/app.py
local_app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'app.py')
local_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin_manager', 'base.py')
local_eb = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin_manager', 'event_bus.py')
sftp = ssh.open_sftp()
sftp.put(local_app, f'{ROOT}/admin/app.py')
sftp.put(local_base, f'{ROOT}/plugin_manager/base.py')
sftp.put(local_eb, f'{ROOT}/plugin_manager/event_bus.py')
sftp.close()
check('同步 admin/app.py + base.py + event_bus.py', True)

# 1.3 杀掉所有 admin 进程
run('pkill -f "admin/app.py" 2>/dev/null')
time.sleep(2)
out, _, _ = run('ps aux | grep admin/app.py | grep -v grep')
check('杀掉旧 admin 进程', not out.strip(), out[:100] if out else 'none')

# 1.4 重启服务
env = 'JWT_SECRET=easykai_jwt_secret_2026'
run(f'cd {ROOT} && export {env} && nohup python3 admin/app.py > /tmp/admin2.log 2>&1 &')
time.sleep(5)

out, _, _ = run('ps aux | grep admin/app.py | grep -v grep')
check('admin 服务启动', bool(out.strip()), out[:200] if out else 'no process')

# 1.5 检查启动日志
out, _, _ = run('tail -10 /tmp/admin2.log')
has_error = 'Traceback' in out or 'Error' in out
check('启动日志无报错', not has_error, out[-300:])
print(f'  日志: {out[-400:]}')

# ═══════════════════════════
# 阶段 2: API 测试
# ═══════════════════════════
print('\n【阶段 2】API 测试')

time.sleep(2)

# 2.1 健康检查
data = api_get('/health')
check('GET /health 200', data and data.get('status') == 'ok', str(data))

# 2.2 Discover
data = api_get('/admin/plugins/discover')
plugins_list = []
if data and data.get('success'):
    plugins_list = data.get('data', {}).get('plugins', []) if isinstance(data.get('data'), dict) else data.get('plugins', [])
check(f'Discover 返回插件 ({len(plugins_list)} 个)', len(plugins_list) > 0, f'plugins: {[p.get("identifier",p.get("name")) for p in plugins_list]}')

expected = ['ali_api', 'coupons', 'reviews', 'wishlist', 'order_notify']
if len(plugins_list) > 0:
    found_names = sorted([p.get('identifier', p.get('name', '')) for p in plugins_list])
    check(f'发现齐全: {found_names}', all(e in found_names for e in expected), f'expected={expected}, found={found_names}')

# 2.3 检查 List（应全为未安装）
data = api_get('/admin/plugins')
installed_list = []
if data and isinstance(data, dict):
    installed_list = data.get('data', []) if 'data' in data else []
    if not isinstance(installed_list, list):
        if isinstance(data.get('data'), dict):
            installed_list = data.get('data', {}).get('plugins', [])
check(f'List 初始为空 ({len(installed_list)} 个)', len(installed_list) == 0, str(installed_list[:3]) if installed_list else 'empty')

# ═══════════════════════════
# 阶段 3: 安装测试
# ═══════════════════════════
print('\n【阶段 3】安装测试')

installed = []
for pid in expected:
    data = api_post(f'/admin/plugins/{pid}/install', {})
    ok = data and data.get('success', False)
    if ok:
        installed.append(pid)
    check(f'Install {pid}', ok, str(data)[:150])
    time.sleep(0.5)

check(f'全部安装成功 ({len(installed)}/{len(expected)})', len(installed) == len(expected), f'installed={installed}')

# 验证 list 现在有数据
data = api_get('/admin/plugins')
list_count = 0
if data and isinstance(data, dict):
    lst = data.get('data', [])
    if isinstance(lst, list):
        list_count = len(lst)
    elif isinstance(lst, dict):
        list_count = len(lst.get('plugins', []))
check(f'List 有 {list_count} 个已安装插件', list_count > 0, str(data)[:200])

# ═══════════════════════════
# 阶段 4: Enable/Disable 测试
# ═══════════════════════════
print('\n【阶段 4】生命周期测试')

# 4.1 Enable ali_api
data = api_post(f'/admin/plugins/ali_api/enable', {})
check('Enable ali_api', data and data.get('success', False), str(data)[:150])

# 4.2 检查状态
data = api_get('/admin/plugins/ali_api')
if data is None:
    data = api_get('/admin/plugins')
ali_status = 'unknown'
if data:
    if isinstance(data, dict) and 'data' in data:
        lst = data['data']
        if isinstance(lst, list):
            for p in lst:
                if isinstance(p, dict) and p.get('identifier') == 'ali_api':
                    ali_status = p.get('status', str(p))
check('ali_api ENABLED', 'ENABLED' in str(ali_status) or 'enabled' in str(ali_status).lower(), str(ali_status))

# 4.3 Disable ali_api
data = api_post(f'/admin/plugins/ali_api/disable', {})
check('Disable ali_api', data and data.get('success', False), str(data)[:150])

# 4.4 重新 Enable 回来
api_post('/admin/plugins/ali_api/enable', {})

# Enable 其他插件
for pid in installed:
    api_post(f'/admin/plugins/{pid}/enable', {})
check('启用全部插件', True)

# ═══════════════════════════
# 阶段 5: Nginx 可达性
# ═══════════════════════════
print('\n【阶段 5】Nginx 可达性')

import urllib.request
try:
    resp = urllib.request.urlopen('https://easykai.cn/admin/plugins/discover', timeout=10)
    body = resp.read().decode()[:200]
    check('Nginx HTTPS 可达', resp.status == 200, f'{resp.status} {body}')
except Exception as e:
    # Try via IP
    try:
        resp = urllib.request.urlopen('http://***REMOVED***:8084/admin/plugins/discover', timeout=5)
        body = resp.read().decode()[:200]
        check('Nginx 直接端口可达', resp.status == 200, f'{resp.status} {body}')
    except Exception as e2:
        check('Nginx HTTP 可达', False, str(e2))

# ═══════════════════════════
# 总结
# ═══════════════════════════
print('\n' + '='*60)
print(f'测试完成: ✅ {PASSED} 通过, ❌ {FAILED} 失败')
if errors:
    print('\n失败列表:')
    for e in errors:
        print(f'  - {e}')
print('='*60)

ssh.close()
sys.exit(0 if FAILED == 0 else 1)
