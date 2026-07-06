# Health Check 独立进程 + Health Guardian 架构方案

## 一、问题背景

### 1.1 当前架构缺陷

```
┌───────────────────────────────┐
│  admin Flask (8084)           │
│  ┌─────────────────────────┐  │
│  │  Health Check 内嵌模块   │  │  ← 与 admin 耦合
│  │  - checkers             │  │     admin 挂了它也跟着挂
│  │  - alerter              │  │     无法自检
│  │  - routes + Dashboard   │  │
│  │  - AI fix + audit       │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
```

### 1.2 核心问题

| 问题 | 后果 |
|------|------|
| Health Check 内嵌在 admin Flask | admin 崩了 Health Check 也崩，无法自检 |
| 没有独立守护进程 | 代码推送错 → 系统崩溃 → 无法自动恢复 |
| 无法区分"主应用挂了"和"健康检查本身挂了" | 告警误导，诊断困难 |

---

## 二、目标架构

### 2.1 三层独立体系

```
┌─────────────────────────────────────────────────────┐
│                   用户访问层                           │
│  https://easykai.cn/admin/health/                    │
│  ↓ Nginx 路由                                        │
├─────────────────────────────────────────────────────┤
│                   逻辑服务层                           │
│  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  admin (8084)    │  │  health-service (8085)    │  │
│  │  AJAX 嵌入       │  │  独立 Flask 服务           │  │
│  │  指向 health     │  │  - checkers / alerter    │  │
│  │  Dashboard       │  │  - AI fix / audit        │  │
│  └──────────────────┘  │  - Prometheus metrics    │  │
│                         │  - Dashboard (自身)      │  │
│                         └──────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│                   系统守护层                           │
│  ┌──────────────────────────────────────────────┐   │
│  │  Health Guardian (极简看门狗)                  │   │
│  │  0 外部依赖，纯 Python 标准库                   │   │
│  │  定时 curl health-service:8085/health         │   │
│  │  失败阶梯：retry → restart → 从 GitHub tag 回滚  │   │
│  │  回滚后冷却期防循环回滚                         │   │
│  │  → Webhook 通知                               │   │
│  │  systemd 守护，挂了自动重启                     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 2.2 关键优势

| 层次 | 优势 |
|------|------|
| health-service 独立 | admin 挂了，Health Check 继续运行，仍可告警 |
| Guardian 独立 | health-service 挂了，Guardian 还能 curl 并回滚 |
| 零依赖 | Guardian 不用 Flask、不用 SQLite、不用任何第三方库 |
| 回滚安全 | 只拉不可变的 git tag，不拉变动的 master |

### 2.3 参考来源

本架构的设计借鉴了以下业界实践：
- **OpenClaw Guardian**（GitHub: Ramsbaby/openclaw-guardian）的冷却期（Cooldown）、Webhook 通知、重试阶梯模式
- **Kubernetes Liveness/Readiness Probe** 的三层探针体系
- **systemd Watchdog** 的系统级守护机制

---

## 三、Health Service (独立进程)

### 3.1 文件结构

```
health_service/
├── app.py                 # Flask 入口，独立启动
├── run_health_service.py  # gunicorn 启动脚本
├── checkers.py            # 从 health_check/ 迁移
├── alerter.py             # 从 health_check/ 迁移
├── ai_fixer.py            # 从 health_check/ 迁移
├── models.py              # 从 health_check/ 迁移
├── metrics.py             # 从 health_check/ 迁移
├── discovery.py           # 从 health_check/ 迁移
├── templates/
│   └── health.html        # Dashboard
└── requirements.txt       # 仅 flask, gunicorn
```

### 3.2 app.py 入口

```python
#!/usr/bin/env python3
"""Health Service — 独立 Flask 入口"""
from flask import Flask
from health_check.routes import health_bp
from health_check.models import init_health_tables, migrate_alert_schema

app = Flask(__name__)
app.register_blueprint(health_bp)  # url_prefix=/admin/health

