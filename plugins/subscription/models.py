#!/usr/bin/env python3
"""
Subscription Plugin — 数据模型
=================================
独立数据库: plugins/subscription/data/subscription.db
表:
  - sub_items           SKU 目录（可订阅项定义）
  - user_subscriptions  用户订阅记录
  - sub_orders          订阅订单
"""

import os
import psycopg2
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


# ── 数据库路径 ──────────────────────────────────────────────────────────

def get_db_path() -> str:
    return os.path.join(os.path.dirname(__file__), 'data', 'subscription.db')


def get_db():
    """获取独立数据库连接"""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
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


# ── 状态枚举 ────────────────────────────────────────────────────────────

class SubStatus(str, Enum):
    ACTIVE = 'active'
    CANCELED = 'canceled'
    EXPIRED = 'expired'
    SUSPENDED = 'suspended'


class OrderStatus(str, Enum):
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    EXPIRED = 'expired'


class IntervalType(str, Enum):
    MONTH = 'month'
    YEAR = 'year'


# ── DDL ─────────────────────────────────────────────────────────────────

SUBSCRIPTION_DDL = """
-- SKU 目录（可订阅项定义）
CREATE TABLE IF NOT EXISTS sub_items (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_key        TEXT UNIQUE NOT NULL,
    category        TEXT NOT NULL DEFAULT 'plugin',
    name_zh         TEXT NOT NULL,
    name_en         TEXT NOT NULL,
    description_zh  TEXT DEFAULT '',
    description_en  TEXT DEFAULT '',
    price_month     BIGINT NOT NULL DEFAULT 0,
    price_year      BIGINT NOT NULL DEFAULT 0,
    is_active       BIGINT NOT NULL DEFAULT 1,
    auto_activate   TEXT DEFAULT '',     -- 自动开通的 item_key 列表（逗号分隔）
    sort_order      BIGINT DEFAULT 0,
    created_at      TEXT DEFAULT (NOW()),
    updated_at      TEXT DEFAULT (NOW())
);

-- 用户订阅记录
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    item_key        TEXT NOT NULL,
    interval_type   TEXT NOT NULL DEFAULT 'month',
    amount_fen      BIGINT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active','canceled','expired','suspended')),
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    auto_renew      BIGINT NOT NULL DEFAULT 1,
    order_no        TEXT DEFAULT '',
    created_at      TEXT DEFAULT (NOW()),
    updated_at      TEXT DEFAULT (NOW()),
    UNIQUE(user_id, item_key)
);

-- 订阅订单
CREATE TABLE IF NOT EXISTS sub_orders (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_no        TEXT UNIQUE NOT NULL,
    user_id         BIGINT NOT NULL,
    item_key        TEXT NOT NULL,
    interval_type   TEXT NOT NULL DEFAULT 'month',
    amount_fen      BIGINT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'alipay',
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','paid','failed','refunded','expired')),
    trade_no        TEXT DEFAULT '',
    qr_code         TEXT DEFAULT '',
    redirect_url    TEXT DEFAULT '',
    paid_at         TEXT,
    created_at      TEXT DEFAULT (NOW()),
    updated_at      TEXT DEFAULT (NOW()),
    extra           TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sub_items_active ON sub_items(is_active);
CREATE INDEX IF NOT EXISTS idx_sub_items_category ON sub_items(category);
CREATE INDEX IF NOT EXISTS idx_user_subs_user ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subs_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subs_item ON user_subscriptions(item_key);
CREATE INDEX IF NOT EXISTS idx_sub_orders_user ON sub_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_sub_orders_status ON sub_orders(status);
"""


def init_tables():
    """初始化所有表"""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
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
    conn.execute(SUBSCRIPTION_DDL)
    conn.commit()
    conn.close()


# ── 默认 SKU 种子数据 ──────────────────────────────────────────────────

