#!/usr/bin/env python3
"""
Health Guardian — 独立看门狗 (v2.0)
===============================================
0 外部依赖，纯 Python 标准库。
定时检查关键端点，失败 N 次后阶梯恢复：
  阶梯 1: systemctl restart <service>
  阶梯 2: 从 GitHub tag 拉文件回滚

特性：
  - 冷却期 (Cooldown)：回滚后暂停 N 秒，防循环回滚
  - Webhook 通知：回滚触发时发送 JSON POST
  - 每日快照：--snapshot 模式创建本地 git commit
  - 环境变量配置：所有参数可覆盖

参考 OpenClaw Guardian (github.com/Ramsbaby/openclaw-guardian):
  - Cooldown 机制
  - 分阶梯恢复 (retry → fix → rollback)
  - 通知机制

用法:
    python3 health_guardian.py                # 启动守护进程
    python3 health_guardian.py --rollback-now # 手动回滚
    python3 health_guardian.py --snapshot     # 创建每日快照
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib.request

# ─── 配置（优先级：环境变量 > 默认值） ─────────────────
TARGETS = [
    "http://127.0.0.1:8085/health",          # health-service 自身
    "http://127.0.0.1:8081/health",          # 主站
    "http://127.0.0.1:8084/health",          # admin
    "http://127.0.0.1:8083/health",          # platform
]

CHECK_INTERVAL  = int(os.getenv('GUARDIAN_CHECK_INTERVAL', '30'))
MAX_FAILURES    = int(os.getenv('GUARDIAN_MAX_FAILURES', '3'))
COOLDOWN_SECS   = int(os.getenv('GUARDIAN_COOLDOWN', '300'))
ROLLBACK_TAG    = os.getenv('GUARDIAN_ROLLBACK_TAG', 'stable')
WEBHOOK_URL     = os.getenv('GUARDIAN_WEBHOOK_URL', '')
PROJECT_DIR     = os.getenv('GUARDIAN_PROJECT_DIR',
                    '/home/easykai/easykai-workspace/easykai.cn')
LOG_FILE        = os.getenv('GUARDIAN_LOG_FILE',
                    '/var/log/health-guardian.log')
GITHUB_RAW_BASE = os.getenv('GUARDIAN_GITHUB_RAW',
                    'https://raw.githubusercontent.com/fanjumin/VeroRunSystem')

# 各端点 → systemd service 名称映射
SERVICE_MAP = {
    "http://127.0.0.1:8085/health": "health",
    "http://127.0.0.1:8081/health": "auth-center",
    "http://127.0.0.1:8084/health": "admin",
    "http://127.0.0.1:8083/health": "platform",
}

# 回滚时恢复的文件列表（相对路径）
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


# ===================================================================
#  通知
# ===================================================================
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
        logging.info("Webhook sent: %s - %s", severity, message)
    except Exception as e:
        logging.error("Webhook failed: %s", e)


# ===================================================================
#  系统操作
# ===================================================================
def restart_service(service_name: str) -> bool:
    """重启 systemd 服务，返回是否成功"""
    try:
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            timeout=15, capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            logging.info("Service '%s' restarted OK", service_name)
            return True
        else:
            logging.error("Service '%s' restart failed: %s",
                          service_name, result.stderr.strip())
            return False
    except Exception as e:
        logging.error("Service '%s' restart error: %s", service_name, e)
        return False


def rollback(failed_url: str):
    """从 GitHub tag 拉取关键文件回滚"""
    tag = ROLLBACK_TAG
    base_url = "%s/%s" % (GITHUB_RAW_BASE, tag)
    logging.warning("Rolling back to tag %s", tag)

    for filepath in FILES_TO_RESTORE:
        url = "%s/%s" % (base_url, filepath)
        dest = os.path.join(PROJECT_DIR, filepath)
        try:
            req = urllib.request.urlopen(url, timeout=15)
            content = req.read()
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(content)
            logging.info("  Restored %s", filepath)
        except Exception as e:
            logging.error("  Failed %s: %s", filepath, e)

    # 重启对应的服务
    service_name = SERVICE_MAP.get(failed_url, "health")
    ok = restart_service(service_name)
    logging.info("Rollback complete, %s %s",
                 service_name, 'OK' if ok else 'FAILED')


# ===================================================================
#  每日快照
# ===================================================================
def take_snapshot():
    """每日快照：自动 git commit 本地变更，作为回滚恢复点"""
    try:
        subprocess.run(
            ["git", "add", "health_check/"],
            cwd=PROJECT_DIR, timeout=30, check=False,
            capture_output=True,
        )
        date_str = time.strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "commit", "-m", "auto-snapshot: %s" % date_str],
            cwd=PROJECT_DIR, timeout=30, check=False,
            capture_output=True, text=True,
        )
        logging.info("Snapshot: %s", result.stdout.strip())
    except Exception as e:
        logging.error("Snapshot failed: %s", e)


# ===================================================================
#  主循环
# ===================================================================
def main():
    failures = 0
    cooldown_until = 0
    logging.info("Health Guardian started")

    # --rollback-now：手动回滚
    if "--rollback-now" in sys.argv:
        logging.warning("Manual rollback triggered via --rollback-now")
        rollback(TARGETS[0])
        send_webhook("Manual rollback executed", "critical")
        return

    # --snapshot：每日快照
    if "--snapshot" in sys.argv:
        logging.info("Snapshot mode triggered")
        take_snapshot()
        return

    # ── 主循环 ──
    while True:
        # 冷却期跳过检查
        if time.time() < cooldown_until:
            remaining = int(cooldown_until - time.time())
            if remaining % CHECK_INTERVAL == 0:
                logging.info("Cooldown: %ds remaining", remaining)
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
                    logging.warning("%s -> %s", url, resp.status)
            except Exception as e:
                all_ok = False
                first_failed_url = first_failed_url or url
                logging.warning("%s -> %s", url, e)

        if all_ok:
            failures = 0
        else:
            failures += 1
            logging.warning("Failures: %d/%d", failures, MAX_FAILURES)

        # 达到阈值 → 阶梯恢复
        if failures >= MAX_FAILURES and first_failed_url:
            service_name = SERVICE_MAP.get(first_failed_url, "health")

            # 阶梯 1: 重启服务
            logging.warning("Attempting restart of '%s' before rollback",
                            service_name)
            ok = restart_service(service_name)

            # 等待后再次检查
            time.sleep(5)
            try:
                resp = urllib.request.urlopen(first_failed_url, timeout=5)
                if resp.status == 200:
                    logging.info("Restart fixed '%s', no rollback needed",
                                 service_name)
                    failures = 0
                    time.sleep(CHECK_INTERVAL)
                    continue
            except Exception:
                pass

            # 阶梯 2: 回滚
            logging.warning("Restart failed, proceeding to rollback for %s",
                            first_failed_url)
            rollback(first_failed_url)
            msg = ("Rollback triggered for %s (service: %s) at tag %s" %
                   (first_failed_url, service_name, ROLLBACK_TAG))
            send_webhook(msg, "critical")

            failures = 0
            cooldown_until = time.time() + COOLDOWN_SECS
            logging.warning("Entering cooldown for %ds", COOLDOWN_SECS)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
