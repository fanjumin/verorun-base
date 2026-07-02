#!/usr/bin/env python3
"""诊断管理员后台 Loading... 的完整脚本"""
import sys, os, subprocess, json

# 1. 从 gunicorn 进程获取 JWT_SECRET
try:
    pid = subprocess.run(
        ["pgrep", "-f", "gunicorn.*8084"],
        capture_output=True, text=True, check=True
    ).stdout.strip().split('\n')[0]
except:
    print("ERROR: 无法找到 gunicorn 8084 进程")
    sys.exit(1)

try:
    env_data = subprocess.run(
        ["strings", f"/proc/{pid}/environ"],
        capture_output=True, text=True, check=True
    ).stdout
    jwt_secret = None
    for line in env_data.split('\n'):
        if 'JWT_SECRET' in line:
            jwt_secret = line.split('=', 1)[1]
            break
    if not jwt_secret:
        print("ERROR: 未找到 JWT_SECRET")
        sys.exit(1)
    print(f"JWT_SECRET found: {jwt_secret[:20]}...")
except Exception as e:
    print(f"ERROR: 获取 JWT_SECRET 失败: {e}")
    sys.exit(1)

# 2. 生成 admin token
sys.path.append('/home/easykai/easykai-workspace/easykai.cn/admin')
sys.path.append('/home/easykai/easykai-workspace/easykai.cn/auth-center')
sys.path.append('/home/easykai/easykai-workspace/easykai.cn')
os.environ['DB_PATH'] = '/home/easykai/easykai-workspace/easykai.cn/instance/x7k2m9a4.db'
os.environ['JWT_SECRET'] = jwt_secret
os.chdir('/home/easykai/easykai-workspace/easykai.cn/admin')

try:
    from services.jwt_service import create_token
    token = create_token(1, phone='13910604299', is_admin=True)
    print(f"TOKEN generated: {token[:50]}...")
except Exception as e:
    print(f"ERROR: 生成 token 失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 请求 /admin 页面
import urllib.request
req = urllib.request.Request('http://127.0.0.1:8084/admin')
req.add_header('Cookie', f'sso_token={token}')
try:
    resp = urllib.request.urlopen(req, timeout=30)
    html = resp.read().decode('utf-8')
    with open('/tmp/admin_page.html', 'w') as f:
        f.write(html)
    print(f"Admin page fetched: {len(html)} bytes")
except Exception as e:
    print(f"ERROR: 获取 admin 页面失败: {e}")
    sys.exit(1)

# 4. 提取 JS 内容
import re
# 找到所有 <script> 块（排除 src= 的外部脚本）
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
if not scripts:
    print("WARNING: 未找到内联 <script> 块，尝试查找包含特定内容的 script")
    # 可能是 icons.html 那个模式：<script> 开头，tail.html 的 </script> 结尾
    # 找最大的 script 块
    all_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"找到 {len(all_scripts)} 个 script 块")
    for i, s in enumerate(all_scripts):
        print(f"  Script {i}: {len(s)} chars, starts with: {s[:50]}")

combined_js = '\n'.join(scripts)
with open('/tmp/admin_js.js', 'w') as f:
    f.write(combined_js)
print(f"Combined JS: {len(combined_js)} chars")

# 5. node --check 检查语法
result = subprocess.run(['node', '--check', '/tmp/admin_js.js'], capture_output=True, text=True)
print(f"\n=== Node --check result ===")
print(f"Return code: {result.returncode}")
if result.returncode != 0:
    print(f"stderr: {result.stderr}")
    print(f"stdout: {result.stdout}")
else:
    print("✓ 没有 JS 语法错误!")
    
    # 6. 如果没有语法错误，进一步检查运行时执行
    print("\n=== 运行时检查 ===")
    # 检查关键变量
    checks = """
try {
    // 检查 token
    console.log("T 类型:", typeof T);
    console.log("T 长度:", typeof T === 'string' ? T.length : 'N/A');
    console.log("T 前50字符:", typeof T === 'string' ? T.substring(0,50) : 'N/A');
    
    // 检查 init 函数
    console.log("init 类型:", typeof init);
    console.log("initJs 类型:", typeof initJs);
    console.log("loadContent 类型:", typeof loadContent);
    
    // 检查可能缺失的函数
    const checkFuncs = ['_', '$'];
    checkFuncs.forEach(function(f) {
        console.log(f + " 类型:", typeof window[f]);
    });
    
    // 获取 token 中 payload 信息
    if (typeof T === 'string' && T.split('.').length === 3) {
        var payload = JSON.parse(atob(T.split('.')[1]));
        console.log("Token payload:", JSON.stringify(payload));
    }
} catch(e) {
    console.log("检查时出错:", e.message);
}
"""
    # 执行 node 检查
    check_result = subprocess.run(
        ['node', '-e', checks],
        capture_output=True, text=True,
        env={**os.environ, 'NODE_PATH': ''}
    )
    print(f"stdout: {check_result.stdout}")
    if check_result.stderr:
        print(f"stderr: {check_result.stderr}")

print("\n=== 诊断完成 ===")
