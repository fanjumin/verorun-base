#!/usr/bin/env python3
"""
Plugin Manager — 订阅管理
===========================
管理插件订阅的创建、续费、取消、到期处理。

订阅类型:
  - monthly: 按月订阅，自动续费
  - yearly: 按年订阅，自动续费
"""

import json
import threading
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

from .models import get_registry_db


class SubscriptionStatus(str, Enum):
    ACTIVE = 'active'           # 生效中
    CANCELED = 'canceled'       # 已取消（到期不再续费）
    EXPIRED = 'expired'         # 已过期
    SUSPENDED = 'suspended'     # 暂停（扣款失败）


# ── DDL ───────────────────────────────────────────────────────────────

PLUGIN_SUBSCRIPTION_DDL = """
CREATE TABLE IF NOT EXISTS plugin_subscriptions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plugin_id       TEXT NOT NULL,
    license_key     TEXT NOT NULL,
    order_no        TEXT NOT NULL,
    interval_type   TEXT NOT NULL CHECK(interval_type IN ('month', 'year')),
    amount_fen      BIGINT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active','canceled','expired','suspended')),
    current_period_start TEXT,
    current_period_end   TEXT,
    auto_renew      BIGINT NOT NULL DEFAULT 1,
    retry_count     BIGINT NOT NULL DEFAULT 0,
    last_charge_at  TEXT,
    canceled_at     TEXT,
    created_at      TEXT DEFAULT NOW(),
    updated_at      TEXT DEFAULT NOW(),
    extra           TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_plugin_subs_plugin
    ON plugin_subscriptions(plugin_id);
CREATE INDEX IF NOT EXISTS idx_plugin_subs_status
    ON plugin_subscriptions(status);
"""


def init_subscription_tables():
    with get_registry_db() as conn:
        conn.executescript(PLUGIN_SUBSCRIPTION_DDL)
        conn.commit()


@dataclass
class PluginSubscription:
    plugin_id: str
    license_key: str
    order_no: str
    interval_type: str          # 'month' | 'year'
    amount_fen: int
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    auto_renew: bool = True
    retry_count: int = 0
    last_charge_at: Optional[str] = None
    canceled_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d

    @classmethod
    def from_row(cls, row: dict) -> 'PluginSubscription':
        return cls(
            id=row['id'],
            plugin_id=row['plugin_id'],
            license_key=row['license_key'],
            order_no=row['order_no'],
            interval_type=row['interval_type'],
            amount_fen=row['amount_fen'],
            status=SubscriptionStatus(row['status']),
            current_period_start=row.get('current_period_start'),
            current_period_end=row.get('current_period_end'),
            auto_renew=bool(row.get('auto_renew', 1)),
            retry_count=row.get('retry_count', 0),
            last_charge_at=row.get('last_charge_at'),
            canceled_at=row.get('canceled_at'),
            extra=json.loads(row.get('extra', '{}')),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )


