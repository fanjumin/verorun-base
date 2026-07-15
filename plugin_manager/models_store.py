#!/usr/bin/env python3
"""
Plugin Manager — License & Store 数据库模型
=============================================
存放于主库 data/verorun.db。

表:
  - plugin_licenses: 已激活的 License 记录
  - store_plugins:   远程商店插件缓存（本地镜像）
"""

import os
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from .models import get_registry_db


# ── 枚举 ──────────────────────────────────────────────────────────────

class LicenseType(str, Enum):
    FREE = 'free'           # 免费
    ONETIME = 'onetime'     # 一次性买断
    SUBSCRIPTION = 'sub'    # 订阅
    TRIAL = 'trial'         # 试用


class LicenseStatus(str, Enum):
    INACTIVE = 'inactive'           # 未激活
    ACTIVE = 'active'               # 正常
    EXPIRED = 'expired'             # 过期
    REVOKED = 'revoked'             # 吊销
    PENDING = 'pending'             # 待激活
    GRACE = 'grace'                 # 离线宽容期内


class PriceInterval(str, Enum):
    ONETIME = 'onetime'
    MONTHLY = 'month'
    YEARLY = 'year'


# ── DDL ───────────────────────────────────────────────────────────────

LICENSE_STORE_DDL = """
-- License 记录表
CREATE TABLE IF NOT EXISTS plugin_licenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_id       TEXT NOT NULL,                  -- 插件 identifier
    license_key     TEXT NOT NULL UNIQUE,            -- License Key
    license_type    TEXT NOT NULL DEFAULT 'free'
                    CHECK(license_type IN ('free','onetime','sub','trial')),
    license_status  TEXT NOT NULL DEFAULT 'pending'
                    CHECK(license_status IN ('inactive','active','expired','revoked','pending','grace')),
    site_id         TEXT NOT NULL,                   -- 站点唯一标识
    site_name       TEXT DEFAULT '',                 -- 站点名称（客户自定义）
    customer_email  TEXT DEFAULT '',                 -- 购买者邮箱
    max_sites       INTEGER NOT NULL DEFAULT 1,      -- 最大激活站点数
    activated_at    TEXT,                            -- 首次激活时间
    expires_at      TEXT,                            -- 过期时间
    trial_ends_at   TEXT,                            -- 试用截止时间
    last_validated  TEXT,                            -- 最后验证时间
    offline_token   TEXT DEFAULT '',                 -- 离线 token（加密）
    grace_until     TEXT,                            -- 离线宽容截止时间
    order_id        TEXT DEFAULT '',                 -- 关联订单号
    subscription_id TEXT DEFAULT '',                 -- 关联订阅 ID
    auto_renew      INTEGER NOT NULL DEFAULT 0,      -- 是否自动续费
    metadata        TEXT DEFAULT '{}',               -- 扩展信息 JSON
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_plugin_licenses_plugin
    ON plugin_licenses(plugin_id);
CREATE INDEX IF NOT EXISTS idx_plugin_licenses_key
    ON plugin_licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_plugin_licenses_site
    ON plugin_licenses(site_id);

-- 商店插件缓存表
CREATE TABLE IF NOT EXISTS store_plugins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier      TEXT NOT NULL UNIQUE,            -- 插件标识
    name            TEXT NOT NULL,                   -- 显示名称
    description     TEXT DEFAULT '',
    version         TEXT NOT NULL DEFAULT '0.1.0',
    author          TEXT DEFAULT '',
    author_url      TEXT DEFAULT '',
    icon_url        TEXT DEFAULT '',
    price_type      TEXT NOT NULL DEFAULT 'free'
                    CHECK(price_type IN ('free','onetime','sub','trial')),
    price_amount    INTEGER DEFAULT 0,               -- 价格（分）
    price_interval  TEXT DEFAULT 'onetime'
                    CHECK(price_interval IN ('onetime','month','year')),
    trial_days      INTEGER DEFAULT 0,               -- 试用天数
    download_url    TEXT DEFAULT '',                 -- 下载地址
    package_hash    TEXT DEFAULT '',                 -- 包签名哈希
    file_size       INTEGER DEFAULT 0,               -- 文件大小（bytes）
    category        TEXT DEFAULT '',
    tags            TEXT DEFAULT '[]',               -- JSON array
    min_app_version TEXT DEFAULT '0.10.0',
    depends_on      TEXT DEFAULT '{}',               -- JSON
    screenshots     TEXT DEFAULT '[]',
    readme_url      TEXT DEFAULT '',
    downloads       INTEGER DEFAULT 0,
    rating          REAL DEFAULT 0.0,
    review_count    INTEGER DEFAULT 0,               -- 评价总数
    enabled         INTEGER NOT NULL DEFAULT 1,      -- 是否上架
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS plugin_reviews (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    plugin_identifier TEXT NOT NULL,
    user_id           INTEGER NOT NULL,
    user_name         TEXT DEFAULT '',
    rating            INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    content           TEXT DEFAULT '',
    version           TEXT DEFAULT '',
    is_active         INTEGER DEFAULT 1,
    reply_content     TEXT DEFAULT '',
    reply_at          TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(plugin_identifier, user_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_plugin
    ON plugin_reviews(plugin_identifier, is_active, created_at);

CREATE INDEX IF NOT EXISTS idx_store_plugins_category
    ON store_plugins(category);
CREATE INDEX IF NOT EXISTS idx_store_plugins_price
    ON store_plugins(price_type);
"""


