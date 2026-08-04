#!/usr/bin/env python3
"""
Shop Plugin — Database initialization
======================================
All 11 shop tables in the `shop` PostgreSQL schema.
Exact copy of auth-center/models/database.py init_shop_db().
"""
import os
import sys

# Ensure auth-center is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'auth-center'))

from models import get_db


def init_shop_db():
    """Create shop tables in shop schema."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS shop")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.products (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                title           TEXT NOT NULL,
                subtitle        TEXT DEFAULT '',
                product_type    TEXT NOT NULL DEFAULT 'service',
                category        TEXT DEFAULT '',
                price           DOUBLE PRECISION NOT NULL DEFAULT 0,
                original_price  DOUBLE PRECISION DEFAULT 0,
                stock           BIGINT DEFAULT 0,
                sales_count     BIGINT DEFAULT 0,
                thumbnail       TEXT DEFAULT '',
                description     TEXT DEFAULT '',
                features        TEXT DEFAULT '[]',
                ai_config       TEXT DEFAULT '{}',
                sort_order      BIGINT DEFAULT 0,
                is_active       BIGINT DEFAULT 1,
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW(),
                images          TEXT DEFAULT '[]',
                category_id     BIGINT DEFAULT 0
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_type ON shop.products(product_type)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_products_active ON shop.products(is_active)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.categories (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name        TEXT NOT NULL,
                slug        TEXT UNIQUE,
                parent_id   BIGINT DEFAULT 0,
                level       BIGINT DEFAULT 0,
                icon        TEXT DEFAULT '',
                sort_order  BIGINT DEFAULT 0,
                is_active   BIGINT DEFAULT 1,
                created_at  TIMESTAMP DEFAULT NOW(),
                updated_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cat_parent ON shop.categories(parent_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cat_level ON shop.categories(level)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.carts (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id         BIGINT NOT NULL,
                product_id      BIGINT NOT NULL,
                sku_id          BIGINT DEFAULT 0,
                quantity        BIGINT DEFAULT 1,
                created_at      TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, product_id)
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_carts_user ON shop.carts(user_id)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.user_purchases (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id         BIGINT NOT NULL,
                product_id      BIGINT NOT NULL,
                order_id        TEXT DEFAULT '',
                purchase_type   TEXT NOT NULL DEFAULT 'once',
                expire_at       TIMESTAMP,
                status          TEXT DEFAULT 'active',
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_up_user ON shop.user_purchases(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_up_status ON shop.user_purchases(status)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.order_items (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                order_id        TEXT NOT NULL,
                user_id         BIGINT NOT NULL,
                product_id      BIGINT NOT NULL,
                product_title   TEXT NOT NULL DEFAULT '',
                quantity        BIGINT DEFAULT 1,
                unit_price      DOUBLE PRECISION NOT NULL DEFAULT 0,
                subtotal        DOUBLE PRECISION NOT NULL DEFAULT 0,
                coupon_id       BIGINT DEFAULT NULL,
                discount        DOUBLE PRECISION DEFAULT 0,
                status          TEXT DEFAULT 'pending',
                created_at      TIMESTAMP DEFAULT NOW(),
                paid_at         TIMESTAMP,
                idempotency_key TEXT DEFAULT '',
                payment_method  TEXT DEFAULT '',
                payment_trade_no TEXT DEFAULT '',
                tracking_company TEXT DEFAULT '',
                tracking_number  TEXT DEFAULT '',
                shipping_status  TEXT DEFAULT '',
                shipped_at       TIMESTAMP,
                completed_at     TIMESTAMP,
                refund_reason    TEXT DEFAULT '',
                refund_requested_at TIMESTAMP,
                refunded_at      TIMESTAMP,
                user_deleted     BIGINT DEFAULT 0
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_oi_order ON shop.order_items(order_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_oi_user ON shop.order_items(user_id)"
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_oi_idempotency ON shop.order_items(idempotency_key) WHERE idempotency_key != ''"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.order_shipping (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                order_item_id   BIGINT NOT NULL,
                tracking_company TEXT DEFAULT '',
                tracking_number  TEXT DEFAULT '',
                shipping_status  TEXT DEFAULT '',
                shipped_at       TIMESTAMP,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_os_orderitem ON shop.order_shipping(order_item_id)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.product_specs (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                product_id  BIGINT NOT NULL,
                spec_name   TEXT NOT NULL,
                sort_order  BIGINT DEFAULT 0,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_ps_product ON shop.product_specs(product_id)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.product_spec_values (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                spec_id     BIGINT NOT NULL,
                spec_value  TEXT NOT NULL,
                sort_order  BIGINT DEFAULT 0,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_psv_spec ON shop.product_spec_values(spec_id)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.product_skus (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                product_id  BIGINT NOT NULL,
                sku_code    TEXT NOT NULL,
                spec_path   TEXT NOT NULL DEFAULT '{}',
                price       DOUBLE PRECISION NOT NULL DEFAULT 0,
                stock       BIGINT DEFAULT 0,
                image       TEXT DEFAULT '',
                is_active   BIGINT DEFAULT 1,
                created_at  TIMESTAMP DEFAULT NOW(),
                updated_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_psk_product ON shop.product_skus(product_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_psk_code ON shop.product_skus(sku_code)"
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.pricing_rules (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                rule_key    TEXT UNIQUE NOT NULL,
                label       TEXT NOT NULL,
                rule_type   TEXT NOT NULL DEFAULT 'radio',
                options_json TEXT NOT NULL DEFAULT '[]',
                sort_order  BIGINT DEFAULT 0,
                is_active   BIGINT DEFAULT 1,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop.express_companies (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                code        TEXT NOT NULL UNIQUE,
                name        TEXT NOT NULL,
                kdniao_code TEXT DEFAULT '',
                is_active   BIGINT DEFAULT 1,
                sort_order  BIGINT DEFAULT 0,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    print('[ShopPlugin] shop schema initialized in PostgreSQL')