class SubscriptionManager:
    """订阅管理器"""

    def __init__(self):
        self._lock = threading.Lock()
        init_subscription_tables()

    # ── 创建订阅 ──────────────────────────────────────────────────

    def create(self, plugin_id: str, license_key: str, order_no: str,
               interval_type: str, amount_fen: int) -> PluginSubscription:
        """购买成功后创建订阅记录"""
        now = datetime.now()
        period_end = self._calc_period_end(now, interval_type)

        sub = PluginSubscription(
            plugin_id=plugin_id,
            license_key=license_key,
            order_no=order_no,
            interval_type=interval_type,
            amount_fen=amount_fen,
            current_period_start=now.isoformat(),
            current_period_end=period_end.isoformat(),
        )

        with get_registry_db() as conn:
            cur = conn.execute("""
                INSERT INTO plugin_subscriptions
                    (plugin_id, license_key, order_no, interval_type,
                     amount_fen, current_period_start, current_period_end,
                     auto_renew, extra)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                sub.plugin_id, sub.license_key, sub.order_no,
                sub.interval_type, sub.amount_fen,
                sub.current_period_start, sub.current_period_end,
                int(sub.auto_renew), json.dumps(sub.extra),
            ))
            conn.commit()
            sub.id = cur.fetchone()['id']

        return sub

    # ── 取消订阅 ──────────────────────────────────────────────────

    def cancel(self, plugin_id: str, immediate: bool = False) -> bool:
        """取消订阅

        Args:
            plugin_id: 插件标识
            immediate: 是否立即取消（否则到期不再续费）

        Returns:
            bool: 是否成功
        """
        sub = self.get_subscription(plugin_id)
        if not sub:
            return False

        with self._lock:
            with get_registry_db() as conn:
                if immediate:
                    conn.execute("""
                        UPDATE plugin_subscriptions SET
                            status='expired', auto_renew=0,
                            canceled_at=NOW(),
                            updated_at=NOW()
                        WHERE plugin_id=%s
                    """, (plugin_id,))
                    # 同步标记 License 已过期
                    conn.execute("""
                        UPDATE plugin_licenses SET
                            license_status='expired',
                            updated_at=NOW()
                        WHERE plugin_id=%s
                    """, (plugin_id,))
                else:
                    conn.execute("""
                        UPDATE plugin_subscriptions SET
                            auto_renew=0, canceled_at=NOW(),
                            updated_at=NOW()
                        WHERE plugin_id=%s
                    """, (plugin_id,))
                conn.commit()
        return True

    # ── 续费处理 ──────────────────────────────────────────────────

    def renew(self, plugin_id: str) -> bool:
        """手动续费（延长一个周期）"""
        sub = self.get_subscription(plugin_id)
        if not sub:
            return False

        if sub.status != SubscriptionStatus.ACTIVE:
            return False

        now = datetime.now()
        current_end = datetime.fromisoformat(sub.current_period_end) if sub.current_period_end else now
        new_start = max(now, current_end)
        new_end = self._calc_period_end(new_start, sub.interval_type)

        with get_registry_db() as conn:
            conn.execute("""
                UPDATE plugin_subscriptions SET
                    current_period_start=%s,
                    current_period_end=%s,
                    last_charge_at=NOW(),
                    retry_count=0,
                    updated_at=NOW()
                WHERE plugin_id=%s
            """, (new_start.isoformat(), new_end.isoformat(), plugin_id))
            # 同步续期 License
            conn.execute("""
                UPDATE plugin_licenses SET
                    expires_at=%s,
                    license_status='active',
                    updated_at=NOW()
                WHERE plugin_id=%s
            """, (new_end.isoformat(), plugin_id))
            conn.commit()
        return True

    # ── 到期检查 ──────────────────────────────────────────────────

    def check_expired(self) -> List[PluginSubscription]:
        """检查并标记所有到期的订阅"""
        now = datetime.now().isoformat()
        expired = []

        with get_registry_db() as conn:
            rows = conn.execute(
                "SELECT * FROM plugin_subscriptions WHERE status='active' AND current_period_end < %s",
                (now,)
            ).fetchall()
            for row in rows:
                sub = PluginSubscription.from_row(dict(row))
                if sub.auto_renew:
                    # 自动续费：尝试扣款（此处仅标记，实际扣款由 scheduler 驱动）
                    expired.append(sub)
                else:
                    # 不续费：标记过期
                    conn.execute(
                        "UPDATE plugin_subscriptions SET status='expired', updated_at=NOW() WHERE id=%s",
                        (sub.id,)
                    )
                    conn.execute(
                        "UPDATE plugin_licenses SET license_status='expired', updated_at=NOW() WHERE plugin_id=%s",
                        (sub.plugin_id,)
                    )
                    conn.commit()
                    expired.append(sub)

        return expired

    # ── 查询 ──────────────────────────────────────────────────────

    def get_subscription(self, plugin_id: str) -> Optional[PluginSubscription]:
        with get_registry_db() as conn:
            row = conn.execute(
                'SELECT * FROM plugin_subscriptions WHERE plugin_id=%s',
                (plugin_id,)
            ).fetchone()
            if row:
                return PluginSubscription.from_row(dict(row))
        return None

    def list_subscriptions(self) -> List[PluginSubscription]:
        with get_registry_db() as conn:
            rows = conn.execute(
                'SELECT * FROM plugin_subscriptions ORDER BY created_at DESC'
            ).fetchall()
            return [PluginSubscription.from_row(dict(r)) for r in rows]

    # ── 内部工具 ──────────────────────────────────────────────────

    def _calc_period_end(self, start: datetime, interval: str) -> datetime:
        if interval == 'month':
            # 加一个月（考虑闰月）
            month = start.month + 1
            year = start.year
            if month > 12:
                month -= 12
                year += 1
            try:
                return start.replace(year=year, month=month)
            except ValueError:
                # 月末截断
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                return start.replace(year=year, month=month, day=last_day)
        elif interval == 'year':
            try:
                return start.replace(year=start.year + 1)
            except ValueError:
                return start.replace(year=start.year + 1, month=2, day=28)
        return start + timedelta(days=30)


# ── 自动续费调度器 ──────────────────────────────────────────────────

_AUTO_RENEW_LOCK = threading.Lock()


def _auto_renew_task(app=None):
    """自动续费检查任务：到期前 3 天内的订阅发起扣款"""
    try:
        mgr = _get_sub_manager_for_scheduler()
        subs = mgr.check_expired()
        for sub in subs:
            if sub.auto_renew and sub.retry_count < 3:
                print(f'[AutoRenew] Attempting renew for {sub.plugin_id} (retry #{sub.retry_count})')
                # 通过原始支付渠道重新下单扣款
                try:
                    from .payment import get_payment_router, create_payment_order, update_payment_order, get_payment_order
                    router = get_payment_router()
                    provider = router.get_provider_for_plugin(sub.plugin_id)

                    order = create_payment_order(
                        plugin_id=sub.plugin_id,
                        channel='auto_renew',
                        amount_fen=sub.amount_fen,
                        subject=f'Plugin subscription renewal - {sub.plugin_id}',
                        description='Auto renew',
                    )

                    result = provider.create_order(order)
                    if result.success:
                        # 模拟：标记为已支付（实际应等回调）
                        update_payment_order(order.order_no, status='paid',
                                             paid_at=datetime.now().isoformat())
                        mgr.renew(sub.plugin_id)
                        print(f'[AutoRenew] ✅ Renewed {sub.plugin_id}')
                    else:
                        conn = get_registry_db().__enter__()
                        conn.execute(
                            'UPDATE plugin_subscriptions SET retry_count=retry_count+1, updated_at=NOW() WHERE id=%s',
                            (sub.id,)
                        )
                        conn.commit()
                        conn.__exit__(None, None, None)
                        print(f'[AutoRenew] ❌ Renewal failed for {sub.plugin_id}: {result.error}')
                except Exception as e:
                    print(f'[AutoRenew] ❌ Error renewing {sub.plugin_id}: {e}')
    except Exception as e:
        print(f'[AutoRenew] Task error: {e}')


def _get_sub_manager_for_scheduler():
    """获取 SubscriptionManager 实例（用于调度器）"""
    global _SUB_MGR
    if _SUB_MGR is None:
        with _SUB_MGR_LOCK:
            if _SUB_MGR is None:
                _SUB_MGR = SubscriptionManager()
    return _SUB_MGR


def start_auto_renew_scheduler(app):
    """注册 APScheduler 每天检查即将到期的订阅

    在 Flask app 初始化时调用。
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=_auto_renew_task,
            trigger='interval',
            days=1,
            id='plugin_sub_auto_renew',
            name='Plugin Subscription Auto Renewal',
            replace_existing=True,
        )
        scheduler.start()
        print('[PluginManager] ✅ Auto-renew scheduler started (daily check)')
    except ImportError:
        print('[PluginManager] ⚠️ APScheduler not installed. Auto-renew disabled.')
    except Exception as e:
        print(f'[PluginManager] ⚠️ Failed to start auto-renew scheduler: {e}')


# ── 模块级单例 ──────────────────────────────────────────────────────

_SUB_MGR = None
_SUB_MGR_LOCK = threading.Lock()


def get_subscription_manager() -> SubscriptionManager:
    global _SUB_MGR
    if _SUB_MGR is None:
        with _SUB_MGR_LOCK:
            if _SUB_MGR is None:
                _SUB_MGR = SubscriptionManager()
    return _SUB_MGR
