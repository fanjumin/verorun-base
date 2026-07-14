"""VeroRun 本地开发 — 一键启动全部 4 个服务 + 测试用户"""
import subprocess, sys, os, time, urllib.request, urllib.error, signal

BASE = os.path.dirname(os.path.abspath(__file__))
ENV = os.environ.copy()
ENV['PYTHONIOENCODING'] = 'utf-8'
ENV['JWT_SECRET'] = ENV.get('JWT_SECRET', 'test-jwt-secret-for-dev-2026')
ENV['DEPLOY_DOMAIN'] = ENV.get('DEPLOY_DOMAIN', 'localhost')
ENV['DEPLOY_PROTOCOL'] = ENV.get('DEPLOY_PROTOCOL', 'http')
ENV['DB_PATH'] = ENV.get('DB_PATH', os.path.join(BASE, 'verorun.db'))

procs = {}

def start(name, cmd, cwd=None):
    print(f'[{name}] 启动中...', flush=True)
    procs[name] = subprocess.Popen(
        cmd, cwd=cwd or BASE, env=ENV,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )

# 启动 4 个服务
start('captcha', [sys.executable, os.path.join(BASE, 'captcha-service', 'server.py'), '8090'],
      cwd=os.path.join(BASE, 'captcha-service'))
start('site', [sys.executable, os.path.join(BASE, 'site', 'app.py'), '8081'])
start('platform', [sys.executable, os.path.join(BASE, 'platform', 'app.py'), '8083'])
start('admin', [sys.executable, os.path.join(BASE, 'admin', 'app.py'), '8084'])

# 等待启动
print('\n等待服务启动...', flush=True)
time.sleep(8)

# 健康检查
print('\n=== 健康检查 ===')
ok = True
for name, port in [('captcha',8090),('site',8081),('platform',8083),('admin',8084)]:
    try:
        resp = urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=5)
        print(f'  [{name:10s}] {resp.status} OK', flush=True)
    except Exception as e:
        print(f'  [{name:10s}] FAIL: {type(e).__name__}', flush=True)
        ok = False

print()
if ok:
    print('=' * 55)
    print('  所有服务已就绪！按 Ctrl+C 停止')
    print('=' * 55)
    print()
    print('  [官网]      http://localhost:8081/')
    print('  [用户控制台] http://localhost:8083/')
    print('  [管理后台]   http://localhost:8084/admin/login')
    print('  [验证码]    http://localhost:8090/health')
    print()
    print('  ── 测试账号 (密码: Test1234!) ──')
    print('  管理后台: admin')
    print('  官网登录: testuser')
    print()
    print('  控制台使用: 先访问 http://localhost:8081/login 用 testuser 登录')
    print('  然后访问 http://localhost:8083/ 进入用户控制台')
else:
    print('⚠️ 部分服务启动失败')

# 保持进程运行
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('\n正在停止所有服务...')
    for name, p in procs.items():
        p.terminate()
    for name, p in procs.items():
        p.wait()
    print('已停止所有服务')
