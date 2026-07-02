#!/usr/bin/env python3
"""
续费提醒服务 — APScheduler 集成
到期前 7天/3天/1天 发站内信通知用户
扣款失败后即时通知

运行方式：
  1. 被 orchestrator APScheduler 调度：
     from services.renewal_reminder import run_reminder_scan
     scheduler.add_job(run_reminder_scan, 'cron', hour=8, minute=0)

  2. 手动测试：
     python services/renewal_reminder.py
"""
import os, sys, json, logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import get_db

logger = logging.getLogger('renewal_reminder')
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s'))
    logger.addHandler(ch)

REMINDER_DAYS = [7, 3, 1]  # 提前天数


def _insert_notification(conn, user_id, title, content):
    """写入站内通知"""
    try:
        conn.execute(
            "INSERT INTO notifications (user_id, title, content, type, is_read) VALUES (?,?,?,?,0)",
            (user_id, title, content, 'subscription'))
    except Exception:
        # notifications 表可能不存在，忽略
        pass


def _insert_sms_queue(conn, user_id, phone, content):
    """插入短信队列"""
    try:
        conn.execute(
            "INSERT INTO sms_queue (user_id, phone, content, status) VALUES (?,?,?,'pending')",
            (user_id, phone, content))
    except Exception:
        pass


def run_reminder_scan():
    """
    每日扫描：查找即将到期的订阅，发送续费提醒
    由 APScheduler 每天 8:00 调用
    """
    today = datetime.now().date()
    logger.info(f'[Reminder] Scan starting {today.isoformat()}')

    with get_db() as conn:
        for days_before in REMINDER_DAYS:
            target_date = today + timedelta(days=days_before)
            rows = conn.execute("""
                SELECT s.*, u.nickname, u.phone, u.display_name, up.name as plan_name
                FROM subscriptions s
                JOIN subscription_plans up ON up.plan_key = s.plan_key
                JOIN users u ON u.id = s.user_id
                WHERE s.status IN ('active', 'trialing')
                  AND s.auto_renew = 1
                  AND date(s.current_period_end) = date(?)
            """, (target_date.isoformat(),)).fetchall()

            for row in rows:
                _send_reminder(conn, dict(row), days_before)

        logger.info(f'[Reminder] Scan complete')


def _send_reminder(conn, sub, days_before):
    """发送单个续费提醒"""
    uid = sub['user_id']
    plan_name = sub.get('plan_name', sub['plan_key'])
    end_date = sub['current_period_end'][:10]
    nickname = sub.get('display_name') or sub.get('nickname') or '用户'
    phone = sub.get('phone', '')

    if days_before == 7:
        title = f'📬 {plan_name} 即将到期'
        content = f'{nickname}，您的 {plan_name} 将于 {end_date} 到期（剩余7天），届时将自动续费。如需取消，请登录用户中心操作。'
        sms = f'【VeroRon 维洛智能】您的{plan_name}将于{end_date}到期，届时自动续费。登录 verorun.com 查看详情。'
    elif days_before == 3:
        title = f'⚠️ {plan_name} 3天后到期'
        content = f'{nickname}，您的 {plan_name} 将于 {end_date} 到期（剩余3天），请确保账户余额充足。'
        sms = f'【VeroRon 维洛智能】您的{plan_name}将于3天后到期，到期自动续费。verorun.com/ucenter'
    elif days_before == 1:
        title = f'⚡ {plan_name} 明天到期'
        content = f'{nickname}，您的 {plan_name} 将于明天（{end_date}）到期，我们将自动为您续费。'
        sms = f'【易站智能】您的{plan_name}明天到期，到期自动续费。{deploy.url()}/ucenter'
    else:
        return

    _insert_notification(conn, uid, title, content)
    if phone:
        _insert_sms_queue(conn, uid, phone, sms)
    conn.commit()
    logger.info(f'  [{days_before}d] user={uid} plan={plan_name} end={end_date}')


def notify_payment_failed(user_id, plan_name, fail_reason):
    """扣款失败通知（由 renewal.py 调用）"""
    with get_db() as conn:
        user = conn.execute(
            'SELECT id, display_name, nickname, phone FROM users WHERE id=?',
            (user_id,)).fetchone()
        if not user:
            return
        user = dict(user)
        nickname = user.get('display_name') or user.get('nickname') or '用户'
        phone = user.get('phone', '')

        title = f'❌ {plan_name} 续费失败'
        content = f'{nickname}，您的 {plan_name} 自动续费扣款失败（{fail_reason}）。系统将在未来7天内重试。请确保账户余额充足或更换支付方式，以免服务中断。'
        sms = f'【易站智能】{plan_name}续费失败：{fail_reason}，7天内将重试。登录 {deploy.url()}/ucenter 处理。'

        _insert_notification(conn, user_id, title, content)
        if phone:
            _insert_sms_queue(conn, user_id, phone, sms)
        conn.commit()
        logger.info(f'  [dunning] user={user_id} plan={plan_name} fail={fail_reason}')


def notify_renewal_success(user_id, plan_name, amount_yuan, end_date):
    """续费成功通知"""
    with get_db() as conn:
        user = conn.execute(
            'SELECT id, display_name, nickname, phone FROM users WHERE id=?',
            (user_id,)).fetchone()
        if not user:
            return
        user = dict(user)
        nickname = user.get('display_name') or user.get('nickname') or '用户'

        title = f'✅ {plan_name} 续费成功'
        content = f'{nickname}，您的 {plan_name} 已成功续费 ¥{amount_yuan:.2f}，有效期至 {end_date}。'
        _insert_notification(conn, user_id, title, content)
        conn.commit()
        logger.info(f'  [success] user={user_id} plan={plan_name}')


def notify_downgraded_to_free(user_id, plan_name):
    """宽限期超期降级通知"""
    with get_db() as conn:
        user = conn.execute(
            'SELECT id, display_name, nickname, phone FROM users WHERE id=?',
            (user_id,)).fetchone()
        if not user:
            return
        user = dict(user)
        nickname = user.get('display_name') or user.get('nickname') or '用户'
        phone = user.get('phone', '')

        title = f'📉 {plan_name} 已过期，已降级至免费版'
        content = f'{nickname}，您的 {plan_name} 宽限期已过，已自动降级为免费套餐。如需恢复高级功能，请登录用户中心重新订阅。'
        sms = f'【VeroRon 维洛智能】{plan_name}已过期，已降级至免费版。登录 verorun.com 重新订阅恢复功能。'

        _insert_notification(conn, user_id, title, content)
        if phone:
            _insert_sms_queue(conn, user_id, phone, sms)
        conn.commit()
        logger.info(f'  [downgrade] user={user_id} plan={plan_name} downgraded to free')


# ============================================================
# 入口
# ============================================================

if __name__ == '__main__':
    run_reminder_scan()
    logger.info('[Reminder] Done')