@app.route('/health')
def ping():
    return {'status': 'ok', 'service': 'health-service'}

if __name__ == '__main__':
    init_health_tables()
    migrate_alert_schema()
    app.run(host='0.0.0.0', port=8085)
```

### 3.3 systemd 服务

**文件：** `/etc/systemd/system/health.service`

```ini
[Unit]
Description=Health Check Service (8085)
After=network.target

[Service]
Type=simple
User=easykai
WorkingDirectory=/home/easykai/easykai-workspace/easykai.cn
ExecStart=/usr/bin/python3 -m gunicorn -w 2 --max-requests=1000 \
    -b 0.0.0.0:8085 health_service.app:app \
    --timeout 30 --graceful-timeout 30 --log-level warning
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 四、Health Guardian (极简守护进程)

### 4.1 设计原则

- **零外部依赖**：只用 Python 标准库（`urllib`、`subprocess`、`time`）
- **极简逻辑**：curl → 计数 → 失败 N 次 → 阶梯恢复
- **systemd 管理**：挂了自动重启
- **无状态**：不写数据库，只写日志
- **环境变量配置**：所有参数可通过 env var 覆盖

### 4.2 恢复阶梯

```
连续 3 次 (30s × 3 = 90 秒) 检查失败
                ↓
    第 1 次失败 → 仅记录日志
    第 2 次失败 → 记录日志
    第 3 次失败 → systemctl restart 对应服务（尝试修复）
    仍失败 → 
                ↓
从 GitHub raw 拉取 stable tag 版本文件
                ↓
systemctl restart 对应服务
                ↓
发送 Webhook 通知（如已配置）
                ↓
进入冷却期（默认 300s），期间跳过所有检查
```

### 4.3 核心代码

