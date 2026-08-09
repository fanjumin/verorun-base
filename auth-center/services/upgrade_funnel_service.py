#!/usr/bin/env python3
"""
Upgrade Funnel Service — Phase 5

Manages the free → paid → premium upgrade path with progressive feature unlocking.
Includes trial period management, usage-based upgrade nudges, and ROI calculation.

Usage:
    from services.upgrade_funnel_service import UpgradeFunnelService
    uf = UpgradeFunnelService()
    status = uf.get_trial_status(user_id)
    nudge = uf.get_upgrade_nudge(user_id)
    roi = uf.calculate_roi(user_id, plugin_count=3)
"""

# ⚠️ DEPRECATED (legacy) — 本服务无生产调用者。
# 主站订阅链路当前由 auth-center/routes/subscription/__init__.py 承载。
# 迁移/重构前请勿基于本文件实现新逻辑。上线任务 T12 要求：仅标注，不迁移。


from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from models import get_db, now_iso
from services.feature_gate_service import FEATURE_MATRIX

# ── Helpers ───────────────────────────────────────────────────────────────


def _format_daily_limit(limit: int) -> str:
    """Format a daily limit value: -1 means unlimited, otherwise the real number."""
    return 'Unlimited' if limit < 0 else str(limit)


def _get_paid_plan_price() -> int:
    """Read the actual paid plan monthly price (fen) from subscription_plans.

    Falls back to 8800 (¥88) when no active plan is configured.
    """
    try:
        with get_db() as conn:
            row = conn.execute(
                'SELECT price_month FROM subscription_plans WHERE is_active=1 ORDER BY price_month ASC LIMIT 1'
            ).fetchone()
        if row:
            return int(row['price_month'])
    except Exception:
        pass
    return 8800

# ── Constants ──────────────────────────────────────────────────────────────

TRIAL_DAYS = 14
TRIAL_DAILY_LIMIT = 50  # elevated during trial
TRIAL_MAX_PLUGINS = 3   # elevated during trial

UPGRADE_NUDGE_THRESHOLDS = {
    'daily_usage_80pct':  {
        'days_at_80pct': 3,
        'message': 'You\'ve been using {pct}% of your daily quota for {days} days. Upgrade to unlock more.',
        'discount_offer': 15,  # 15% off first month
    },
    'feature_blocked': {
        'message': '"{feature}" is a {tier} feature. Upgrade to unlock this and {n} more features.',
        'discount_offer': 10,
    },
    'plugin_limit': {
        'message': 'You\'ve reached the {limit}-plugin limit. Upgrade for unlimited plugins.',
        'discount_offer': 10,
    },
    'watermark_shown': {
        'message': 'Remove the "Powered by VeroRun" watermark with a paid plan.',
        'discount_offer': 20,
    },
}

# ── UpgradeFunnelService ───────────────────────────────────────────────────


