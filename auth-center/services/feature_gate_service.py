#!/usr/bin/env python3
"""
Feature Gate Service — Phase 5

Centralized feature gate enforcement for the free → paid upgrade funnel.
All feature access decisions flow through this single service.

Feature tiers:
  free     — 20 calls/day, 1 plugin, watermark, basic features only
  paid     — no watermark, unlimited plugins, all features, higher rate limits
  premium  — priority queue, custom models, advanced analytics

Usage:
    from services.feature_gate_service import FeatureGateService
    fg = FeatureGateService()
    if fg.should_watermark(user_id):
        result.add_watermark()
    if not fg.check_feature(user_id, 'advanced_analytics'):
        return {'error': 'Upgrade required'}
"""

# ⚠️ DEPRECATED (legacy) — 本服务无生产调用者（仅被同为遗留的 upgrade_funnel_service 内部引用）。
# 主站订阅链路当前由 auth-center/routes/subscription/__init__.py 承载。
# 迁移/重构前请勿基于本文件实现新逻辑。上线任务 T12 要求：仅标注，不迁移。


from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set

from models import get_db, now_iso

# ── Feature Definitions ────────────────────────────────────────────────────

FEATURE_MATRIX = {
    'free': {
        'name': 'Free',
        'daily_limit': 20,
        'max_plugins': 1,
        'watermark': True,
        'rate_limit_rpm': 5,
        'supported_models': ['basic'],
        'features': {
            'basic_chat', 'basic_translation', 'basic_sentiment',
            'text_to_speech', 'basic_ocr',
        },
        'restricted_features': {
            'advanced_analytics', 'custom_models', 'priority_queue',
            'batch_processing', 'api_access', 'webhook',
            'data_export', 'team_collaboration',
        },
    },
    'paid': {
        'name': 'Paid',
        'daily_limit': 1000,
        'max_plugins': -1,  # unlimited
        'watermark': False,
        'rate_limit_rpm': 60,
        'supported_models': ['basic', 'advanced', 'custom'],
        'features': {
            'basic_chat', 'basic_translation', 'basic_sentiment',
            'text_to_speech', 'basic_ocr',
            'advanced_analytics', 'custom_models',
            'batch_processing', 'api_access', 'webhook',
            'data_export',
        },
        'restricted_features': {
            'priority_queue', 'team_collaboration',
        },
    },
    'premium': {
        'name': 'Premium',
        'daily_limit': -1,  # unlimited
        'max_plugins': -1,  # unlimited
        'watermark': False,
        'rate_limit_rpm': 300,
        'supported_models': ['basic', 'advanced', 'custom', 'enterprise'],
        'features': {
            'basic_chat', 'basic_translation', 'basic_sentiment',
            'text_to_speech', 'basic_ocr',
            'advanced_analytics', 'custom_models', 'priority_queue',
            'batch_processing', 'api_access', 'webhook',
            'data_export', 'team_collaboration',
        },
        'restricted_features': set(),
    },
}

ALL_FEATURES = set()
for tier in FEATURE_MATRIX.values():
    ALL_FEATURES.update(tier['features'])
    ALL_FEATURES.update(tier['restricted_features'])


# ── FeatureGateService ─────────────────────────────────────────────────────