```python
#!/usr/bin/env python3
"""
Health Guardian — 独立看门狗
0 外部依赖，定时检查关键端点，失败 N 次后从 GitHub tag 回滚
"""
import urllib.request
import subprocess
import time
import logging
import os
import sys
import json

# ─── 配置（优先级：环境变量 > 默认值） ─────────────────
TARGETS = [
    "http://127.0.0.1:8085/health",          # health-service 自身
    "http://127.0.0.1:8081/health",          # 主站
    "http://127.0.0.1:8084/health",          # admin
    "http://127.0.0.1:8083/health",          # platform
]

CHECK_INTERVAL  = int(os.getenv('GUARDIAN_CHECK_INTERVAL', '30'))
MAX_FAILURES    = int(os.getenv('GUARDIAN_MAX_FAILURES', '3'))
COOLDOWN_SECS   = int(os.getenv('GUARDIAN_COOLDOWN', '300'))       # 冷却期
ROLLBACK_TAG    = os.getenv('GUARDIAN_ROLLBACK_TAG', 'stable')
WEBHOOK_URL     = os.getenv('GUARDIAN_WEBHOOK_URL', '')            # 通知 URL
PROJECT_DIR     = os.getenv('GUARDIAN_PROJECT_DIR',
                    '/home/easykai/easykai-workspace/easykai.cn')
LOG_FILE        = os.getenv('GUARDIAN_LOG_FILE',
                    '/var/log/health-guardian.log')

GITHUB_RAW_BASE = os.getenv('GUARDIAN_GITHUB_RAW',
                    'https://raw.githubusercontent.com/fanjumin/VeroRunSystem')

# 各服务 systemd unit 名称
SERVICE_MAP = {
    "http://127.0.0.1:8085/health": "health",
    "http://127.0.0.1:8081/health": "easykai",
    "http://127.0.0.1:8084/health": "admin",
    "http://127.0.0.1:8083/health": "platform",
}

FILES_TO_RESTORE = [
    "health_check/routes.py",
    "health_check/checkers.py",
    "health_check/ai_fixer.py",
    "health_check/models.py",
    "health_check/templates/health.html",
]

# ─── 日志 ──────────────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ─── 通知 ──────────────────────────────────────────────
def send_webhook(message: str, severity: str = "warning"):
    """发送 Webhook 通知（如已配置 URL）"""
    if not WEBHOOK_URL:
        return
    try:
        payload = json.dumps({
            "text": message,
            "severity": severity,
            "service": "health-guardian",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }).encode()
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        logging.info(f"Webhook sent: {severity} - {message}")
    except Exception as e:
        logging.error(f"Webhook failed: {e}")

# ─── 重启服务 ──────────────────────────────────────────
def restart_service(service_name: str) -> bool:
    """重启 systemd 服务，返回是否成功"""
    try:
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            timeout=15, capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            logging.info(f"Service '{service_name}' restarted OK")
            return True
        else:
            logging.error(f"Service '{service_name}' restart failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        logging.error(f"Service '{service_name}' restart error: {e}")
        return False

# ─── 回滚 ──────────────────────────────────────────────
def rollback(failed_url: str):
    """从 GitHub tag 拉取关键文件回滚"""
    tag = ROLLBACK_TAG
    base_url = f"{GITHUB_RAW_BASE}/{tag}"

    logging.warning(f"Rolling back to tag {tag}")

    for filepath in FILES_TO_RESTORE:
        url = f"{base_url}/{filepath}"
        dest = os.path.join(PROJECT_DIR, filepath)
        try:
            req = urllib.request.urlopen(url, timeout=15)
            content = req.read()
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(content)
            logging.info(f"  Restored {filepath}")
        except Exception as e:
            logging.error(f"  Failed {filepath}: {e}")

    # 重启对应的服务
    service_name = SERVICE_MAP.get(failed_url, "health")
    ok = restart_service(service_name)
    logging.info(f"Rollback complete, {service_name} {'OK' if ok else 'FAILED'}")

# ─── 主循环 ────────────────────────────────────────────
def main():
    failures = 0
    cooldown_until = 0
    logging.info("Health Guardian started")

    # 如果命令行有 --rollback-now，手动触发回滚
    if "--rollback-now" in sys.argv:
        logging.warning("Manual rollback triggered via --rollback-now")
        rollback(TARGETS[0])
        send_webhook("Manual rollback executed", "critical")
        return

    while True:
        # 冷却期跳过检查
        if time.time() < cooldown_until:
            remaining = int(cooldown_until - time.time())
            if remaining % CHECK_INTERVAL == 0:  # 每间隔打印一次
                logging.info(f"Cooldown: {remaining}s remaining")
            time.sleep(CHECK_INTERVAL)
            continue

        all_ok = True
        first_failed_url = None

        for url in TARGETS:
            try:
                resp = urllib.request.urlopen(url, timeout=5)
                if resp.status != 200:
                    all_ok = False
                    first_failed_url = first_failed_url or url
                    logging.warning(f"{url} → {resp.status}")
            except Exception as e:
                all_ok = False
                first_failed_url = first_failed_url or url
                logging.warning(f"{url} → {e}")

        if all_ok:
            failures = 0
        else:
            failures += 1
            logging.warning(f"Failures: {failures}/{MAX_FAILURES}")

        if failures >= MAX_FAILURES and first_failed_url:
            service_name = SERVICE_MAP.get(first_failed_url, "health")

            # 阶梯 1：先尝试重启服务
            logging.warning(f"Attempting restart of '{service_name}' before rollback")
            ok = restart_service(service_name)

            # 等待几秒后再次检查
            time.sleep(5)
            try:
                resp = urllib.request.urlopen(first_failed_url, timeout=5)
                if resp.status == 200:
                    logging.info(f"Restart fixed '{service_name}', no rollback needed")
                    failures = 0
                    time.sleep(CHECK_INTERVAL)
                    continue
            except Exception:
                pass

            # 阶梯 2：重启无效，执行回滚
            logging.warning(f"Restart failed, proceeding to rollback for {first_failed_url}")
            rollback(first_failed_url)
            msg = f"Rollback triggered for {first_failed_url} (service: {service_name}) at tag {ROLLBACK_TAG}"
            send_webhook(msg, "critical")

            failures = 0
            cooldown_until = time.time() + COOLDOWN_SECS
            logging.warning(f"Entering cooldown for {COOLDOWN_SECS}s")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
```

