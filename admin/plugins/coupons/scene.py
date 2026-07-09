#!/usr/bin/env python3
"""
场景券（Scene Coupon）定义
=========================
券不再只绑定"商品"，而是绑定"场景"。
"""


class SceneName:
    """系统内置场景常量。"""

    # ── 商城场景 ──
    SHOP_GENERAL = 'shop_general'           # 商城通用
    FIRST_ORDER = 'first_order'             # 首单
    REVIEW_REWARD = 'review_reward'         # 评价奖励

    # ── 采购场景 ──
    PURCHASE_1688 = 'purchase_1688'         # 1688 采购

    # ── AI 场景 ──
    AI_CONTENT = 'ai_content'               # AI 内容生成

    # ── 订阅场景 ──
    SUBSCRIPTION_RENEW = 'subscription_renew'   # 续费
    SUBSCRIPTION_UPGRADE = 'subscription_upgrade'  # 升级

    # ── 运营场景 ──
    NEW_USER = 'new_user'                   # 新人
    PROMOTION = 'promotion'                 # 推广
    REFERRAL = 'referral'                   # 推荐有礼


# 场景 → 可读描述（用于前端展示）
SCENE_LABELS = {
    SceneName.SHOP_GENERAL: '商城通用',
    SceneName.FIRST_ORDER: '首单专享',
    SceneName.REVIEW_REWARD: '评价奖励',
    SceneName.PURCHASE_1688: '1688 采购',
    SceneName.AI_CONTENT: 'AI 内容生成',
    SceneName.SUBSCRIPTION_RENEW: '续费专享',
    SceneName.SUBSCRIPTION_UPGRADE: '升级优惠',
    SceneName.NEW_USER: '新人专享',
    SceneName.PROMOTION: '推广活动',
    SceneName.REFERRAL: '推荐有礼',
}

SCENE_LABELS_EN = {
    SceneName.SHOP_GENERAL: 'Shop General',
    SceneName.FIRST_ORDER: 'First Order',
    SceneName.REVIEW_REWARD: 'Review Reward',
    SceneName.PURCHASE_1688: '1688 Purchase',
    SceneName.AI_CONTENT: 'AI Content',
    SceneName.SUBSCRIPTION_RENEW: 'Renewal',
    SceneName.SUBSCRIPTION_UPGRADE: 'Upgrade',
    SceneName.NEW_USER: 'New User',
    SceneName.PROMOTION: 'Promotion',
    SceneName.REFERRAL: 'Referral',
}


def get_scene_label(scene: str, locale: str = 'zh-CN') -> str:
    """获取场景的可读名称。"""
    labels = SCENE_LABELS_EN if locale == 'en' else SCENE_LABELS
    return labels.get(scene, scene)
