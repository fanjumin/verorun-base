#!/usr/bin/env python3
"""
Subscription Plugin — 核心业务层
==================================
SubscriptionService: 订阅/取消/续费/查询/权限检查
支付路由: 根据 DEPLOY_MARKET 自动选择支付渠道
"""

import os
import json
import psycopg2
import secrets
import time
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from functools import wraps

from .models import (
    get_db, get_db_path,
    SubItem, UserSubscription, SubOrder,
    SubStatus, OrderStatus, IntervalType,
    init_tables, seed_default_items,
)

# ── i18n 注入 ───────────────────────────────────────────────────────────

_t = lambda text, **kwargs: text  # 默认回退


def init_i18n(t_func):
    """由 __init__.py 在 on_enable 时调用注入翻译函数"""
    global _t
    _t = t_func


# ── 支付渠道路由（双环境） ──────────────────────────────────────────────

def get_market() -> str:
    """返回当前市场: 'cn' | 'intl'"""
    return os.environ.get('DEPLOY_MARKET', 'cn')


def get_default_payment_channel() -> str:
    """根据 DEPLOY_MARKET 返回默认支付渠道"""
    return 'stripe' if get_market() == 'intl' else 'alipay'


def get_available_channels() -> List[str]:
    """返回当前市场可用的支付渠道列表"""
    if get_market() == 'intl':
        return ['stripe', 'paypal']
    return ['alipay', 'wechat']


# ── 订阅服务 ────────────────────────────────────────────────────────────