### 4.4 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GUARDIAN_CHECK_INTERVAL` | `30` | 检查间隔（秒） |
| `GUARDIAN_MAX_FAILURES` | `3` | 连续失败触发阈值 |
| `GUARDIAN_COOLDOWN` | `300` | 回滚后冷却期（秒） |
| `GUARDIAN_ROLLBACK_TAG` | `stable` | 回滚目标 git tag |
| `GUARDIAN_WEBHOOK_URL` | `""` | Webhook 通知 URL（为空则不通知） |
| `GUARDIAN_PROJECT_DIR` | `/home/easykai/easykai-workspace/easykai.cn` | 项目目录 |
| `GUARDIAN_LOG_FILE` | `/var/log/health-guardian.log` | 日志文件路径 |
| `GUARDIAN_GITHUB_RAW` | `https://raw.githubusercontent.com/fanjumin/VeroRunSystem` | GitHub raw 基础 URL |

### 4.5 systemd 服务

**文件：** `/etc/systemd/system/health-guardian.service`

```ini
[Unit]
Description=Health Guardian — 独立看门狗 / 自动回滚
Documentation=https://github.com/fanjumin/VeroRunSystem
After=network.target health.service
Requires=health.service

[Service]
Type=simple
User=root
EnvironmentFile=-/etc/default/health-guardian
ExecStart=/usr/bin/python3 /home/easykai/easykai-workspace/easykai.cn/health_guardian.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**环境变量文件：** `/etc/default/health-guardian`

```
# Guardian 环境变量配置
GUARDIAN_CHECK_INTERVAL=30
GUARDIAN_MAX_FAILURES=3
GUARDIAN_COOLDOWN=300
GUARDIAN_ROLLBACK_TAG=stable
GUARDIAN_WEBHOOK_URL=
GUARDIAN_LOG_FILE=/var/log/health-guardian.log
```

---

## 五、Nginx 路由

### 5.1 当前

```nginx
# admin (8084) 直接渲染 Health Dashboard
location /admin/health/ {
    proxy_pass http://127.0.0.1:8084/admin/health/;
}
```

### 5.2 改后

```nginx
# health-service (8085) 独立服务
location /admin/health/ {
    proxy_pass http://127.0.0.1:8085/admin/health/;
}
```

admin Dashboard 的 Health Check 标签页保持 **AJAX HTML 嵌入**方式，只需将请求代理从 8084 改为 8085。

---

## 六、回滚流程

### 6.1 前置条件

1. 每次部署前打 tag：`git tag deploy-$(date +%Y%m%d)` 并 `git push origin --tags`
2. 维护一个 `stable` tag 指向当前稳定的部署版本
3. GitHub 仓库 `fanjumin/VeroRunSystem` 必须是最新状态

### 6.2 回滚触发条件

```
连续 3 次 (CHECK_INTERVAL × 3 = 90 秒) 检查失败
                ↓
Health Guardian 判定"服务异常"
                ↓
阶梯 1: systemctl restart <service>（尝试修复）
                ↓
等待 5 秒后再次检查
                ↓
仍失败 →
阶梯 2: 从 GitHub raw 拉取 stable tag 版本文件
                ↓
systemctl restart <service>
                ↓
发送 Webhook 通知
                ↓
进入冷却期 (300 秒)，防循环回滚
```

### 6.3 手动回滚

```bash
# SSH 到服务器
ssh easykai@***REMOVED***

# 手动触发回滚
python3 /home/easykai/easykai-workspace/easykai.cn/health_guardian.py --rollback-now

