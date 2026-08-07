#!/usr/bin/env python3
"""
Subscription Plugin — 定时任务
================================
通过 APScheduler 注册定时任务:
  - 每天检查到期订阅
  - 到期前 3 天通知用户
  - 到期日自动续费扣款
"""

from datetime import datetime, timedelta

from .services import get_subscription_service


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
                        "UPDATE user_subscriptions SET status='suspended', updated_at=NOW() WHERE id=%s",
                        (sub.id,)
                    )
                    conn.commit()


def notify_expiring_soon():
    """到期前 3 天通知用户（站内信 / 预留）"""
    svc = get_subscription_service()
    warn_date = (datetime.now() + timedelta(days=3)).isoformat()

    with svc._get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM user_subscriptions WHERE status='active' AND auto_renew=1 AND period_end < %s",
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
            success, msg, _ = svc.renew(sub_data['user_id'], sub_data['item_key'])
            if not success:
                print(f'[Subscription/Job] Retry renew failed: user={sub_data["user_id"]}, item={sub_data["item_key"]}, msg={msg}')


def cleanup_old_orders():
    """清理 90 天前的过期订单"""
    svc = get_subscription_service()
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()

    with svc._get_conn() as conn:
        conn.execute(
            "UPDATE sub_orders SET status='expired', updated_at=NOW() WHERE status='pending' AND created_at < %s",
            (cutoff,)
        )
        conn.commit()


# ── 注册到 APScheduler ───────────────────────────────────────────────────

# M-04：按标准 §3.2 register_jobs() 配置格式定义
#   job_id / func / trigger / kwargs / priority / max_retries
SUBSCRIPTION_JOBS = [
    {
        'job_id': 'subscription_check_expired',
        'func': check_expired_subscriptions,
        'trigger': 'cron',
        'kwargs': {'hour': 2, 'minute': 0},
        'priority': 'normal',
        'max_retries': 2,
        'description': 'Daily check for expired subscriptions and auto-renew',
    },
    {
        'job_id': 'subscription_notify_expiring',
        'func': notify_expiring_soon,
        'trigger': 'cron',
        'kwargs': {'hour': 10, 'minute': 0},
        'priority': 'low',
        'max_retries': 2,
        'description': 'Daily notification for subscriptions expiring in 3 days',
    },
    {
        'job_id': 'subscription_cleanup_orders',
        'func': cleanup_old_orders,
        'trigger': 'cron',
        'kwargs': {'hour': 3, 'minute': 30},
        'priority': 'low',
        'max_retries': 2,
        'description': 'Cleanup pending orders older than 90 days',
    },
]
