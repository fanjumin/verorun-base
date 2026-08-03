#!/usr/bin/env python3
"""
Subscription — 自动续费引擎 + Dunning 失败重试
运行方式：cronjob / 手动调用
"""
import os, sys, json, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from models import get_db, DB_PATH


# Dunning 重试计划：失败后第1天 / 第3天 / 第7天
DUNNING_DAYS = [1, 3, 7]
GRACE_DAYS = 7  # 宽限期天数


def run_renewal_scan():
    """
    每日扫描：查找今天到期的订阅，执行自动续费
    """
    today = datetime.now().date()
    print(f'[renewal] Scan starting {today.isoformat()}')

    try:
        with get_db() as conn:
            # 查找今天到期的活跃订阅
            due = conn.execute("""
                SELECT s.*, u.nickname, u.phone, u.agent_id
                FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                WHERE s.auto_renew = 1
                  AND s.status = 'active'
                  AND date(s.current_period_end) = CURRENT_DATE
            """).fetchall()

            print(f'[renewal] {len(due)} subscription(s) due for renewal')

            for sub in due:
                sub = dict(sub)
                _process_renewal(conn, sub)
    except Exception as e:
        print(f'[renewal] DB error: {e}')
        return


def run_dunning_scan():
    """
    每日扫描 dunning：查找 past_due 状态需要重试的订阅
    """
    today = datetime.now().date()
    print(f'[dunning] Scan starting {today.isoformat()}')

    try:
        with get_db() as conn:
            # 查找 past_due 状态的订阅
            past_due = conn.execute("""
                SELECT s.*, u.nickname, u.phone, u.agent_id
                FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                WHERE s.status = 'past_due'
                  AND s.auto_renew = 1
                  AND date(s.current_period_end) >= CURRENT_DATE - (%s * INTERVAL '1 day')
            """, (GRACE_DAYS,)).fetchall()

            print(f'[dunning] {len(past_due)} past_due subscription(s) to check')

            for sub in past_due:
                sub = dict(sub)
                _retry_charge(conn, sub)

            # 超期宽限期的 → 降级为免费套餐
            # 先查询受影响的用户（含套餐名）
            expired_users = conn.execute("""
                SELECT s.user_id, u.nickname, u.display_name, u.phone, sp.name as plan_name
                FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                JOIN subscription_plans sp ON sp.plan_key = s.plan_key
                WHERE s.status='past_due'
                  AND date(s.current_period_end) < CURRENT_DATE - (%s * INTERVAL '1 day')
            """, (GRACE_DAYS,)).fetchall()

            if expired_users:
                expired_ids = [u['user_id'] for u in expired_users]
                placeholders = ','.join(['%s'] * len(expired_ids))
                print(f'[dunning] {len(expired_users)} user(s) downgraded to free after grace period')

                conn.execute(f"""
                    UPDATE subscriptions SET status='expired', plan_key='free', period='month', auto_renew=0, updated_at=NOW()
                    WHERE user_id IN ({placeholders})
                """, expired_ids)
                # 同步降级 app_authorizations 和 skill_keys
                conn.execute(f"""
                    UPDATE app_authorizations SET tier='free', tier_expire_at=NOW() + INTERVAL '365 days'
                    WHERE user_id IN ({placeholders}) AND app_name='trademind'
                """, expired_ids)
                conn.execute(f"""
                    UPDATE skill_keys SET tier='free'
                    WHERE user_id IN ({placeholders})
                """, expired_ids)
                conn.commit()

                # 发送降级通知
                for eu in expired_users:
                    eu = dict(eu)
                    try:
                        from services.renewal_reminder import notify_downgraded_to_free
                        notify_downgraded_to_free(eu['user_id'], eu['plan_name'])
                    except Exception as e:
                        print(f'[dunning] notify downgrade failed user={eu["user_id"]}: {e}')
    except Exception as e:
        print(f'[dunning] DB error: {e}')
        return


