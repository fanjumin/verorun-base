#!/usr/bin/env python3
"""
旧订阅模块（已解耦至插件）
=============================
订阅功能已整体迁移至 plugins/subscription（独立 subscription schema）。
本包仅保留子包 gateway/ 供 shop 插件支付网关复用
（微信/支付宝/Stripe/PayPal 的签名校验与支付调用）。
旧 sub_bp 全部路由已下线。
"""


def _fulfill_order(order_no, payment_method=None, channel_order_id=None, notify_id=None, notify_raw=None):
    """[已弃用] 旧订阅履约逻辑。

    订阅系统已迁移至插件 plugins/subscription，此函数不再可用。
    若被调用说明仍有旧 notify 路径残留，应立即排查并切换到插件。
    """
    raise RuntimeError(
        'legacy subscription fulfillment decommissioned; '
        'subscription is now served by plugins/subscription'
    )
