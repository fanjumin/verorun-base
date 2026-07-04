#!/usr/bin/env python3
"""
Coupon Plugin — 智能优惠券引擎
===============================
场景券 / AI 推荐 / 订阅联动
"""

from plugins.base import BasePlugin

from .engine import CouponEngine
from .ai_recommender import AICouponRecommender
from .routes import coupon_bp, init_routes

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
        """安装时添加 scene 字段到 coupons 表。"""
        from models import get_db
        try:
            with get_db() as conn:
                cols = [r['name'] for r in conn.execute(
                    'PRAGMA table_info(coupons)').fetchall()]
                if 'scene' not in cols:
                    conn.execute(
                        "ALTER TABLE coupons ADD COLUMN scene TEXT DEFAULT ''")
                    print('[CouponPlugin] coupons.scene column added')
                # 确保 coupon_redemptions 表存在
                conn.execute('''CREATE TABLE IF NOT EXISTS coupon_redemptions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    coupon_id       INTEGER NOT NULL REFERENCES coupons(id),
                    user_id         INTEGER NOT NULL,
                    order_no        TEXT NOT NULL,
                    discount_fen    INTEGER NOT NULL DEFAULT 0,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
                conn.commit()
        except Exception as e:
            print(f'[CouponPlugin] on_install error: {e}')
        return True

    def on_enable(self, registry):
        """启用时初始化引擎。"""
        global _engine, _recommender

        from models import get_db

        _engine = CouponEngine(get_db)
        _recommender = AICouponRecommender(_engine)

        # 注入到 routes
        init_routes(get_db, _engine, _recommender)

        print(f'[CouponPlugin] CouponEngine initialized')
        return True

    def register_routes(self):
        """注册蓝图为系统路由。"""
        return [coupon_bp]
