#!/usr/bin/env python3
"""
Plugin Manager — 订阅管理
===========================
管理插件订阅的创建、续费、取消、到期处理。

订阅类型:
  - monthly: 按月订阅，自动续费
  - yearly: 按年订阅，自动续费
"""

# ⚠️ DEPRECATED (auto-renew engine) — 本文件的自动续费调度入口已弃用。
# 主站自动续费链路当前由 auth-center/routes/subscription/renewal.py 承载
# （admin/app.py 每日调度 run_renewal_scan / run_dunning_scan）。
# 上线任务 T07/T11 要求：仅保留订阅 CRUD 能力，勿再启用 _auto_renew_task 引擎。

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


# 到期后未续费的宽限期（天）。宽限期内 License 保留 active，
# 超过宽限期未续费则由 run_grace_lock_scan() 锁定为 expired。
GRACE_DAYS = 7


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
        """手动续费（延长一个周期）

        续费成功后：
          - 清除待支付续费订单标记（防止 _ensure_renewal_order 幂等误判已支付订单仍待支付）
          - 记录 last_renewed_at
          - 仅对仍处于 active 的 License 延长有效期（避免覆盖其他状态）
        """
        sub = self.get_subscription(plugin_id)
        if not sub:
            return False

        if sub.status != SubscriptionStatus.ACTIVE:
            return False

        now = datetime.now()
        current_end = datetime.fromisoformat(sub.current_period_end) if sub.current_period_end else now
        new_start = max(now, current_end)
        new_end = self._calc_period_end(new_start, sub.interval_type)

        extra = dict(sub.extra or {})
        extra.pop('pending_renew_order', None)
        extra['last_renewed_at'] = now.isoformat()

        with get_registry_db() as conn:
            conn.execute("""
                UPDATE plugin_subscriptions SET
                    current_period_start=%s,
                    current_period_end=%s,
                    last_charge_at=NOW(),
                    retry_count=0,
                    extra=%s,
                    updated_at=NOW()
                WHERE id=%s
            """, (new_start.isoformat(), new_end.isoformat(),
                  json.dumps(extra, ensure_ascii=False), sub.id))
            # 同步续期 License（仅限 active，避免覆盖其他状态）
            conn.execute("""
                UPDATE plugin_licenses SET
                    expires_at=%s,
                    license_status='active',
                    updated_at=NOW()
                WHERE plugin_id=%s AND license_status='active'
            """, (new_end.isoformat(), plugin_id))
            conn.commit()
        return True

    def reactivate(self, plugin_id: str, interval_type: str = None,
                   amount_fen: int = None) -> bool:
        """补缴/重新购买后恢复订阅

        适用：订阅已 expired / suspended / canceled，用户完成支付后恢复。
        行为：
          - 订阅恢复 active + auto_renew=1，重新计算一个完整周期
          - 同步恢复 License 为 active 并刷新 expires_at
        """
        sub = self.get_subscription(plugin_id)
        if not sub:
            return False

        if interval_type:
            sub.interval_type = interval_type
        if amount_fen is not None:
            sub.amount_fen = amount_fen

        now = datetime.now()
        new_end = self._calc_period_end(now, sub.interval_type)

        extra = dict(sub.extra or {})
        extra.pop('pending_renew_order', None)
        extra.pop('grace_since', None)
        extra['last_renewed_at'] = now.isoformat()

        with get_registry_db() as conn:
            conn.execute("""
                UPDATE plugin_subscriptions SET
                    status='active',
                    auto_renew=1,
                    interval_type=%s,
                    amount_fen=%s,
                    current_period_start=%s,
                    current_period_end=%s,
                    last_charge_at=NOW(),
                    retry_count=0,
                    extra=%s,
                    updated_at=NOW()
                WHERE id=%s
            """, (sub.interval_type, sub.amount_fen,
                  now.isoformat(), new_end.isoformat(),
                  json.dumps(extra, ensure_ascii=False), sub.id))
            # 恢复 License（订阅恢复意味着用户已补缴，License 一并恢复）
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
        """检查并处理所有到期的订阅

        - auto_renew=0 → 立即标记 expired 并同步过期 License
        - auto_renew=1 → 进入宽限期（GRACE_DAYS 内 License 保留 active），
          并生成续费订单供支付；超过宽限期由 run_grace_lock_scan() 锁定。
        """
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
                    # 进入宽限期：生成续费订单（幂等，已生成则跳过）
                    try:
                        self._ensure_renewal_order(sub)
                    except Exception as e:
                        print(f'[PluginSub] renewal order failed for {sub.plugin_id}: {e}')
                    expired.append(sub)
                else:
                    # 不续费：标记过期
                    conn.execute(
                        "UPDATE plugin_subscriptions SET status='expired', updated_at=NOW() WHERE id=%s",
                        (sub.id,)
                    )
                    conn.execute(
                        "UPDATE plugin_licenses SET license_status='expired', updated_at=NOW() "
                        "WHERE plugin_id=%s AND license_status='active'",
                        (sub.plugin_id,)
                    )
                    conn.commit()
                    expired.append(sub)

        return expired

    def _ensure_renewal_order(self, sub: PluginSubscription) -> Optional[str]:
        """为到期自动续费订阅生成续费订单（幂等：已生成则跳过）"""
        extra = dict(sub.extra or {})
        if extra.get('pending_renew_order'):
            return extra['pending_renew_order']

        # 从原支付订单获取渠道与客户邮箱
        from .payment import get_payment_order, create_payment_order, get_payment_router, update_payment_order
        src = get_payment_order(sub.order_no)
        if not src:
            extra['renewal_error'] = 'source_order_missing'
            self._update_extra(sub.plugin_id, extra, sub.id)
            return None

        order = create_payment_order(
            plugin_id=sub.plugin_id,
            channel=src.channel or 'alipay',
            amount_fen=sub.amount_fen,
            subject=f'{sub.plugin_id} renewal ({sub.interval_type})',
            description='Plugin subscription renewal',
            customer_email=src.customer_email or '',
        )
        # 标记续费订单：支付回调据此识别（审计追踪），并关联到订阅
        try:
            update_payment_order(order.order_no, extra=json.dumps({
                'renewal': True,
                'subscription_id': sub.id,
            }, ensure_ascii=False))
        except Exception as e:
            print(f'[PluginSub] mark renewal order {order.order_no} failed: {e}')
        try:
            provider = get_payment_router().get_provider(order.channel)
            result = provider.create_order(order)
        except Exception as e:
            extra['renewal_error'] = f'gateway: {e}'
            self._update_extra(sub.plugin_id, extra, sub.id)
            return None
        if not result.success:
            extra['renewal_error'] = f'gateway: {result.error}'
            self._update_extra(sub.plugin_id, extra, sub.id)
            return None

        extra['pending_renew_order'] = order.order_no
        if not extra.get('grace_since'):
            extra['grace_since'] = datetime.now().isoformat()
        self._update_extra(sub.plugin_id, extra, sub.id)
        print(f'[PluginSub] renewal order {order.order_no} created for {sub.plugin_id}')
        return order.order_no

    def _update_extra(self, plugin_id: str, extra: dict, sub_id: int = None) -> None:
        with get_registry_db() as conn:
            if sub_id:
                conn.execute(
                    "UPDATE plugin_subscriptions SET extra=%s, updated_at=NOW() WHERE id=%s",
                    (json.dumps(extra, ensure_ascii=False), sub_id)
                )
            else:
                conn.execute(
                    "UPDATE plugin_subscriptions SET extra=%s, updated_at=NOW() WHERE plugin_id=%s",
                    (json.dumps(extra, ensure_ascii=False), plugin_id)
                )
            conn.commit()

    def run_grace_lock_scan(self) -> List[PluginSubscription]:
        """宽限期锁定：到期超过 GRACE_DAYS 仍未续费的自动续费订阅
        → 订阅 expired + License 过期"""
        locked = []
        with get_registry_db() as conn:
            rows = conn.execute(
                "SELECT * FROM plugin_subscriptions "
                "WHERE status='active' AND auto_renew=1 "
                "  AND current_period_end::timestamp < NOW() - (%s * INTERVAL '1 day')",
                (GRACE_DAYS,)
            ).fetchall()
            for row in rows:
                sub = PluginSubscription.from_row(dict(row))
                conn.execute(
                    "UPDATE plugin_subscriptions SET status='expired', auto_renew=0, updated_at=NOW() WHERE id=%s",
                    (sub.id,)
                )
                conn.execute(
                    "UPDATE plugin_licenses SET license_status='expired', updated_at=NOW() "
                    "WHERE plugin_id=%s AND license_status='active'",
                    (sub.plugin_id,)
                )
                conn.commit()
                locked.append(sub)
        if locked:
            print(f'[PluginSub] grace-locked {len(locked)} expired subscription(s)')
        return locked

    # ── 查询 ──────────────────────────────────────────────────────

    def get_subscription(self, plugin_id: str) -> Optional[PluginSubscription]:
        with get_registry_db() as conn:
            row = conn.execute(
                'SELECT * FROM plugin_subscriptions WHERE plugin_id=%s ORDER BY id DESC LIMIT 1',
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


# ── 定时任务包装（由 admin/app.py APScheduler 调度） ──────────────────

def run_plugin_sub_scan() -> None:
    """每日调度：插件订阅到期扫描（生成续费订单 / 标记过期）"""
    mgr = get_subscription_manager()
    expired = mgr.check_expired()
    if expired:
        print(f'[PluginSub] {len(expired)} subscription(s) past due')


def run_plugin_sub_grace_scan() -> None:
    """每日调度：插件订阅宽限期锁定（超期未续费 → License 过期）"""
    mgr = get_subscription_manager()
    locked = mgr.run_grace_lock_scan()
    if locked:
        print(f'[PluginSub] grace-locked {len(locked)} subscription(s)')