def _process_renewal(conn, sub):
    """处理单个订阅的续费"""
    uid = sub['user_id']
    plan_key = sub['plan_key']
    period = sub['period']
    payment_method = sub.get('payment_method', '')
    alipay_agreement = sub.get('alipay_agreement_id', '')
    wechat_contract = sub.get('wechat_contract_id', '')

    # 获取套餐价格
    plan = conn.execute('SELECT * FROM subscription_plans WHERE plan_key=%s', (plan_key,)).fetchone()
    if not plan:
        print(f'[renewal] ERROR: plan not found {plan_key} for user {uid}')
        return
    plan = dict(plan)

    amount_fen = plan['price_year'] if period == 'year' else plan['price_month']
    expire_days = 365 if period == 'year' else 30
    brand = os.environ.get("DEPLOY_BRAND", "")
    desc = f"{brand} {plan['name']}{'Annual Payment' if period=='year' else 'Monthly Payment'} Renewal"
    from . import new_order_no
    order_no = new_order_no('REN')

    # 创建续费订单
    conn.execute(
        'INSERT INTO subscription_orders (order_no, user_id, amount_fen, item_type, plan_key, period, payment_method, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
        (order_no, uid, amount_fen, 'renew', plan_key, period, payment_method, 'pending'))
    conn.commit()

    # 执行扣款
    success = False
    fail_reason = ''

    if payment_method == 'alipay' and alipay_agreement:
        from .gateway.alipay import execute_charge
        success, fail_reason = execute_charge(alipay_agreement, order_no, amount_fen, desc)
    elif payment_method == 'wechat' and wechat_contract:
        from .gateway.wechat import execute_contract_charge
        success, fail_reason = execute_contract_charge(wechat_contract, order_no, amount_fen, desc)

    if success:
        # 扣款成功
        from . import _fulfill_order
        _fulfill_order(order_no, payment_method)
        print(f'[renewal] OK user={uid} {plan_key}/{period} ¥{amount_fen/100:.2f}')
        # 发送续费成功通知
        try:
            from services.renewal_reminder import notify_renewal_success
            end_date = datetime.fromisoformat(sub['current_period_end']) + timedelta(days=expire_days)
            notify_renewal_success(uid, plan['name'], amount_fen/100, end_date.strftime('%Y-%m-%d'))
        except Exception as e:
            print(f'[renewal] notify success failed: {e}')
    else:
        # 扣款失败 → 进入 past_due
        _mark_past_due(conn, sub, order_no, fail_reason)
        print(f'[renewal] FAIL user={uid} {plan_key}/{period} reason={fail_reason}')
        # 发送扣款失败通知
        try:
            from services.renewal_reminder import notify_payment_failed
            notify_payment_failed(uid, plan['name'], fail_reason)
        except Exception as e:
            print(f'[renewal] notify failed: {e}')


def _retry_charge(conn, sub):
    """重试扣款"""
    uid = sub['user_id']
    plan_key = sub['plan_key']
    period = sub['period']
    payment_method = sub.get('payment_method', '')
    alipay_agreement = sub.get('alipay_agreement_id', '')
    wechat_contract = sub.get('wechat_contract_id', '')

    plan = conn.execute('SELECT * FROM subscription_plans WHERE plan_key=%s', (plan_key,)).fetchone()
    if not plan: return
    plan = dict(plan)

    amount_fen = plan['price_year'] if period == 'year' else plan['price_month']
    expire_days = 365 if period == 'year' else 30
    brand = os.environ.get("DEPLOY_BRAND", "")
    desc = f"{brand} {plan['name']} Renewal (Retry)"
    order_no = new_order_no('RET')
    conn.execute(
        'INSERT INTO subscription_orders (order_no, user_id, amount_fen, item_type, plan_key, period, payment_method, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
        (order_no, uid, amount_fen, 'renew', plan_key, period, payment_method, 'pending'))
    conn.commit()

    success = False
    fail_reason = ''

    if payment_method == 'alipay' and alipay_agreement:
        from .gateway.alipay import execute_charge
        success, fail_reason = execute_charge(alipay_agreement, order_no, amount_fen, desc)
    elif payment_method == 'wechat' and wechat_contract:
        from .gateway.wechat import execute_contract_charge
        success, fail_reason = execute_contract_charge(wechat_contract, order_no, amount_fen, desc)

    if success:
        from . import _fulfill_order
        _fulfill_order(order_no, payment_method)
        print(f'[dunning] RETRY OK user={uid} ¥{amount_fen/100:.2f}')
    else:
        conn.execute(
            "UPDATE subscription_orders SET status='failed', fail_reason=%s, updated_at=NOW() WHERE order_no=%s",
            (fail_reason, order_no))
        conn.commit()
        # 记录事件
        _log_payment_event(conn, uid, sub['id'], 'charge_fail', payment_method, amount_fen, fail_reason)
        print(f'[dunning] RETRY FAIL user={uid} reason={fail_reason}')


def _mark_past_due(conn, sub, order_no, fail_reason):
    """将订阅标记为 past_due"""
    conn.execute(
        "UPDATE subscription_orders SET status='failed', fail_reason=%s, updated_at=NOW() WHERE order_no=%s",
        (fail_reason, order_no))
    conn.execute(
        "UPDATE subscriptions SET status='past_due', updated_at=NOW() WHERE id=%s",
        (sub['id'],))
    conn.commit()

    _log_payment_event(conn, sub['user_id'], sub['id'], 'charge_fail',
                       sub.get('payment_method', ''), 0, fail_reason)
    _log_audit(conn, sub['user_id'], 'renewal_failed',
               f'Payment failed: {fail_reason}', sub_id=sub['id'])


def _log_payment_event(conn, user_id, sub_id, event_type, channel, amount_fen, fail_reason=''):
    conn.execute(
        'INSERT INTO payment_events (user_id, sub_id, event_type, channel, amount_fen, result, fail_reason) VALUES (%s,%s,%s,%s,%s,%s,%s)',
        (user_id, sub_id, event_type, channel, amount_fen, 'fail' if fail_reason else 'success', fail_reason))
    conn.commit()


def _log_audit(conn, user_id, action, detail, sub_id=None, admin_id=None):
    conn.execute(
        'INSERT INTO subscription_audit_log (user_id, sub_id, action, detail, admin_id) VALUES (%s,%s,%s,%s,%s)',
        (user_id, sub_id, action, detail, admin_id))
    conn.commit()


# ============================================================
# 入口
# ============================================================

if __name__ == '__main__(':
    # 直接运行：导入依赖后执行
    import secrets
    run_renewal_scan()
    run_dunning_scan()
    print(')[renewal] Done')