class FeatureGateService:
    """Centralized feature gate for subscription tier enforcement."""

    # ── Tier Resolution ────────────────────────────────────────────────

    def get_user_tier(self, user_id: int) -> str:
        """Resolve user's effective tier: free, paid, or premium."""
        with get_db() as conn:
            sub = conn.execute(
                'SELECT plan_key FROM user_subscriptions WHERE user_id=%s AND status=%s',
                (user_id, 'active'),
            ).fetchone()

        if not sub:
            return 'free'

        plan_key = sub['plan_key']
        if plan_key in ('premium', 'enterprise'):
            return 'premium'
        if plan_key in ('paid', 'standard', 'pro'):
            return 'paid'
        return 'free'

    def get_tier_config(self, user_id: int) -> Dict[str, Any]:
        """Get full tier configuration for a user."""
        tier = self.get_user_tier(user_id)
        return {'tier': tier, **FEATURE_MATRIX[tier]}

    # ── Feature Checks ─────────────────────────────────────────────────

    def check_feature(self, user_id: int, feature: str) -> Dict[str, Any]:
        """Check if a user can access a specific feature.

        Returns:
            {allowed, tier, feature, message, upgrade_path}
        """
        tier = self.get_user_tier(user_id)
        tier_config = FEATURE_MATRIX[tier]
        allowed = feature in tier_config['features']

        if allowed:
            return {
                'allowed': True,
                'tier': tier,
                'feature': feature,
                'message': 'Access granted',
                'upgrade_path': None,
            }

        # Find which tier unlocks this feature
        upgrade_tier = None
        for t in ('paid', 'premium'):
            if feature in FEATURE_MATRIX[t]['features']:
                upgrade_tier = t
                break

        return {
            'allowed': False,
            'tier': tier,
            'feature': feature,
            'message': f'"{feature}" requires {upgrade_tier} tier',
            'upgrade_path': {
                'current_tier': tier,
                'required_tier': upgrade_tier,
                'tier_name': FEATURE_MATRIX[upgrade_tier]['name'] if upgrade_tier else 'Unknown',
            },
        }

    def should_watermark(self, user_id: int) -> bool:
        """Check if output should include a watermark."""
        tier = self.get_user_tier(user_id)
        return FEATURE_MATRIX[tier]['watermark']

    def get_plugin_limit(self, user_id: int) -> int:
        """Get max plugins user can subscribe to. -1 = unlimited."""
        tier = self.get_user_tier(user_id)
        return FEATURE_MATRIX[tier]['max_plugins']

    def get_rate_limit(self, user_id: int) -> int:
        """Get RPM rate limit for user."""
        tier = self.get_user_tier(user_id)
        return FEATURE_MATRIX[tier]['rate_limit_rpm']

    def get_daily_limit(self, user_id: int) -> int:
        """Get daily API call limit. -1 = unlimited."""
        tier = self.get_user_tier(user_id)
        return FEATURE_MATRIX[tier]['daily_limit']

    def get_supported_models(self, user_id: int) -> List[str]:
        """Get available AI models for user."""
        tier = self.get_user_tier(user_id)
        return list(FEATURE_MATRIX[tier]['supported_models'])

    def can_use_model(self, user_id: int, model_name: str) -> bool:
        """Check if user can use a specific model."""
        tier = self.get_user_tier(user_id)
        return model_name in FEATURE_MATRIX[tier]['supported_models']

    # ── Feature Lists ──────────────────────────────────────────────────

    def get_allowed_features(self, user_id: int) -> Dict[str, Any]:
        """Get complete feature access map for a user."""
        tier = self.get_user_tier(user_id)
        tier_config = FEATURE_MATRIX[tier]
        allowed = tier_config['features']
        restricted = tier_config['restricted_features']

        return {
            'tier': tier,
            'tier_name': tier_config['name'],
            'allowed_features': sorted(allowed),
            'restricted_features': sorted(restricted),
            'total_allowed': len(allowed),
            'total_restricted': len(restricted),
            'total_features': len(ALL_FEATURES),
            'unlock_percent': round(len(allowed) / len(ALL_FEATURES) * 100, 1),
        }

    def get_upgrade_diff(self, user_id: int) -> Dict[str, Any]:
        """Show what features would be unlocked by upgrading."""
        tier = self.get_user_tier(user_id)
        if tier == 'premium':
            return {'tier': 'premium', 'upgrade_available': False, 'new_features': [],
                    'message': 'Already at highest tier'}

        next_tier = 'paid' if tier == 'free' else 'premium'
        current_features = FEATURE_MATRIX[tier]['features']
        next_features = FEATURE_MATRIX[next_tier]['features']
        new_features = sorted(next_features - current_features)

        improvements = []
        current_config = FEATURE_MATRIX[tier]
        next_config = FEATURE_MATRIX[next_tier]

        if current_config['daily_limit'] < next_config['daily_limit']:
            improvements.append({
                'metric': 'Daily API calls',
                'current': f'{current_config["daily_limit"]}' if current_config['daily_limit'] >= 0 else 'Unlimited',
                'upgraded': f'{next_config["daily_limit"]}' if next_config['daily_limit'] >= 0 else 'Unlimited',
            })
        if current_config['watermark'] and not next_config['watermark']:
            improvements.append({'metric': 'Watermark', 'current': 'Yes', 'upgraded': 'No'})
        if current_config['max_plugins'] != next_config['max_plugins']:
            improvements.append({
                'metric': 'Max plugins',
                'current': f'{current_config["max_plugins"]}' if current_config['max_plugins'] >= 0 else 'Unlimited',
                'upgraded': f'{next_config["max_plugins"]}' if next_config['max_plugins'] >= 0 else 'Unlimited',
            })

        return {
            'current_tier': tier,
            'upgrade_tier': next_tier,
            'upgrade_tier_name': FEATURE_MATRIX[next_tier]['name'],
            'upgrade_available': True,
            'new_features': new_features,
            'new_feature_count': len(new_features),
            'improvements': improvements,
            'improvement_count': len(improvements),
        }

    # ── Bulk Checks ────────────────────────────────────────────────────

    def check_all_features(self, user_id: int) -> Dict[str, Any]:
        """Check all features for a user in one call."""
        tier = self.get_user_tier(user_id)
        result = {'tier': tier, 'tier_name': FEATURE_MATRIX[tier]['name'], 'features': {}}
        for f in sorted(ALL_FEATURES):
            result['features'][f] = self.check_feature(user_id, f)['allowed']
        return result

    def check_upgrade_required(self, user_id: int, feature: str) -> Dict[str, Any]:
        """Quick check: does this feature require an upgrade?"""
        check = self.check_feature(user_id, feature)
        if check['allowed']:
            return {'required': False, 'feature': feature, 'message': 'Already have access'}
        return {
            'required': True,
            'feature': feature,
            'current_tier': check['tier'],
            'required_tier': check['upgrade_path']['required_tier'],
            'message': check['message'],
        }