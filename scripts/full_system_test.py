#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易站智能建站系统（easykai.cn） — 全面系统测试脚本（只读 / 幂等）
================================================================
通过 Paramiko SSH 连接生产服务器，分 6 层对全站做只读健康探测：

    L0 存活层   4 个服务 /health 端点 → 200
    L1 就绪层   health-service /ready → 数据库连通
    L2 深度体检 携带 admin JWT 调 POST /admin/health/api/run，跑全部 checker
    L3 路由+SSO Nginx 各域名/子路由 HTTPS 可达 + JWT 跨子域免登 + token 边界
    L4 业务冒烟 插件/订阅/商城/CMS 等 GET 类接口可达
    L5 定时任务 交叉读取 workflow_engine checker 结果

【零副作用保证】
    全程 GET/只读探测 + 一次 health/api/run（仅写自身检查历史表，不动业务数据），
    不重启服务、不修改任何文件、不新建数据库。

【凭据处理】（不硬编码明文，优先环境变量）
    EASYKAI_SSH_HOST   默认 ***REMOVED***
    EASYKAI_SSH_USER   默认 easykai
    EASYKAI_SSH_PASS   SSH 密码（未设置时回退到内置默认，仅用于本项目固定服务器）
    ADMIN_USER         管理后台账号（默认 admin）
    ADMIN_PASS         管理后台密码（必须通过环境变量提供，用于换取 admin JWT）

用法：
    # PowerShell
    $env:ADMIN_PASS="你的管理员密码"; python scripts/full_system_test.py
    # 可选覆盖：
    $env:EASYKAI_SSH_PASS="..."; $env:ADMIN_USER="admin"

    报告将同时打印到终端并写入 report_full_system_test.md
