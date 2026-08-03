#!/usr/bin/env python3
"""
Unified Subscription Service — Phase 4

Manages base plans (free entry) and individual plugin subscriptions.
Each plugin is independently subscribed — no bundle packaging.

Data model:
  base_plans          — single free entry plan (daily 20 API calls)
  plugin_products     — each plugin as an independent product
  user_subscriptions  — one record per user for base plan
  subscription_addons — per-user per-plugin subscription records

Usage:
    from services.unified_subscription_service import UnifiedSubscriptionService
    svc = UnifiedSubscriptionService()
    svc.subscribe_plugin(user_id=1, plugin_key='sentiment', period='month')
    access = svc.check_plugin_access(user_id=1, plugin_key='sentiment')
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from models import get_db, now_iso

# ── Constants ──────────────────────────────────────────────────────────────

FREE_DAILY_LIMIT = 20
BASE_PLAN_KEY = 'free'
VALID_PERIODS = ('month', 'year')
PERIOD_DAYS = {'month': 30, 'year': 365}


# ── UnifiedSubscriptionService ─────────────────────────────────────────────


class UnifiedSubscriptionService:
    """Unified subscription management: base plan + individual plugins."""

    # ── Base Plan ──────────────────────────────────────────────────────

    def get_base_plan(self) -> Optional[Dict[str, Any]]:
        """Get the base plan (free entry)."""
        with get_db() as conn:
            row = conn.execute(
                'SELECT * FROM base_plans WHERE plan_key=%s AND is_active=1',
                (BASE_PLAN_KEY,),
            ).fetchone()
        return dict(row) if row else None

    def ensure_user_subscription(self, user_id: int) -> Dict[str, Any]:
        """Ensure a user has a base subscription record. Creates one if missing."""
        with get_db() as conn:
            sub = conn.execute(
                'SELECT * FROM user_subscriptions WHERE user_id=%s',
                (user_id,),
            ).fetchone()

            if sub:
                return dict(sub)

            now = now_iso()
            conn.execute(
                '''INSERT INTO user_subscriptions
                   (user_id, plan_key, status, daily_limit, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s)''',
                (user_id, BASE_PLAN_KEY, 'active', FREE_DAILY_LIMIT, now, now),
            )
            conn.commit()
            return {
                'user_id': user_id,
                'plan_key': BASE_PLAN_KEY,
                'status': 'active',
                'daily_limit': FREE_DAILY_LIMIT,
                'calls_today': 0,
                'calls_total': 0,
            }

    def get_subscription_summary(self, user_id: int) -> Dict[str, Any]:
        """Get full subscription overview: base plan + active plugin addons."""
        base = self.ensure_user_subscription(user_id)
        addons = self.list_user_addons(user_id)

        return {
            'user_id': user_id,
            'base_plan': {
                'plan_key': base['plan_key'],
                'status': base['status'],
                'daily_limit': base.get('daily_limit', FREE_DAILY_LIMIT),
                'calls_today': base.get('calls_today', 0),
                'calls_total': base.get('calls_total', 0),
            },
            'addons': addons,
            'addon_count': len(addons),
            'monthly_cost_fen': sum(a.get('price_month_fen', 0) for a in addons if a['status'] == 'active'),
        }

    # ── Plugin Subscription ────────────────────────────────────────────

    def subscribe_plugin(
        self,
        user_id: int,
        plugin_key: str,
        period: str = 'month',
        payment_method: str = 'wechat',
    ) -> Tuple[bool, Dict[str, Any]]:
        """Subscribe to a plugin. Returns (success, result_dict).

        The actual payment is handled externally; this records the subscription
        intent and creates the addon record.
        """
        if period not in VALID_PERIODS:
            return False, {'error': f'Invalid period: {period}. Must be one of {VALID_PERIODS}'}

        # Validate plugin exists
        plugin = self._get_plugin_product(plugin_key)
        if not plugin:
            return False, {'error': f'Plugin not found: {plugin_key}'}

        # Ensure base subscription exists
        self.ensure_user_subscription(user_id)

        # Check existing addon
        existing = self._get_user_addon(user_id, plugin_key)
        if existing and existing['status'] == 'active':
            return False, {'error': f'Already subscribed to plugin: {plugin_key}', 'addon': existing}

        now = now_iso()
        expire_days = PERIOD_DAYS.get(period, 30)
        period_start = now
        period_end = (datetime.now() + timedelta(days=expire_days)).isoformat()

        price_fen = self._get_plugin_price(plugin_key, period)

        with get_db() as conn:
            if existing and existing['status'] in ('expired', 'cancelled'):
                # Reactivate
                conn.execute(
                    '''UPDATE subscription_addons
                       SET status='active', period=%s, period_start=%s, period_end=%s,
                           price_fen=%s, payment_method=%s, updated_at=%s
                       WHERE user_id=%s AND plugin_key=%s''',
                    (period, period_start, period_end, price_fen, payment_method, now, user_id, plugin_key),
                )
            else:
                conn.execute(
                    '''INSERT INTO subscription_addons
                       (user_id, plugin_key, plugin_name, period, period_start, period_end,
                        price_fen, payment_method, status, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (user_id, plugin_key, plugin['name'], period, period_start, period_end,
                     price_fen, payment_method, 'active', now, now),
                )
            conn.commit()

        addon = self._get_user_addon(user_id, plugin_key)
        return True, {
            'addon': addon,
            'plugin': plugin,
            'period': period,
            'price_fen': price_fen,
            'price_yuan': f'¥{price_fen/100:.2f}',
            'period_end': period_end,
            'message': f'Subscribed to {plugin["name"]}',
        }

    def unsubscribe_plugin(self, user_id: int, plugin_key: str) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a plugin subscription. Access continues until period end."""
        addon = self._get_user_addon(user_id, plugin_key)
        if not addon or addon['status'] != 'active':
            return False, {'error': f'No active subscription for plugin: {plugin_key}'}

        with get_db() as conn:
            conn.execute(
                "UPDATE subscription_addons SET status='cancelled', updated_at=%s "
                'WHERE user_id=%s AND plugin_key=%s',
                (now_iso(), user_id, plugin_key),
            )
            conn.commit()

        return True, {
            'plugin_key': plugin_key,
            'status': 'cancelled',
            'access_until': addon['period_end'],
            'message': 'Cancelled. Access continues until period end.',
        }

    def list_user_addons(self, user_id: int) -> List[Dict[str, Any]]:
        """List all plugin addons for a user."""
        with get_db() as conn:
            rows = conn.execute(
                'SELECT * FROM subscription_addons WHERE user_id=%s ORDER BY created_at DESC',
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def check_plugin_access(self, user_id: int, plugin_key: str) -> Dict[str, Any]:
        """Check if a user has access to a specific plugin.

        Returns {allowed, status, addon, reason}.
        """
        addon = self._get_user_addon(user_id, plugin_key)

        if not addon:
            return {'allowed': False, 'status': None, 'addon': None, 'reason': 'not subscribed'}

        status = addon['status']
        if status == 'active':
            return {'allowed': True, 'status': 'active', 'addon': addon, 'reason': 'ok'}

        if status == 'cancelled':
            # Check if still within current period
            period_end = addon.get('period_end', '')
            if period_end:
                try:
                    end = datetime.fromisoformat(period_end)
                    if datetime.now() < end:
                        return {'allowed': True, 'status': 'cancelled', 'addon': addon,
                                'reason': 'cancelled but within period'}
                except (ValueError, TypeError):
                    pass
            return {'allowed': False, 'status': 'cancelled', 'addon': addon,
                    'reason': 'cancelled, period expired'}

        return {'allowed': False, 'status': status, 'addon': addon, 'reason': f'status: {status}'}

    def list_available_plugins(self) -> List[Dict[str, Any]]:
        """List all available plugin products for purchase."""
        with get_db() as conn:
            rows = conn.execute(
                'SELECT * FROM plugin_products WHERE is_active=1 ORDER BY sort_order',
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Internal Helpers ───────────────────────────────────────────────

    def _get_plugin_product(self, plugin_key: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute(
                'SELECT * FROM plugin_products WHERE plugin_key=%s AND is_active=1',
                (plugin_key,),
            ).fetchone()
        return dict(row) if row else None

    def _get_user_addon(self, user_id: int, plugin_key: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute(
                'SELECT * FROM subscription_addons WHERE user_id=%s AND plugin_key=%s',
                (user_id, plugin_key),
            ).fetchone()
        return dict(row) if row else None

    def _get_plugin_price(self, plugin_key: str, period: str) -> int:
        plugin = self._get_plugin_product(plugin_key)
        if not plugin:
            return 0
        return plugin.get('price_year_fen', 0) if period == 'year' else plugin.get('price_month_fen', 0)

    def update_daily_usage(self, user_id: int):
        """Increment daily usage counter for the user's base plan."""
        with get_db() as conn:
            conn.execute(
                'UPDATE user_subscriptions SET calls_today=calls_today+1, calls_total=calls_total+1 '
                'WHERE user_id=%s AND status=%s',
                (user_id, 'active'),
            )
            conn.commit()

    def check_daily_quota(self, user_id: int) -> Dict[str, Any]:
        """Check remaining daily quota for a user."""
        base = self.ensure_user_subscription(user_id)
        daily_limit = base.get('daily_limit', FREE_DAILY_LIMIT)
        used_today = base.get('calls_today', 0)

        if daily_limit <= 0:
            return {'allowed': True, 'remaining': -1, 'daily_limit': 0, 'used_today': used_today,
                    'reason': 'unlimited'}

        remaining = max(0, daily_limit - used_today)
        return {
            'allowed': remaining > 0,
            'remaining': remaining,
            'daily_limit': daily_limit,
            'used_today': used_today,
            'reason': 'ok' if remaining > 0 else 'daily quota exceeded',
        }