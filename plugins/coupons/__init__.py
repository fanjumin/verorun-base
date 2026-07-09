#!/usr/bin/env python3
"""
Coupon Plugin — 智能优惠券引擎
===============================
场景券 / AI 推荐 / 订阅联动
使用独立 coupons.db 存储券表，主库只读查询。
"""

from plugin_manager.base import BasePlugin

from .engine import CouponEngine
from .ai_recommender import AICouponRecommender
from .routes import coupon_bp, init_routes
from .models import get_db, get_main_db, init_db

# ── 全局引用，方便外部调用 ──
_engine: CouponEngine = None
_recommender: AICouponRecommender = None


def get_engine() -> CouponEngine:
    """获取 CouponEngine 单例（供核心代码调用）。"""
    return _engine


def get_recommender() -> AICouponRecommender:
    """获取 AICouponRecommender 单例。"""
    return _recommender


class CouponPlugin(BasePlugin):
    name = 'coupons'
    version = '0.1.0'
    description = '智能优惠券引擎 — 场景券/AI推荐/订阅联动'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化插件数据库。"""
        init_db()
        return True

    def on_enable(self, registry):
        """启用时初始化引擎。"""
        global _engine, _recommender

        _engine = CouponEngine(get_db, get_main_db, t_func=self.t)
        _recommender = AICouponRecommender(_engine)

        # 注入到 routes（传递 t 函数）
        init_routes(get_db, get_main_db, _engine, _recommender, t_func=self.t)

        print(f'[CouponPlugin] CouponEngine initialized')
        return True

    def register_routes(self):
        """注册蓝图为系统路由。"""
        return [coupon_bp]