DEFAULT_ITEMS = [
    # 系统底座
    {
        'item_key': 'base',
        'category': 'base',
        'name_zh': '系统底座',
        'name_en': 'System Base',
        'description_zh': 'CMS 内容管理 + Agent 矩阵 + 口令控制台 + 模型配置 + 邮件服务 + AI 图片生成',
        'description_en': 'CMS + Agent Matrix + Command Console + Model Config + Email + AI Image Gen',
        'price_month': 9900,
        'price_year': 106800,
        'sort_order': 1,
        'auto_activate': 'email',
    },
    # 小程序网关
    {
        'item_key': 'miniapp_wechat',
        'category': 'miniapp',
        'name_zh': '微信小程序',
        'name_en': 'WeChat Mini App',
        'description_zh': '生成并发布微信小程序',
        'description_en': 'Generate and publish WeChat Mini App',
        'price_month': 9900,
        'price_year': 106800,
        'sort_order': 10,
    },
    {
        'item_key': 'miniapp_douyin',
        'category': 'miniapp',
        'name_zh': '抖音小程序',
        'name_en': 'Toutiao Mini App',
        'description_zh': '生成并发布抖音小程序',
        'description_en': 'Generate and publish Toutiao Mini App',
        'price_month': 9900,
        'price_year': 106800,
        'sort_order': 11,
    },
    {
        'item_key': 'miniapp_telegram',
        'category': 'miniapp',
        'name_zh': 'Telegram 小程序',
        'name_en': 'Telegram Mini App',
        'description_zh': '生成并发布 Telegram Mini App',
        'description_en': 'Generate and publish Telegram Mini App',
        'price_month': 9900,
        'price_year': 106800,
        'sort_order': 12,
    },
    {
        'item_key': 'miniapp_line',
        'category': 'miniapp',
        'name_zh': 'LINE 小程序',
        'name_en': 'LINE Mini App',
        'description_zh': '生成并发布 LINE 小程序',
        'description_en': 'Generate and publish LINE Mini App',
        'price_month': 9900,
        'price_year': 106800,
        'sort_order': 13,
    },
    # 能力项
    {
        'item_key': 'api_management',
        'category': 'feature',
        'name_zh': 'API 管理',
        'name_en': 'API Management',
        'description_zh': 'API 密钥生成、额度管理、调用统计、访问日志',
        'description_en': 'API key generation, quota management, call stats, access logs',
        'price_month': 1500,
        'price_year': 16200,
        'sort_order': 20,
    },
    {
        'item_key': 'enterprise_verify',
        'category': 'feature',
        'name_zh': '企业认证',
        'name_en': 'Enterprise Verification',
        'description_zh': '企业资质认证服务',
        'description_en': 'Enterprise qualification verification',
        'price_month': 1000,
        'price_year': 10800,
        'sort_order': 21,
    },
    {
        'item_key': 'oauth_config',
        'category': 'feature',
        'name_zh': 'OAuth 登录配置',
        'name_en': 'OAuth Login Config',
        'description_zh': '配置第三方 OAuth 登录（Google/GitHub/Facebook）',
        'description_en': 'Configure third-party OAuth login (Google/GitHub/Facebook)',
        'price_month': 1000,
        'price_year': 10800,
        'sort_order': 22,
    },
    {
        'item_key': 'site_domains',
        'category': 'feature',
        'name_zh': '自定义域名',
        'name_en': 'Custom Domain',
        'description_zh': '绑定独立域名到你的站点',
        'description_en': 'Bind a custom domain to your site',
        'price_month': 1000,
        'price_year': 10800,
        'sort_order': 23,
    },
    {
        'item_key': 'analytics',
        'category': 'feature',
        'name_zh': '数据分析',
        'name_en': 'Analytics',
        'description_zh': '站点访问统计与趋势分析',
        'description_en': 'Site traffic stats and trend analysis',
        'price_month': 1500,
        'price_year': 16200,
        'sort_order': 24,
    },
    {
        'item_key': 'health_check',
        'category': 'feature',
        'name_zh': '健康巡检',
        'name_en': 'Health Check',
        'description_zh': '系统健康监控与自动告警',
        'description_en': 'System health monitoring and auto-alerting',
        'price_month': 1000,
        'price_year': 10800,
        'sort_order': 25,
    },
    {
        'item_key': 'sms_service',
        'category': 'feature',
        'name_zh': '短信服务',
        'name_en': 'SMS Service',
        'description_zh': '短信验证码与通知发送',
        'description_en': 'SMS verification and notification',
        'price_month': 1500,
        'price_year': 16200,
        'sort_order': 26,
    },
    {
        'item_key': 'social_push',
        'category': 'feature',
        'name_zh': '社媒推送',
        'name_en': 'Social Push',
        'description_zh': '自动推送内容到社交媒体平台',
        'description_en': 'Auto-publish content to social media',
        'price_month': 1500,
        'price_year': 16200,
        'sort_order': 27,
    },
    {
        'item_key': 'content_factory',
        'category': 'feature',
        'name_zh': '内容工厂',
        'name_en': 'Content Factory',
        'description_zh': 'AI 批量内容生成',
        'description_en': 'AI batch content generation',
        'price_month': 1500,
        'price_year': 16200,
        'sort_order': 28,
    },
    {
        'item_key': 'automation',
        'category': 'feature',
        'name_zh': '自动任务',
        'name_en': 'Automation',
        'description_zh': '定时自动执行工作流',
        'description_en': 'Scheduled workflow automation',
        'price_month': 1000,
        'price_year': 10800,
        'sort_order': 29,
    },
    {
        'item_key': 'logistics',
        'category': 'feature',
        'name_zh': '物流查询',
        'name_en': 'Logistics',
        'description_zh': '国际物流追踪查询',
        'description_en': 'International logistics tracking',
        'price_month': 1000,
        'price_year': 10800,
        'sort_order': 30,
    },
]