"""

import os
import sys
import json
import time
import datetime

try:
    import paramiko
except ImportError:
    print('缺少依赖 paramiko，请先执行: pip install paramiko')
    sys.exit(2)

# ─── 配置（环境变量优先） ─────────────────────────────────────────────
HOST = os.environ.get('EASYKAI_SSH_HOST', '***REMOVED***')
USER = os.environ.get('EASYKAI_SSH_USER', 'easykai')
# 服务器口令：优先环境变量；回退到本项目固定服务器默认口令（仅内部使用）
PASS = os.environ.get('EASYKAI_SSH_PASS', '***REMOVED***')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', '')

# 站点域名（依据 project_rules.md 第 6 节真实拓扑）
MAIN_DOMAIN = 'easykai.cn'
PLATFORM_DOMAIN = 'platform.easykai.cn'
AGENT_DOMAIN = 'agent.easykai.cn'

# 本地服务端口 → 名称
LOCAL_SERVICES = [
    ('site',     8081),   # 主站后端 / OAuth
    ('platform', 8083),   # 认证/订阅/Platform
    ('admin',    8084),   # 管理后台 / Admin
    ('health',   8085),   # 独立健康检查服务
]

REPORT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'report_full_system_test.md'
)

# ─── 结果收集 ────────────────────────────────────────────────────────
RESULTS = []   # 每项: {'layer', 'name', 'status'('pass'|'warn'|'fail'), 'detail', 'ms'}
_counts = {'pass': 0, 'warn': 0, 'fail': 0}


def record(layer, name, status, detail='', ms=0):
    """记录一条测试结果并即时打印"""
    assert status in ('pass', 'warn', 'fail')
    _counts[status] += 1
    icon = {'pass': '✅', 'warn': '⚠️', 'fail': '❌'}[status]
    line = f'  {icon} [{layer}] {name}'
    if ms:
        line += f'  ({ms}ms)'
    print(line, flush=True)
    if status != 'pass' and detail:
        print(f'       ↳ {str(detail)[:300]}', flush=True)
    RESULTS.append({
        'layer': layer, 'name': name, 'status': status,
        'detail': str(detail)[:500], 'ms': ms,
    })


# ─── SSH 封装 ────────────────────────────────────────────────────────
ssh = None


def connect_ssh():
    global ssh
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS,
                look_for_keys=False, allow_agent=False, timeout=15)


def run(cmd, timeout=30):
    """在服务器执行命令，返回 (stdout, stderr, exit_code)"""
    stdin, out, err = ssh.exec_command(cmd, timeout=timeout)
    code = out.channel.recv_exit_status()
    return out.read().decode('utf-8', 'replace').strip(), \
        err.read().decode('utf-8', 'replace').strip(), code


def curl_json(url, method='GET', headers=None, data=None, timeout=20):
    """在服务器上 curl 一个 URL，返回 (http_code, parsed_json_or_text, raw)"""
    parts = [f'curl -s -m {timeout} -o /tmp/_fst_body -w "%{{http_code}}"']
    if method != 'GET':
        parts.append(f'-X {method}')
    for k, v in (headers or {}).items():
        parts.append(f'-H "{k}: {v}"')
    if data is not None:
        body = json.dumps(data).replace("'", "'\\''")
        parts.append(f"-d '{body}'")
    parts.append(f'"{url}"')
    cmd = ' '.join(parts) + '; echo; cat /tmp/_fst_body'
    out, _, _ = run(cmd, timeout=timeout + 5)
    # out = "<http_code>\n<body>"
    http_code = 0
    body = ''
    if '\n' in out:
        head, body = out.split('\n', 1)
        try:
            http_code = int(head.strip())
        except ValueError:
            http_code = 0
    else:
        try:
            http_code = int(out.strip())
        except ValueError:
            http_code = 0
    parsed = None
    try:
        parsed = json.loads(body) if body.strip() else None
    except (json.JSONDecodeError, ValueError):
        parsed = None
    return http_code, parsed, body


# ═══════════════════════════════════════════════════════════════════
# Auth: 换取 admin JWT
# ═══════════════════════════════════════════════════════════════════
def get_admin_jwt():
    """用 client_type=desktop 登录管理后台，返回纯 JSON token（不设 cookie）"""
    if not ADMIN_PASS:
        record('Auth', '获取 admin JWT', 'warn',
               '未提供 ADMIN_PASS 环境变量，L2/L3 需鉴权的项将被跳过')
        return None
    code, parsed, raw = curl_json(
        'http://localhost:8084/admin/login', method='POST',
        headers={'Content-Type': 'application/json'},
        data={'username': ADMIN_USER, 'password': ADMIN_PASS, 'client_type': 'desktop'},
    )
    token = None
    if code == 200 and isinstance(parsed, dict) and parsed.get('success'):
        token = (parsed.get('data') or {}).get('token')
    if token:
        record('Auth', '获取 admin JWT', 'pass', f'token 长度={len(token)}')
    else:
        record('Auth', '获取 admin JWT', 'fail', f'HTTP {code} resp={raw[:200]}')
    return token


# ═══════════════════════════════════════════════════════════════════
# L0 服务存活
# ═══════════════════════════════════════════════════════════════════
def test_l0_liveness():
    print('\n【L0】服务存活探测')
    for name, port in LOCAL_SERVICES:
        t0 = time.time()
        code, parsed, raw = curl_json(f'http://127.0.0.1:{port}/health', timeout=6)
        ms = int((time.time() - t0) * 1000)
        if code == 200:
            record('L0', f'{name}:{port}/health', 'pass', raw[:80], ms)
        else:
            record('L0', f'{name}:{port}/health', 'fail', f'HTTP {code} {raw[:120]}', ms)


# ═══════════════════════════════════════════════════════════════════
# L1 就绪探测
# ═══════════════════════════════════════════════════════════════════
def test_l1_readiness():
    print('\n【L1】就绪 / 数据库连通探测')
    code, parsed, raw = curl_json('http://127.0.0.1:8085/ready', timeout=8)
    if code == 200 and isinstance(parsed, dict) and parsed.get('status') == 'ready':
        record('L1', 'health-service /ready (DB 连通)', 'pass', raw[:80])
    else:
        record('L1', 'health-service /ready (DB 连通)', 'fail', f'HTTP {code} {raw[:150]}')


# ═══════════════════════════════════════════════════════════════════
# L2 深度体检
# ═══════════════════════════════════════════════════════════════════
def _fetch_latest_run(jwt, timeout=20):
    """读取 GET /api/status，返回 (run_dict, items)。用于 L2/L5 共用。"""
    code, parsed, raw = curl_json(
        'http://localhost:8084/admin/health/api/status',
        headers={'Authorization': f'Bearer {jwt}'}, timeout=timeout,
    )
    if code != 200 or not isinstance(parsed, dict):
        return None, [], (code, raw)
    latest = (parsed.get('data') or {}).get('latest_run') or {}
    items = latest.get('items') or []
    return latest, items, (code, raw)


def test_l2_deep_inspection(jwt):
    print('\n【L2】深度体检（health/api/run 全 checker）')
    if not jwt:
        record('L2', '触发 health/api/run', 'warn', '无 admin JWT，跳过深度体检')
        return
    # /api/run 是异步接口：启动后台线程后立即返回 {success, message}，
    # 需先记录当前最新 run 的时间戳，再触发，然后轮询直到出现更新的 run。
    prev_run, _, _ = _fetch_latest_run(jwt)
    prev_ts = (prev_run or {}).get('created_at') or (prev_run or {}).get('id')

    auth = {'Authorization': f'Bearer {jwt}', 'Content-Type': 'application/json'}
    t0 = time.time()
    code, parsed, raw = curl_json(
        'http://localhost:8084/admin/health/api/run',
        method='POST', headers=auth, data={}, timeout=30,
    )
    if code != 200 or not (isinstance(parsed, dict) and parsed.get('success')):
        record('L2', '触发 health/api/run', 'fail', f'HTTP {code} {raw[:200]}')
        return
    record('L2', '触发 health/api/run（异步）', 'pass',
           parsed.get('message', ''), int((time.time() - t0) * 1000))

    # 轮询等待新 run 完成（最多 ~40 秒）
    latest, items, dbg = None, [], None
    for _ in range(20):
        time.sleep(2)
        latest, items, dbg = _fetch_latest_run(jwt)
        cur_ts = (latest or {}).get('created_at') or (latest or {}).get('id')
        status = (latest or {}).get('status')
        if latest and cur_ts != prev_ts and status == 'completed' and items:
            break
    if not items:
        record('L2', '拉取体检明细', 'warn',
               f'轮询超时或无明细（异步检查可能仍在进行）dbg={dbg}')
        return
    for it in items:
        key = it.get('check_key') or it.get('check_name') or 'unknown'
        st = (it.get('status') or '').lower()
        msg = it.get('message', '')
        ims = it.get('response_time_ms', 0)
        mapped = 'pass' if st == 'passed' else ('warn' if st == 'warning' else 'fail')
        record('L2', f'checker: {key}', mapped, msg, ims)


# ═══════════════════════════════════════════════════════════════════
# L3 路由 + JWT SSO
# ═══════════════════════════════════════════════════════════════════
def test_l3_routing_sso(jwt):
    print('\n【L3】Nginx 路由可达 + JWT SSO 跨子域')
    # 3.1 各域名/子路由 HTTPS 可达（从服务器本机 curl，避免出网限制）
    routes = [
        (f'https://{MAIN_DOMAIN}/',          '主站根路由'),
        (f'https://{MAIN_DOMAIN}/admin/login', 'admin 登录页'),
        (f'https://{MAIN_DOMAIN}/auth/',      'auth 认证路由'),
        (f'https://{PLATFORM_DOMAIN}/',       'platform 子域'),
        (f'https://{AGENT_DOMAIN}/',          'agent 子域'),
    ]
    for url, label in routes:
        code, _, raw = _curl_status(url)
        # 2xx/3xx/401/403 均视为“路由可达”（服务在响应）；仅连接失败/5xx 视为异常
        if code in (200, 301, 302, 303, 307, 308, 401, 403):
            record('L3', f'HTTPS 可达: {label}', 'pass', f'HTTP {code}')
        elif code == 0:
            record('L3', f'HTTPS 可达: {label}', 'fail', f'连接失败 {raw[:120]}')
        else:
            record('L3', f'HTTPS 可达: {label}', 'warn', f'HTTP {code}')

    # 3.2 JWT SSO 跨子域免登：带同一 admin JWT 访问 platform 受登录保护接口
    if not jwt:
        record('L3', 'SSO 跨子域免登', 'warn', '无 admin JWT，跳过 SSO 验证')
    else:
        # platform 的需登录接口：/api/notifications/unread-count（Cookie sso_token 鉴权）
        code, parsed, raw = curl_json(
            'http://127.0.0.1:8083/api/notifications/unread-count',
            headers={'Cookie': f'sso_token={jwt}'}, timeout=15,
        )
        if code == 200:
            record('L3', 'SSO: platform 免登通过', 'pass', raw[:100])
        elif code in (401, 403):
            record('L3', 'SSO: platform 免登通过', 'fail',
                   f'HTTP {code} — 同一 token 在 platform 未通过，疑似 Cookie Domain 未跨子域')
        else:
            record('L3', 'SSO: platform 免登通过', 'warn', f'HTTP {code} {raw[:120]}')

        # 3.3 token 边界：篡改 token 应被拒绝
        bad = jwt[:-3] + 'xxx' if len(jwt) > 3 else 'invalid'
        code, parsed, raw = curl_json(
            'http://127.0.0.1:8084/admin/health/api/status',
            headers={'Authorization': f'Bearer {bad}'}, timeout=15,
        )
        if code in (401, 403):
            record('L3', 'SSO: 篡改 token 被拒', 'pass', f'HTTP {code}')
        elif code == 200:
            record('L3', 'SSO: 篡改 token 被拒', 'fail', '篡改 token 竟然通过鉴权！')
        else:
            record('L3', 'SSO: 篡改 token 被拒', 'warn', f'HTTP {code}')


def _curl_status(url):
    """仅取 HTTP 状态码（跟随重定向 -L，忽略证书 -k），返回 (code, None, raw)"""
    out, _, _ = run(
        f'curl -s -k -L -m 15 -o /dev/null -w "%{{http_code}}" "{url}"', timeout=25
    )
    try:
        return int(out.strip()), None, out
    except ValueError:
        return 0, None, out


# ═══════════════════════════════════════════════════════════════════
# L4 业务冒烟
# ═══════════════════════════════════════════════════════════════════
def test_l4_smoke(jwt):
    print('\n【L4】业务冒烟（GET 只读接口）')
    # 4.1 验证码：现由 admin:8084 的 captcha_embedded 插件承载，
    #     主站 8081 通过 /api/captcha/generate 代理暴露入口（无独立 8090 服务）
    code, _, raw = curl_json('http://127.0.0.1:8081/api/captcha/generate', timeout=8)
    if code == 200:
        record('L4', '验证码代理 8081/api/captcha/generate', 'pass', raw[:60])
    else:
        record('L4', '验证码代理 8081/api/captcha/generate', 'warn', f'HTTP {code} {raw[:120]}')

    # 4.2 插件系统 discover（需 admin）
    hdr = {'Authorization': f'Bearer {jwt}'} if jwt else {}
    code, parsed, raw = curl_json('http://localhost:8084/admin/plugins/discover',
                                  headers=hdr, timeout=20)
    if code == 200 and isinstance(parsed, dict):
        plugins = parsed.get('plugins') or (parsed.get('data') or {}).get('plugins') or []
        record('L4', f'插件 discover（{len(plugins)} 个）', 'pass' if plugins else 'warn',
               raw[:100])
    elif code in (401, 403):
        record('L4', '插件 discover', 'warn', f'HTTP {code}（需鉴权，未提供 token）')
    else:
        record('L4', '插件 discover', 'fail', f'HTTP {code} {raw[:120]}')

    # 4.3 主站首页可访问
    code, _, _ = _curl_status(f'https://{MAIN_DOMAIN}/')
    record('L4', '主站首页渲染', 'pass' if code == 200 else 'warn', f'HTTP {code}')


# ═══════════════════════════════════════════════════════════════════
# L5 定时任务（交叉验证 workflow_engine checker）
# ═══════════════════════════════════════════════════════════════════
def test_l5_scheduler(jwt):
    print('\n【L5】定时任务 / 工作流交叉验证')
    if not jwt:
        record('L5', '工作流引擎状态', 'warn', '无 admin JWT，跳过')
        return
    latest, items, dbg = _fetch_latest_run(jwt)
    if not items:
        record('L5', '工作流引擎状态', 'warn', f'无最新体检数据 dbg={dbg}')
        return
    found = False
    for c in items:
        if c.get('check_key') == 'workflow_engine':
            found = True
            st = (c.get('status') or '').lower()
            mapped = 'pass' if st == 'passed' else ('warn' if st == 'warning' else 'fail')
            record('L5', 'workflow_engine', mapped, c.get('message', ''))
    if not found:
        record('L5', 'workflow_engine', 'warn', '最新体检未包含该项（已由 L2 覆盖）')


# ═══════════════════════════════════════════════════════════════════
# 报告输出
# ═══════════════════════════════════════════════════════════════════
def write_report():
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = sum(_counts.values())
    lines = []
    lines.append(f'# 易站系统全面测试报告\n')
    lines.append(f'- 生成时间: {ts}')
    lines.append(f'- 目标服务器: {USER}@{HOST}')
    lines.append(f'- 汇总: ✅ {_counts["pass"]}  ⚠️ {_counts["warn"]}  ❌ {_counts["fail"]}  '
                 f'(共 {total} 项)\n')

    # 按层分组
    layers = {}
    for r in RESULTS:
        layers.setdefault(r['layer'], []).append(r)
    for layer in sorted(layers.keys()):
        lines.append(f'## {layer}\n')
        lines.append('| 状态 | 项目 | 耗时 | 详情 |')
        lines.append('|------|------|------|------|')
        for r in layers[layer]:
            icon = {'pass': '✅', 'warn': '⚠️', 'fail': '❌'}[r['status']]
            detail = r['detail'].replace('|', '\\|').replace('\n', ' ')
            ms = f'{r["ms"]}ms' if r['ms'] else '-'
            lines.append(f'| {icon} | {r["name"]} | {ms} | {detail} |')
        lines.append('')

    content = '\n'.join(lines)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'\n报告已写入: {REPORT_FILE}')


# ═══════════════════════════════════════════════════════════════════
def main():
    print('=' * 64)
    print('  易站智能建站系统 — 全面系统测试（只读 / 幂等）')
    print(f'  目标: {USER}@{HOST}')
    print('=' * 64)

    try:
        connect_ssh()
    except Exception as e:
        print(f'❌ SSH 连接失败: {e}')
        sys.exit(2)

    try:
        jwt = get_admin_jwt()
        test_l0_liveness()
        test_l1_readiness()
        test_l2_deep_inspection(jwt)
        test_l3_routing_sso(jwt)
        test_l4_smoke(jwt)
        test_l5_scheduler(jwt)
    finally:
        try:
            ssh.close()
        except Exception:
            pass

    # 汇总
    print('\n' + '=' * 64)
    print(f'  测试完成: ✅ {_counts["pass"]}  ⚠️ {_counts["warn"]}  ❌ {_counts["fail"]}')
    print('=' * 64)
    write_report()

    sys.exit(1 if _counts['fail'] > 0 else 0)


if __name__ == '__main__':
    main()