# 或拉取指定 tag
wget -q -O /path/to/file.py \
  https://raw.githubusercontent.com/fanjumin/VeroRunSystem/deploy-20260706/health_check/routes.py
systemctl restart health
```

---

## 七、每日快照机制

### 7.1 原理

Guardian 提供一个 `--snapshot` 模式，由 systemd timer 每日触发：
- 自动 `git add` 关键目录
- `git commit -m "auto-snapshot: YYYY-MM-DD"`
- 不 `git push`（只在本地作为恢复点）

### 7.2 systemd timer 配置

**文件：** `/etc/systemd/system/health-snapshot.service`

```ini
[Unit]
Description=Daily Health Guardian Snapshot

[Service]
Type=oneshot
User=easykai
WorkingDirectory=/home/easykai/easykai-workspace/easykai.cn
ExecStart=/usr/bin/python3 /home/easykai/easykai-workspace/easykai.cn/health_guardian.py --snapshot
```

**文件：** `/etc/systemd/system/health-snapshot.timer`

```ini
[Unit]
Description=Daily snapshot for Health Guardian rollback

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

### 7.3 快照模式代码（health_guardian.py 中）

```python
def take_snapshot():
    """每日快照：自动 git commit 本地变更，作为回滚恢复点"""
    import subprocess
    try:
        subprocess.run(["git", "add", "health_check/"], cwd=PROJECT_DIR,
                       timeout=30, check=False, capture_output=True)
        date_str = time.strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "commit", "-m", f"auto-snapshot: {date_str}"],
            cwd=PROJECT_DIR, timeout=30, check=False,
            capture_output=True, text=True,
        )
        logging.info(f"Snapshot: {result.stdout.strip()}")
    except Exception as e:
        logging.error(f"Snapshot failed: {e}")
```

---

## 八、部署步骤

### 8.1 创建 health_service 目录

```bash
mkdir -p /home/easykai/easykai-workspace/easykai.cn/health_service
```

### 8.2 创建 app.py + run_health_service.py

### 8.3 部署 health_guardian.py

```bash
scp health_guardian.py easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/
```

### 8.4 部署环境变量文件

```bash
scp health-guardian.env easykai@***REMOVED***:/tmp/
ssh easykai@***REMOVED*** "sudo mv /tmp/health-guardian.env /etc/default/health-guardian"
```

### 8.5 注册 systemd 服务

```bash
# health.service
sudo systemctl daemon-reload
sudo systemctl enable health.service
sudo systemctl start health.service

# health-guardian.service
sudo systemctl enable health-guardian.service
sudo systemctl start health-guardian.service

# health-snapshot.timer
sudo systemctl enable health-snapshot.timer
sudo systemctl start health-snapshot.timer
```

### 8.6 验证

```bash
curl http://127.0.0.1:8085/health
# → {"status": "ok", "service": "health-service"}

curl http://127.0.0.1:8085/admin/health/api/status
# → Health Check Dashboard API 正常返回

systemctl status health-guardian
# → active (running)

systemctl status health-snapshot.timer
# → active (waiting)
```

---

## 九、风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| Guardian 回滚拉取 GitHub 超时 | 增加 timeout=15，失败跳过单个文件 |
| 回滚后代码仍有问题 | Guardian 只回滚一次，+ 冷却期 (300s) 防循环回滚 |
| GitHub token 过期 | 公开仓库不需要 token，raw 可匿名访问 |
| 数据库兼容性 | 回滚不涉及数据库，只回滚代码文件 |
| systemd 依赖顺序 | health-guardian 设置 `After=health.service` |
| 冷却期内真实故障被忽略 | 冷却期默认 300s 较短，Guardian 本身由 systemd 守护 |

---

<!-- 文档版本: v2.0 | 最后更新: 2026-07-06 | 更新内容: 借鉴 OpenClaw Guardian 增加冷却期、Webhook 通知、恢复阶梯、每日快照、环境变量配置 -->