def seed_default_items():
    """种子 SKU 目录（INSERT ... ON CONFLICT，不覆盖已有数据）"""
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
    for item in DEFAULT_ITEMS:
        conn.execute("""
            INSERT INTO sub_items
                (item_key, category, name_zh, name_en, description_zh, description_en,
                 price_month, price_year, sort_order, auto_activate)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (item_key) DO NOTHING
        """, (
            item['item_key'], item['category'],
            item['name_zh'], item['name_en'],
            item['description_zh'], item['description_en'],
            item['price_month'], item['price_year'],
            item['sort_order'], item.get('auto_activate', ''),
        ))
    conn.commit()
    conn.close()


# ── 数据类 ──────────────────────────────────────────────────────────────

@dataclass
class SubItem:
    """可订阅项"""
    item_key: str
    category: str
    name_zh: str
    name_en: str
    price_month: int
    price_year: int
    description_zh: str = ''
    description_en: str = ''
    is_active: bool = True
    auto_activate: str = ''
    sort_order: int = 0
    id: Optional[int] = None

    def to_dict(self, locale: str = 'zh-CN') -> dict:
        return {
            'id': self.id,
            'item_key': self.item_key,
            'category': self.category,
            'name': self.name_zh if locale == 'zh-CN' else self.name_en,
            'description': self.description_zh if locale == 'zh-CN' else self.description_en,
            'price_month': self.price_month,
            'price_year': self.price_year,
            'price_month_yuan': f'{self.price_month / 100:.2f}',
            'price_year_yuan': f'{self.price_year / 100:.2f}',
            'is_active': self.is_active,
            'sort_order': self.sort_order,
        }

    @classmethod
    def from_row(cls, row: dict) -> 'SubItem':
        return cls(
            id=row['id'],
            item_key=row['item_key'],
            category=row['category'],
            name_zh=row['name_zh'],
            name_en=row['name_en'],
            description_zh=row.get('description_zh', ''),
            description_en=row.get('description_en', ''),
            price_month=row['price_month'],
            price_year=row['price_year'],
            is_active=bool(row.get('is_active', 1)),
            auto_activate=row.get('auto_activate', ''),
            sort_order=row.get('sort_order', 0),
        )


@dataclass
class UserSubscription:
    """用户订阅"""
    user_id: int
    item_key: str
    interval_type: str
    amount_fen: int
    period_start: str
    period_end: str
    status: SubStatus = SubStatus.ACTIVE
    auto_renew: bool = True
    order_no: str = ''
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_key': self.item_key,
            'interval_type': self.interval_type,
            'amount_fen': self.amount_fen,
            'amount_yuan': f'{self.amount_fen / 100:.2f}',
            'status': self.status.value,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'auto_renew': self.auto_renew,
            'order_no': self.order_no,
        }

    @classmethod
    def from_row(cls, row: dict) -> 'UserSubscription':
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            item_key=row['item_key'],
            interval_type=row['interval_type'],
            amount_fen=row['amount_fen'],
            period_start=row['period_start'],
            period_end=row['period_end'],
            status=SubStatus(row['status']),
            auto_renew=bool(row.get('auto_renew', 1)),
            order_no=row.get('order_no', ''),
        )


@dataclass
class SubOrder:
    """订阅订单"""
    order_no: str
    user_id: int
    item_key: str
    interval_type: str
    amount_fen: int
    channel: str
    status: OrderStatus = OrderStatus.PENDING
    trade_no: str = ''
    qr_code: str = ''
    redirect_url: str = ''
    paid_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'order_no': self.order_no,
            'user_id': self.user_id,
            'item_key': self.item_key,
            'interval_type': self.interval_type,
            'amount_fen': self.amount_fen,
            'amount_yuan': f'{self.amount_fen / 100:.2f}',
            'channel': self.channel,
            'status': self.status.value,
            'trade_no': self.trade_no,
            'qr_code': self.qr_code,
            'redirect_url': self.redirect_url,
            'paid_at': self.paid_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> 'SubOrder':
        import json
        return cls(
            id=row['id'],
            order_no=row['order_no'],
            user_id=row['user_id'],
            item_key=row['item_key'],
            interval_type=row['interval_type'],
            amount_fen=row['amount_fen'],
            channel=row['channel'],
            status=OrderStatus(row['status']),
            trade_no=row.get('trade_no', ''),
            qr_code=row.get('qr_code', ''),
            redirect_url=row.get('redirect_url', ''),
            paid_at=row.get('paid_at'),
            extra=json.loads(row.get('extra', '{}')),
        )
