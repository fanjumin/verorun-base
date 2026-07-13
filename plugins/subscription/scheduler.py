#!/usr/bin/env python3
"""
Subscription Plugin — 定时任务
================================
通过 APScheduler 注册定时任务:
  - 每天检查到期订阅
  - 到期前 3 天通知用户
  - 到期日自动续费扣款
"""

import os
from datetime import datetime, timedelta

from .services import get_subscription_service, has_subscription
from .models import SubStatus


SUBSCRIPTION_JOBS = []


def _get_locale():
    return 'zh-CN' if os.environ.get('DEPLOY_MARKET', 'cn') == 'cn' else 'en'


def check_expired_subscriptions():
    """每天检查到期订阅"""
    svc = get_subscription_service()
    expired = svc.check_expired()

    if not expired:
        return

    print(f'[Subscription/Job] Found {len(expired)} expired subscriptions')

    for sub in expired:
        if sub.auto_renew:
            # 尝试自动续费
            success, msg, order_data = svc.renew(sub.user_id, sub.item_key)
            if success:
                print(f'[Subscription/Job] Auto-renewed: user={sub.user_id}, item={sub.item_key}')
            else:
                print(f'[Subscription/Job] Auto-renew failed: user={sub.user_id}, item={sub.item_key}, msg={msg}')
                # 3 天后重试，暂时标记 suspended
                with svc._get_conn() as conn:
                    conn.execute(
                        "UPDATE user_subscriptions SET status='suspended', updated_at=datetime('now') WHERE id=?",
                        (sub.id,)
                    )
                    conn.commit()


def notify_expiring_soon():
    """到期前 3 天通知用户（站内信 / 预留）"""
    svc = get_subscription_service()
    warn_date = (datetime.now() + timedelta(days=3)).isoformat()

    with svc._get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM user_subscriptions WHERE status='active' AND auto_renew=1 AND period_end < ?",
            (warn_date,)
        ).fetchall()

        if rows:
            print(f'[Subscription/Job] {len(rows)} subscriptions expiring within 3 days')
            # TODO: 对接邮件/站内信通知系统
            for row in rows:
                pass  # placeholder for notification logic

    # 也处理 suspended 状态的重试
    with svc._get_conn() as conn:
        suspended = conn.execute(
            "SELECT * FROM user_subscriptions WHERE status='suspended'"
        ).fetchall()

        for row in suspended:
            sub_data = dict(row)
            # 重试：创建新订单
            svc.renew(sub_data['user_id'], sub_data['item_key'])


def cleanup_old_orders():
    """清理 90 天前的过期订单"""
    svc = get_subscription_service()
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()

    with svc._get_conn() as conn:
        conn.execute(
            "UPDATE sub_orders SET status='expired', updated_at=datetime('now') WHERE status='pending' AND created_at < ?",
            (cutoff,)
        )
        conn.commit()


# ── 注册到 APScheduler ───────────────────────────────────────────────────

SUBSCRIPTION_JOBS = [
    {
        'name': 'subscription_check_expired',
        'func': check_expired_subscriptions,
        'trigger': 'cron',
        'hour': 2,
        'minute': 0,
        'description': 'Daily check for expired subscriptions and auto-renew',
    },
    {
        'name': 'subscription_notify_expiring',
        'func': notify_expiring_soon,
        'trigger': 'cron',
        'hour': 10,
        'minute': 0,
        'description': 'Daily notification for subscriptions expiring in 3 days',
    },
    {
        'name': 'subscription_cleanup_orders',
        'func': cleanup_old_orders,
        'trigger': 'cron',
        'hour': 3,
        'minute': 30,
        'description': 'Cleanup pending orders older than 90 days',
    },
]


def seed_subscription_schedules():
    """将定时任务写入 orchestrator 的 cron_jobs 表

    使用 INSERT OR IGNORE，不覆盖已有同名任务。
    """
    try:
        import sqlite3

        # orchestrator 数据库路径（与 orchestrator/models.py 一致）
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data'
        )
        orch_db = os.environ.get('DB_PATH', os.path.join(data_dir, 'x7k2m9a4.db'))

        if not os.path.exists(orch_db):
            print(f'[Subscription/Scheduler] Orchestrator DB not found: {orch_db}, skipping')
            return

        conn = sqlite3.connect(orch_db)
        conn.execute("PRAGMA journal_mode=WAL")

        # 确保 cron_jobs 表存在
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cron_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                func TEXT,
                trigger TEXT DEFAULT 'cron',
                hour INTEGER DEFAULT 0,
                minute INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        for job in SUBSCRIPTION_JOBS:
            conn.execute("""
                INSERT OR IGNORE INTO cron_jobs (name, func, trigger, hour, minute, description, enabled)
                VALUES (?,?,?,?,?,?,1)
            """, (
                job['name'],
                f"plugins.subscription.scheduler.{job['func'].__name__}",
                job.get('trigger', 'cron'),
                job.get('hour', 0),
                job.get('minute', 0),
                job.get('description', ''),
            ))

        conn.commit()
        conn.close()
        print(f'[Subscription/Scheduler] {len(SUBSCRIPTION_JOBS)} jobs seeded to orchestrator')

    except Exception as e:
        print(f'[Subscription/Scheduler] Error seeding schedules: {e}')