class UpgradeFunnelService:
    """Progressive upgrade funnel: trial → paid → premium."""

    # ── Trial Management ───────────────────────────────────────────────

    def start_trial(self, user_id: int) -> Dict[str, Any]:
        """Start a 14-day trial for a user."""
        with get_db() as conn:
            existing = conn.execute(
                'SELECT * FROM user_subscriptions WHERE user_id=%s',
                (user_id,),
            ).fetchone()

            if existing:
                if existing['status'] == 'active' and existing['plan_key'] != 'trial':
                    return {'success': False, 'error': 'User already has an active subscription'}
                if existing['plan_key'] == 'trial':
                    return {'success': False, 'error': 'Trial already started'}

            now = now_iso()
            trial_end = (datetime.now() + timedelta(days=TRIAL_DAYS)).isoformat()

            if existing:
                conn.execute(
                    'UPDATE user_subscriptions SET plan_key=%s, status=%s, daily_limit=%s, '
                    'trial_started_at=%s, trial_ends_at=%s, updated_at=%s '
                    'WHERE user_id=%s',
                    ('trial', 'active', TRIAL_DAILY_LIMIT, now, trial_end, now, user_id),
                )
            else:
                conn.execute(
                    'INSERT INTO user_subscriptions '
                    '(user_id, plan_key, status, daily_limit, trial_started_at, trial_ends_at, created_at, updated_at) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                    (user_id, 'trial', 'active', TRIAL_DAILY_LIMIT, now, trial_end, now, now),
                )
            conn.commit()

        return {
            'success': True,
            'trial_started_at': now,
            'trial_ends_at': trial_end,
            'trial_days': TRIAL_DAYS,
            'daily_limit': TRIAL_DAILY_LIMIT,
            'max_plugins': TRIAL_MAX_PLUGINS,
            'message': f'Trial started! {TRIAL_DAYS} days of full access.',
        }

    def get_trial_status(self, user_id: int) -> Dict[str, Any]:
        """Get current trial status for a user."""
        with get_db() as conn:
            sub = conn.execute(
                'SELECT plan_key, status, trial_started_at, trial_ends_at, daily_limit '
                'FROM user_subscriptions WHERE user_id=%s',
                (user_id,),
            ).fetchone()

        if not sub or sub['plan_key'] != 'trial':
            return {'in_trial': False, 'message': 'Not in trial'}

        status = sub['status']
        trial_end = sub.get('trial_ends_at', '')
        trial_start = sub.get('trial_started_at', '')

        # Check if trial expired
        try:
            end = datetime.fromisoformat(trial_end)
            now = datetime.now()
            days_remaining = (end - now).days
            is_expired = days_remaining < 0
        except (ValueError, TypeError):
            days_remaining = 0
            is_expired = True

        if status == 'cancelled' or is_expired:
            return {
                'in_trial': False,
                'was_trial': True,
                'trial_ended': True,
                'trial_end': trial_end,
                'message': 'Trial has ended',
                'upgrade_offer': 'Get 20% off your first month!',
            }

        return {
            'in_trial': True,
            'trial_started_at': trial_start,
            'trial_ends_at': trial_end,
            'days_remaining': max(0, days_remaining),
            'days_total': TRIAL_DAYS,
            'daily_limit': sub.get('daily_limit', TRIAL_DAILY_LIMIT),
            'status': status,
            'message': f'{days_remaining} days remaining in trial',
            'urgency': self._get_trial_urgency(days_remaining),
        }

    def _get_trial_urgency(self, days_remaining: int) -> str:
        """Get urgency level based on remaining trial days."""
        if days_remaining <= 1:
            return 'critical'
        if days_remaining <= 3:
            return 'high'
        if days_remaining <= 7:
            return 'medium'
        return 'low'

    # ── Upgrade Path ───────────────────────────────────────────────────

    def get_upgrade_path(self, user_id: int) -> Dict[str, Any]:
        """Get the full upgrade path from current tier to max tier."""
        from services.feature_gate_service import FeatureGateService
        fg = FeatureGateService()
        tier = fg.get_user_tier(user_id)

        path = {
            'current_tier': tier,
            'current_tier_name': {'free': 'Free', 'paid': 'Paid', 'premium': 'Premium'}[tier],
            'steps': [],
        }

        if tier == 'free':
            diff = fg.get_upgrade_diff(user_id)
            path['steps'].append({
                'from': 'free',
                'to': 'paid',
                'name': 'Free → Paid',
                'new_features': diff['new_features'],
                'improvements': diff['improvements'],
                'cta': 'Upgrade to Paid',
            })

        if tier in ('free', 'paid'):
            # Show premium as next step
            premium_features = {
                'free': {'advanced_analytics', 'custom_models', 'batch_processing',
                         'api_access', 'webhook', 'data_export'},
                'paid': {'priority_queue', 'team_collaboration'},
            }
            current_restricted = premium_features.get(tier, set())
            path['steps'].append({
                'from': tier,
                'to': 'premium',
                'name': f'{tier.title()} → Premium',
                'new_features': sorted(current_restricted),
                'improvements': [
                    {'metric': 'Rate limit', 'current': f'{fg.get_rate_limit(user_id)} RPM',
                     'upgraded': '300 RPM'},
                    {'metric': 'Daily limit',
                     'current': _format_daily_limit(FEATURE_MATRIX[tier]['daily_limit']),
                     'upgraded': _format_daily_limit(FEATURE_MATRIX['premium']['daily_limit'])},
                ],
                'cta': 'Go Premium',
            })

        return path

    # ── Upgrade Nudge ──────────────────────────────────────────────────

    def get_upgrade_nudge(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Generate a contextual upgrade suggestion based on user behavior.

        Returns None if no nudge is appropriate.
        """
        from services.feature_gate_service import FeatureGateService
        fg = FeatureGateService()
        tier = fg.get_user_tier(user_id)

        if tier == 'premium':
            return None

        # Check daily usage
        with get_db() as conn:
            sub = conn.execute(
                'SELECT daily_limit, calls_today FROM user_subscriptions WHERE user_id=%s',
                (user_id,),
            ).fetchone()

        if sub and sub['daily_limit'] > 0:
            usage_pct = sub['calls_today'] / sub['daily_limit'] * 100
            if usage_pct >= 80:
                threshold = UPGRADE_NUDGE_THRESHOLDS['daily_usage_80pct']
                return {
                    'type': 'daily_usage_80pct',
                    'message': threshold['message'].format(
                        pct=int(usage_pct), days=threshold['days_at_80pct']
                    ),
                    'discount_offer': threshold['discount_offer'],
                    'usage_pct': int(usage_pct),
                    'used_today': sub['calls_today'],
                    'daily_limit': sub['daily_limit'],
                    'cta': 'Unlock unlimited calls',
                }

        # Check plugin limit
        if tier == 'free':
            with get_db() as conn:
                plugin_count = conn.execute(
                    "SELECT COUNT(*) as c FROM subscription_addons "
                    "WHERE user_id=%s AND status='active'",
                    (user_id,),
                ).fetchone()

            if plugin_count['c'] >= 1:
                threshold = UPGRADE_NUDGE_THRESHOLDS['plugin_limit']
                return {
                    'type': 'plugin_limit',
                    'message': threshold['message'].format(limit=1),
                    'discount_offer': threshold['discount_offer'],
                    'current_plugins': plugin_count['c'],
                    'limit': 1,
                    'cta': 'Get unlimited plugins',
                }

        # Check watermark
        if fg.should_watermark(user_id):
            threshold = UPGRADE_NUDGE_THRESHOLDS['watermark_shown']
            return {
                'type': 'watermark',
                'message': threshold['message'],
                'discount_offer': threshold['discount_offer'],
                'cta': 'Remove watermark',
            }

        return None

    def get_feature_nudge(self, user_id: int, feature: str) -> Optional[Dict[str, Any]]:
        """Generate an upgrade nudge for a specific blocked feature."""
        from services.feature_gate_service import FeatureGateService
        fg = FeatureGateService()
        check = fg.check_feature(user_id, feature)

        if check['allowed']:
            return None

        # Count total locked features
        all_features = fg.get_allowed_features(user_id)
        locked_count = all_features['total_restricted']

        threshold = UPGRADE_NUDGE_THRESHOLDS['feature_blocked']
        return {
            'type': 'feature_blocked',
            'message': threshold['message'].format(
                feature=feature, tier=check['upgrade_path']['required_tier'].title(), n=locked_count
            ),
            'discount_offer': threshold['discount_offer'],
            'feature': feature,
            'required_tier': check['upgrade_path']['required_tier'],
            'locked_features_count': locked_count,
            'cta': f'Unlock {feature} and {locked_count} more features',
        }

    # ── ROI Calculation ────────────────────────────────────────────────

    def calculate_roi(self, user_id: int, plugin_count: int) -> Dict[str, Any]:
        """Calculate ROI of upgrading vs buying plugins individually.

        Compares total cost of separate plugin subscriptions vs bundled paid plan.
        """
        from services.pricing_service import PricingService
        ps = PricingService()

        # Hypothetical: if user buys all plugins individually
        all_plugins = ps.get_plugin_products()
        top_plugins = sorted(all_plugins, key=lambda p: p.get('price_month_fen', 0), reverse=True)[:plugin_count]

        individual_total = sum(p.get('price_month_fen', 0) for p in top_plugins)

        # Paid plan unlocks all plugins (read actual price from subscription_plans)
        paid_plan_price = _get_paid_plan_price()  # fallback 8800 if unconfigured

        savings = individual_total - paid_plan_price
        savings_pct = round(savings / individual_total * 100, 1) if individual_total > 0 else 0

        return {
            'plugin_count': plugin_count,
            'individual_total_fen': individual_total,
            'individual_total_yuan': f'¥{individual_total/100:.2f}',
            'paid_plan_price_fen': paid_plan_price,
            'paid_plan_price_yuan': f'¥{paid_plan_price/100:.2f}',
            'savings_fen': max(0, savings),
            'savings_yuan': f'¥{max(0, savings)/100:.2f}',
            'savings_percent': savings_pct,
            'is_cheaper': savings > 0,
            'message': (
                f'Buying {plugin_count} plugins individually: ¥{individual_total/100:.2f}/month. '
                f'Paid plan: ¥{paid_plan_price/100:.2f}/month. '
                + (f'Save {savings_pct}%!' if savings > 0 else 'Individual purchase is cheaper.')
            ),
            'top_plugins': [
                {'name': p.get('name', p['plugin_key']), 'price_yuan': f'¥{p.get("price_month_fen", 0)/100:.2f}'}
                for p in top_plugins
            ],
        }

    # ── Conversion Tracking ────────────────────────────────────────────

    def get_conversion_funnel(self) -> Dict[str, Any]:
        """Get aggregate conversion funnel metrics across all users."""
        with get_db() as conn:
            total = conn.execute('SELECT COUNT(*) as c FROM user_subscriptions').fetchone()
            paid = conn.execute(
                "SELECT COUNT(*) as c FROM user_subscriptions WHERE plan_key IN ('paid','standard','pro','premium')"
            ).fetchone()
            trial = conn.execute(
                "SELECT COUNT(*) as c FROM user_subscriptions WHERE plan_key='trial'"
            ).fetchone()
            trial_converted = conn.execute(
                "SELECT COUNT(*) as c FROM user_subscriptions WHERE plan_key IN ('paid','standard','pro','premium') "
                "AND trial_started_at IS NOT NULL"
            ).fetchone()

        total_users = total['c'] if total else 0
        paid_users = paid['c'] if paid else 0
        trial_users = trial['c'] if trial else 0
        converted = trial_converted['c'] if trial_converted else 0

        return {
            'total_users': total_users,
            'paid_users': paid_users,
            'free_users': total_users - paid_users,
            'conversion_rate': round(paid_users / total_users * 100, 1) if total_users > 0 else 0,
            'trial_users': trial_users,
            'trial_to_paid': converted,
            'trial_conversion_rate': round(converted / trial_users * 100, 1) if trial_users > 0 else 0,
        }