class SubscriptionService:
    """订阅管理核心服务"""

    def __init__(self):
        self._db_path = get_db_path()

    def _get_conn(self):
        conn = psycopg2.connect(
            host=os.environ.get('PG_HOST', 'localhost'),
            port=int(os.environ.get('PG_PORT', 5432)),
            dbname=os.environ.get('PG_DB', 'verorun'),
            user=os.environ.get('PG_USER', 'verorun'),
            password=os.environ.get('PG_PASSWORD', ''),
        )
        conn.autocommit = False
        conn.execute("CREATE SCHEMA IF NOT EXISTS subscription")
        conn.execute("SET search_path TO subscription")
        return conn

    # ── SKU 目录查询 ───────────────────────────────────────────────

    def list_items(self, locale: str = 'zh-CN', active_only: bool = True) -> List[Dict]:
        """获取所有可订阅项"""
        with self._get_conn() as conn:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM sub_items WHERE is_active=1 ORDER BY sort_order"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sub_items ORDER BY sort_order"
                ).fetchall()
            return [SubItem.from_row(dict(r)).to_dict(locale) for r in rows]

    def get_item(self, item_key: str) -> Optional[SubItem]:
        """获取单个 SKU"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sub_items WHERE item_key=%s", (item_key,)
            ).fetchone()
            if row:
                return SubItem.from_row(dict(row))
        return None

    def upsert_item(self, item_data: Dict) -> bool:
        """管理后台：创建或更新 SKU"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO sub_items
                    (item_key, category, name_zh, name_en, description_zh, description_en,
                     price_month, price_year, is_active, auto_activate, sort_order, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                ON CONFLICT(item_key) DO UPDATE SET
                    category=excluded.category,
                    name_zh=excluded.name_zh,
                    name_en=excluded.name_en,
                    description_zh=excluded.description_zh,
                    description_en=excluded.description_en,
                    price_month=excluded.price_month,
                    price_year=excluded.price_year,
                    is_active=excluded.is_active,
                    auto_activate=excluded.auto_activate,
                    sort_order=excluded.sort_order,
                    updated_at=NOW()
            """, (
                item_data['item_key'],
                item_data.get('category', 'plugin'),
                item_data.get('name_zh', ''),
                item_data.get('name_en', ''),
                item_data.get('description_zh', ''),
                item_data.get('description_en', ''),
                item_data.get('price_month', 0),
                item_data.get('price_year', 0),
                int(item_data.get('is_active', 1)),
                item_data.get('auto_activate', ''),
                item_data.get('sort_order', 0),
            ))
            conn.commit()
        return True

    # ── 用户订阅查询 ───────────────────────────────────────────────

    def get_user_subscriptions(self, user_id: int) -> List[UserSubscription]:
        """获取用户所有订阅"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM user_subscriptions WHERE user_id=%s ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            return [UserSubscription.from_row(dict(r)) for r in rows]

    def get_user_subscription(self, user_id: int, item_key: str) -> Optional[UserSubscription]:
        """获取用户某个订阅"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM user_subscriptions WHERE user_id=%s AND item_key=%s",
                (user_id, item_key)
            ).fetchone()
            if row:
                return UserSubscription.from_row(dict(row))
        return None

    def has_subscription(self, user_id: int, item_key: str) -> bool:
        """检查用户是否有某个有效订阅（含自动开通）"""
        # 先查直接订阅
        sub = self.get_user_subscription(user_id, item_key)
        if sub and sub.status == SubStatus.ACTIVE:
            return True

        # 再查 base 自动开通的项
        base_sub = self.get_user_subscription(user_id, 'base')
        if base_sub and base_sub.status == SubStatus.ACTIVE:
            base_item = self.get_item('base')
            if base_item and base_item.auto_activate:
                auto_items = [x.strip() for x in base_item.auto_activate.split(',') if x.strip()]
                if item_key in auto_items:
                    return True

        return False

    def get_active_features(self, user_id: int) -> List[str]:
        """获取用户当前所有活跃的 feature key 列表"""
        subs = self.get_user_subscriptions(user_id)
        active = [s.item_key for s in subs if s.status == SubStatus.ACTIVE]

        # base 自动开通的项
        if 'base' in active:
            base_item = self.get_item('base')
            if base_item and base_item.auto_activate:
                auto_items = [x.strip() for x in base_item.auto_activate.split(',') if x.strip()]
                for ai in auto_items:
                    if ai not in active:
                        active.append(ai)

        return active

    # ── 创建订阅 ──────────────────────────────────────────────────

    def subscribe(self, user_id: int, item_key: str, interval_type: str,
                  channel: str = None) -> Tuple[bool, str, Optional[dict]]:
        """创建订阅订单，返回 (success, message, order_data)

        订单创建后返回支付信息，支付成功后才正式创建 user_subscriptions 记录。
        """
        # 检查 SKU 是否存在且活跃
        item = self.get_item(item_key)
        if not item:
            return False, _t('Subscription item not found'), None
        if not item.is_active:
            return False, _t('Subscription item is not available'), None

        # 检查是否已订阅
        existing = self.get_user_subscription(user_id, item_key)
        if existing and existing.status == SubStatus.ACTIVE:
            return False, _t('Already subscribed'), None

        # 计算价格
        if interval_type not in ('month', 'year'):
            return False, _t('Invalid interval type'), None

        amount_fen = item.price_month if interval_type == 'month' else item.price_year
        if amount_fen <= 0:
            return False, _t('Invalid price'), None

        # 选择支付渠道
        if channel is None:
            channel = get_default_payment_channel()

        # 创建订单
        order_no = f'SUB{int(time.time())}{secrets.token_hex(4).upper()}'
        now = datetime.now()

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO sub_orders
                    (order_no, user_id, item_key, interval_type, amount_fen, channel, status, extra)
                VALUES (%s,%s,%s,%s,%s,%s,'pending','{}')
            """, (order_no, user_id, item_key, interval_type, amount_fen, channel))
            conn.commit()

        # 调用支付网关创建支付
        from .gateways import create_payment
        pay_result = create_payment(
            order_no=order_no,
            amount_fen=amount_fen,
            subject=item.name_zh,
            description=item.description_zh,
            channel=channel,
            interval_type=interval_type,
        )

        # 更新订单支付信息
        with self._get_conn() as conn:
            if pay_result.get('qr_code') or pay_result.get('redirect_url'):
                conn.execute("""
                    UPDATE sub_orders SET
                        qr_code=%s, redirect_url=%s, trade_no=%s, updated_at=NOW()
                    WHERE order_no=%s
                """, (
                    pay_result.get('qr_code', ''),
                    pay_result.get('redirect_url', ''),
                    pay_result.get('trade_no', ''),
                    order_no,
                ))
                conn.commit()

        order_data = {
            'order_no': order_no,
            'amount_fen': amount_fen,
            'amount_yuan': f'{amount_fen / 100:.2f}',
            'channel': channel,
            'qr_code': pay_result.get('qr_code', ''),
            'redirect_url': pay_result.get('redirect_url', ''),
            'interval_type': interval_type,
            'item_name': item.name_zh if get_market() == 'cn' else item.name_en,
        }

        return True, 'ok', order_data

    # ── 支付成功回调 ──────────────────────────────────────────────

    def on_payment_success(self, order_no: str, trade_no: str = '') -> Tuple[bool, str]:
        """支付成功后：标记订单 + 创建/续费用户订阅"""
        with self._get_conn() as conn:
            order_row = conn.execute(
                "SELECT * FROM sub_orders WHERE order_no=%s AND status='pending'",
                (order_no,)
            ).fetchone()

            if not order_row:
                return False, 'Order not found or already processed'

            order = SubOrder.from_row(dict(order_row))

            # 更新订单状态
            conn.execute("""
                UPDATE sub_orders SET
                    status='paid', trade_no=%s, paid_at=NOW(), updated_at=NOW()
                WHERE order_no=%s
            """, (trade_no, order_no))

            # 创建或续费订阅
            now = datetime.now()
            interval = order.interval_type
            period_end = self._calc_period_end(now, interval)

            existing = conn.execute(
                "SELECT * FROM user_subscriptions WHERE user_id=%s AND item_key=%s",
                (order.user_id, order.item_key)
            ).fetchone()

            if existing:
                ex = UserSubscription.from_row(dict(existing))
                if ex.status in (SubStatus.EXPIRED, SubStatus.CANCELED):
                    # 重新激活
                    conn.execute("""
                        UPDATE user_subscriptions SET
                            status='active', interval_type=%s, amount_fen=%s,
                            period_start=%s, period_end=%s, auto_renew=1,
                            order_no=%s, updated_at=NOW()
                        WHERE user_id=%s AND item_key=%s
                    """, (interval, order.amount_fen, now.isoformat(), period_end.isoformat(),
                          order_no, order.user_id, order.item_key))
                else:
                    # 续费：延长 period_end
                    conn.execute("""
                        UPDATE user_subscriptions SET
                            status='active', interval_type=%s, amount_fen=%s,
                            period_start=%s, period_end=%s, auto_renew=1,
                            order_no=%s, updated_at=NOW()
                        WHERE user_id=%s AND item_key=%s
                    """, (interval, order.amount_fen, now.isoformat(), period_end.isoformat(),
                          order_no, order.user_id, order.item_key))
            else:
                conn.execute("""
                    INSERT INTO user_subscriptions
                        (user_id, item_key, interval_type, amount_fen, period_start, period_end,
                         auto_renew, order_no)
                    VALUES (%s,%s,%s,%s,%s,%s,1,%s)
                """, (order.user_id, order.item_key, interval, order.amount_fen,
                      now.isoformat(), period_end.isoformat(), order_no))

            # 处理 auto_activate：订阅 base 时自动开通关联项
            if order.item_key == 'base':
                base_item = self.get_item('base')
                if base_item and base_item.auto_activate:
                    auto_items = [x.strip() for x in base_item.auto_activate.split(',') if x.strip()]
                    for ai in auto_items:
                        ai_existing = conn.execute(
                            "SELECT * FROM user_subscriptions WHERE user_id=%s AND item_key=%s",
                            (order.user_id, ai)
                        ).fetchone()
                        if not ai_existing:
                            conn.execute("""
                                INSERT INTO user_subscriptions
                                    (user_id, item_key, interval_type, amount_fen, period_start,
                                     period_end, auto_renew, order_no, status)
                                VALUES (%s,%s,'month',0,%s,%s,0,%s,'active')
                            """, (order.user_id, ai, now.isoformat(), period_end.isoformat(), order_no))

            conn.commit()

        return True, 'ok'

    # ── 取消订阅 ──────────────────────────────────────────────────

    def cancel(self, user_id: int, item_key: str, immediate: bool = False) -> Tuple[bool, str]:
        """取消订阅

        Args:
            immediate: True=立即过期, False=到期不续
        """
        sub = self.get_user_subscription(user_id, item_key)
        if not sub:
            return False, _t('Subscription not found')

        # 不允许取消 base 自动开通的子项
        if item_key != 'base':
            base_item = self.get_item('base')
            if base_item and base_item.auto_activate:
                auto_items = [x.strip() for x in base_item.auto_activate.split(',') if x.strip()]
                if item_key in auto_items:
                    return False, _t('This item is included in your Base subscription and cannot be canceled separately')

        with self._get_conn() as conn:
            if immediate:
                conn.execute("""
                    UPDATE user_subscriptions SET
                        status='canceled', auto_renew=0, updated_at=NOW()
                    WHERE user_id=%s AND item_key=%s
                """, (user_id, item_key))
            else:
                conn.execute("""
                    UPDATE user_subscriptions SET
                        auto_renew=0, updated_at=NOW()
                    WHERE user_id=%s AND item_key=%s
                """, (user_id, item_key))
            conn.commit()

        return True, 'ok'

    # ── 续费 ──────────────────────────────────────────────────────

    def renew(self, user_id: int, item_key: str, channel: str = None) -> Tuple[bool, str, Optional[dict]]:
        """手动续费：创建续费订单"""
        sub = self.get_user_subscription(user_id, item_key)
        if not sub:
            return False, _t('Subscription not found'), None

        item = self.get_item(item_key)
        if not item:
            return False, _t('Subscription item not found'), None

        interval = sub.interval_type
        amount_fen = item.price_month if interval == 'month' else item.price_year

        if channel is None:
            channel = get_default_payment_channel()

        order_no = f'SUB{int(time.time())}{secrets.token_hex(4).upper()}'

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO sub_orders
                    (order_no, user_id, item_key, interval_type, amount_fen, channel, status, extra)
                VALUES (%s,%s,%s,%s,%s,%s,'pending','{}')
            """, (order_no, user_id, item_key, interval, amount_fen, channel))
            conn.commit()

        from .gateways import create_payment
        pay_result = create_payment(
            order_no=order_no,
            amount_fen=amount_fen,
            subject=f"{item.name_zh} - {_t('Renewal')}",
            description=item.description_zh,
            channel=channel,
            interval_type=interval,
        )

        order_data = {
            'order_no': order_no,
            'amount_fen': amount_fen,
            'amount_yuan': f'{amount_fen / 100:.2f}',
            'channel': channel,
            'qr_code': pay_result.get('qr_code', ''),
            'redirect_url': pay_result.get('redirect_url', ''),
            'interval_type': interval,
        }
        return True, 'ok', order_data

    # ── 到期检查 ──────────────────────────────────────────────────

    def check_expired(self) -> List[UserSubscription]:
        """检查并处理到期订阅"""
        now = datetime.now().isoformat()
        expired = []

        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM user_subscriptions WHERE status='active' AND period_end < %s",
                (now,)
            ).fetchall()

            for row in rows:
                sub = UserSubscription.from_row(dict(row))
                if sub.auto_renew:
                    # 标记待自动续费（由 scheduler 处理）
                    expired.append(sub)
                else:
                    conn.execute(
                        "UPDATE user_subscriptions SET status='expired', updated_at=NOW() WHERE id=%s",
                        (sub.id,)
                    )
                    conn.commit()
                    sub.status = SubStatus.EXPIRED
                    expired.append(sub)

        return expired

    # ── 订单查询 ──────────────────────────────────────────────────

    def get_order(self, order_no: str) -> Optional[SubOrder]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sub_orders WHERE order_no=%s", (order_no,)
            ).fetchone()
            if row:
                return SubOrder.from_row(dict(row))
        return None

    def list_orders(self, user_id: int, limit: int = 50) -> List[SubOrder]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sub_orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            return [SubOrder.from_row(dict(r)) for r in rows]

    def list_all_orders(self, limit: int = 100, offset: int = 0) -> List[SubOrder]:
        """管理员：全部订单"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sub_orders ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset)
            ).fetchall()
            return [SubOrder.from_row(dict(r)) for r in rows]

    # ── 退款 ──────────────────────────────────────────────────────

    def refund_order(self, order_no: str) -> Tuple[bool, str]:
        """管理员：退款订单
        1. 查订单确认状态为 paid
        2. 调用支付网关退款
        3. 更新订单状态为 refunded
        4. 取消对应用户订阅
        """
        order = self.get_order(order_no)
        if not order:
            return False, _t('Order not found')
        if order.status != OrderStatus.PAID:
            return False, _t('Order cannot be refunded (current status: {status})').format(status=order.status.value)

        # 调用支付网关退款
        from .gateways import process_refund
        refund_result = process_refund(
            order_no=order.order_no,
            amount_fen=order.amount_fen,
            channel=order.channel,
            trade_no=order.trade_no,
        )

        if not refund_result.get('success'):
            error_msg = refund_result.get('error', 'Unknown error')
            print(f'[Subscription Refund] Gateway refund failed for {order_no}: {error_msg}')
            return False, _t('Refund failed: {error}').format(error=error_msg)

        # 更新订单
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE sub_orders SET
                    status='refunded', updated_at=NOW()
                WHERE order_no=%s
            """, (order_no,))

            # 取消用户订阅
            conn.execute("""
                UPDATE user_subscriptions SET
                    status='canceled', auto_renew=0, updated_at=NOW()
                WHERE user_id=%s AND item_key=%s
            """, (order.user_id, order.item_key))

            conn.commit()

        return True, 'ok'

    # ── 内部工具 ──────────────────────────────────────────────────

    def _calc_period_end(self, start: datetime, interval: str) -> datetime:
        if interval == 'month':
            month = start.month + 1
            year = start.year
            if month > 12:
                month -= 12
                year += 1
            try:
                return start.replace(year=year, month=month)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                return start.replace(year=year, month=month, day=last_day)
        elif interval == 'year':
            try:
                return start.replace(year=start.year + 1)
            except ValueError:
                return start.replace(year=start.year + 1, month=2, day=28)
        return start + timedelta(days=30)


# ── 模块级单例 ──────────────────────────────────────────────────────────

_SERVICE = None


def get_subscription_service() -> SubscriptionService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = SubscriptionService()
    return _SERVICE


# ── 快捷函数（供外部模块调用） ──────────────────────────────────────────

def has_subscription(user_id: int, item_key: str) -> bool:
    """快捷检查：用户是否有某项订阅"""
    return get_subscription_service().has_subscription(user_id, item_key)


def get_active_features(user_id: int) -> List[str]:
    """快捷获取：用户活跃功能列表"""
    return get_subscription_service().get_active_features(user_id)


# ── 装饰器（供路由层使用） ──────────────────────────────────────────────

def require_subscription(item_key: str):
    """装饰器：要求用户订阅了指定项才能访问

    用法:
        @require_subscription('miniapp_wechat')
        def generate_miniapp():
            ...
    """
    import functools
    from flask import request, jsonify

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
            if not has_subscription(user_id, item_key):
                return jsonify({'error': f'Subscription required: {item_key}', 'code': 'NO_SUBSCRIPTION'}), 402
            return f(*args, **kwargs)
        return wrapper
    return decorator