# ── 初始化 ─────────────────────────────────────────────────────────────

def init_license_store_tables():
    """幂等初始化 License + Store 表"""
    with get_registry_db() as conn:
        conn.executescript(LICENSE_STORE_DDL)
        print(f'[PluginManager] ✅ plugin_licenses + store_plugins tables ready')
        conn.commit()


# ── LicenseRecord 数据类 ──────────────────────────────────────────────

@dataclass
class LicenseRecord:
    plugin_id: str
    license_key: str
    license_type: LicenseType = LicenseType.FREE
    license_status: LicenseStatus = LicenseStatus.PENDING
    site_id: str = ''
    site_name: str = ''
    customer_email: str = ''
    max_sites: int = 1
    activated_at: Optional[str] = None
    expires_at: Optional[str] = None
    trial_ends_at: Optional[str] = None
    last_validated: Optional[str] = None
    offline_token: str = ''
    grace_until: Optional[str] = None
    order_id: str = ''
    subscription_id: str = ''
    auto_renew: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d['license_type'] = self.license_type.value
        d['license_status'] = self.license_status.value
        if isinstance(d.get('metadata'), dict):
            d['metadata'] = json.dumps(d['metadata'], ensure_ascii=False)
        return d

    @classmethod
    def from_row(cls, row: dict) -> 'LicenseRecord':
        return cls(
            id=row['id'],
            plugin_id=row['plugin_id'],
            license_key=row['license_key'],
            license_type=LicenseType(row['license_type']),
            license_status=LicenseStatus(row['license_status']),
            site_id=row.get('site_id', ''),
            site_name=row.get('site_name', ''),
            customer_email=row.get('customer_email', ''),
            max_sites=row.get('max_sites', 1),
            activated_at=row.get('activated_at'),
            expires_at=row.get('expires_at'),
            trial_ends_at=row.get('trial_ends_at'),
            last_validated=row.get('last_validated'),
            offline_token=row.get('offline_token', ''),
            grace_until=row.get('grace_until'),
            order_id=row.get('order_id', ''),
            subscription_id=row.get('subscription_id', ''),
            auto_renew=bool(row.get('auto_renew', 0)),
            metadata=json.loads(row.get('metadata', '{}')),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )


# ── StorePlugin 数据类 ───────────────────────────────────────────────

@dataclass
class StorePlugin:
    identifier: str
    name: str
    description: str = ''
    version: str = '0.1.0'
    author: str = ''
    author_url: str = ''
    icon_url: str = ''
    price_type: str = 'free'
    price_amount: int = 0
    price_interval: str = 'onetime'
    trial_days: int = 0
    download_url: str = ''
    package_hash: str = ''
    file_size: int = 0
    category: str = ''
    tags: List[str] = field(default_factory=list)
    min_app_version: str = '0.10.0'
    depends_on: Dict[str, str] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    readme_url: str = ''
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_row(cls, row: dict) -> 'StorePlugin':
        return cls(
            id=row['id'],
            identifier=row['identifier'],
            name=row['name'],
            description=row.get('description', ''),
            version=row.get('version', '0.1.0'),
            author=row.get('author', ''),
            author_url=row.get('author_url', ''),
            icon_url=row.get('icon_url', ''),
            price_type=row.get('price_type', 'free'),
            price_amount=row.get('price_amount', 0),
            price_interval=row.get('price_interval', 'onetime'),
            trial_days=row.get('trial_days', 0),
            download_url=row.get('download_url', ''),
            package_hash=row.get('package_hash', ''),
            file_size=row.get('file_size', 0),
            category=row.get('category', ''),
            tags=json.loads(row.get('tags', '[]')),
            min_app_version=row.get('min_app_version', '0.10.0'),
            depends_on=json.loads(row.get('depends_on', '{}')),
            screenshots=json.loads(row.get('screenshots', '[]')),
            readme_url=row.get('readme_url', ''),
            downloads=row.get('downloads', 0),
            rating=row.get('rating', 0.0),
            review_count=row.get('review_count', 0),
            enabled=bool(row.get('enabled', 1)),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )


@dataclass
class PluginReview:
    id: Optional[int] = None
    plugin_identifier: str = ''
    user_id: int = 0
    user_name: str = ''
    rating: int = 5
    content: str = ''
    version: str = ''
    is_active: bool = True
    reply_content: str = ''
    reply_at: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d['is_active'] = int(self.is_active)
        return d

    @classmethod
    def from_row(cls, row: dict) -> 'PluginReview':
        return cls(
            id=row['id'],
            plugin_identifier=row['plugin_identifier'],
            user_id=row['user_id'],
            user_name=row.get('user_name', ''),
            rating=row['rating'],
            content=row.get('content', ''),
            version=row.get('version', ''),
            is_active=bool(row.get('is_active', 1)),
            reply_content=row.get('reply_content', ''),
            reply_at=row.get('reply_at'),
            created_at=row.get('created_at'),
        )
