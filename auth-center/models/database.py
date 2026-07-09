#!/usr/bin/env python3
"""auth-center: Unified Database Manager - all 易站智能 apps share one DB."""
import os, sqlite3
from datetime import datetime
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
DB_PATH = os.environ.get('DB_PATH', os.path.join(DATA_DIR, 'x7k2m9a4.db'))
os.makedirs(DATA_DIR, exist_ok=True)

# 国际化：当前市场
MARKET = os.environ.get('DEPLOY_MARKET', 'cn')


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=1000")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT UNIQUE,
                phone           TEXT UNIQUE,
                phone_verified  INTEGER DEFAULT 0,
                email           TEXT UNIQUE,
                password_hash   TEXT,
                wechat_openid   TEXT UNIQUE,
                wechat_unionid  TEXT,
                wechat_nickname TEXT,
                douyin_open_id  TEXT UNIQUE,
                douyin_nickname TEXT,
                douyin_avatar   TEXT,
                avatar_url      TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                last_login      TEXT,
                active          INTEGER DEFAULT 1,
                is_admin        INTEGER DEFAULT 0,
                agent_id        TEXT UNIQUE,
                agent_nickname  TEXT DEFAULT '',
                agent_avatar_url TEXT DEFAULT '',
                display_name      TEXT DEFAULT '',
                email_verified    INTEGER DEFAULT 0,
                password_changed_at TEXT,
                totp_secret       TEXT DEFAULT '',
                totp_enabled      INTEGER DEFAULT 0,
                security_level    INTEGER DEFAULT 0,
                completion_percentage  INTEGER DEFAULT 0,
                completion_last_updated TEXT
            );
            CREATE TABLE IF NOT EXISTS user_profiles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id),
                gender          TEXT DEFAULT '' CHECK(gender IN ('', 'male', 'female', 'other', 'secret')),
                birth_date      TEXT DEFAULT NULL,
                age_group       TEXT DEFAULT '',
                occupation      TEXT DEFAULT '',
                industry        TEXT DEFAULT '',
                interests       TEXT DEFAULT '[]',
                bio             TEXT DEFAULT '',
                industry_id     INTEGER DEFAULT NULL,
                career_id       INTEGER DEFAULT NULL,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS industries (
                id          INTEGER PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                sort_order  INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS career_options (
                id          INTEGER PRIMARY KEY,
                category    TEXT NOT NULL CHECK(category IN ('job', 'freelance')),
                name        TEXT NOT NULL UNIQUE,
                industry_id INTEGER DEFAULT NULL REFERENCES industries(id) ON DELETE SET NULL,
                parent_id   INTEGER DEFAULT NULL REFERENCES career_options(id) ON DELETE CASCADE,
                sort_order  INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_career_options_category ON career_options(category);
            CREATE INDEX IF NOT EXISTS idx_career_options_parent   ON career_options(parent_id);
            CREATE TABLE IF NOT EXISTS user_addresses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                recipient_name  TEXT NOT NULL DEFAULT '',
                phone           TEXT NOT NULL DEFAULT '',
                province_code   TEXT NOT NULL DEFAULT '',
                city_code       TEXT NOT NULL DEFAULT '',
                district_code   TEXT NOT NULL DEFAULT '',
                street_code     TEXT NOT NULL DEFAULT '',
                street_address  TEXT NOT NULL DEFAULT '',
                postal_code     TEXT DEFAULT '',
                is_default      INTEGER DEFAULT 0,
                status          INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_user_addresses_user ON user_addresses(user_id);
            CREATE TABLE IF NOT EXISTS app_authorizations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                app_name        TEXT NOT NULL,
                tier            TEXT DEFAULT 'free',
                tier_expire_at  TEXT,
                calls_today     INTEGER DEFAULT 0,
                calls_total     INTEGER DEFAULT 0,
                last_reset      TEXT,
                active          INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, app_name)
            );
            CREATE TABLE IF NOT EXISTS api_keys (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                app_name        TEXT NOT NULL,
                key_hash        TEXT UNIQUE NOT NULL,
                key_prefix      TEXT NOT NULL,
                name            TEXT DEFAULT '',
                calls_today     INTEGER DEFAULT 0,
                calls_total     INTEGER DEFAULT 0,
                last_reset      TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                expire_at       TEXT,
                last_used       TEXT,
                active          INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS system_config (
                key             TEXT PRIMARY KEY,
                value           TEXT NOT NULL DEFAULT '',
                description     TEXT DEFAULT '',
                updated_at      TEXT DEFAULT (datetime('now')),
                updated_by      INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS user_notifications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                type            TEXT NOT NULL DEFAULT 'system',
                title           TEXT NOT NULL,
                content         TEXT DEFAULT '',
                link_url        TEXT DEFAULT '',
                is_read         INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id),
                prefs           TEXT DEFAULT '{}',   -- JSON: {"system_site":true,"system_mail":true,"order_site":true,"order_mail":true,"activity_site":true,"activity_mail":false}
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS user_agents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                agent_name      TEXT NOT NULL DEFAULT '',
                agent_type      TEXT NOT NULL DEFAULT 'personal',  -- personal / trading
                avatar_url      TEXT DEFAULT '',
                status          TEXT DEFAULT 'active',  -- active / inactive / suspended
                default_scopes  TEXT DEFAULT '[]',      -- JSON: ["stock:read","market:alert"]
                metadata        TEXT DEFAULT '{}',      -- JSON: non-privacy business data
                last_active_ip  TEXT DEFAULT '',
                last_active_at  TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_user_agents_user ON user_agents(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_agents_name ON user_agents(user_id, agent_name);
            
            CREATE TABLE IF NOT EXISTS agent_api_keys (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id        INTEGER NOT NULL REFERENCES user_agents(id),
                user_id         INTEGER NOT NULL REFERENCES users(id),
                key_hash        TEXT UNIQUE NOT NULL,
                key_prefix      TEXT NOT NULL,
                name            TEXT DEFAULT '',
                scopes          TEXT DEFAULT '[]',      -- JSON override, empty=inherit from agent
                status          TEXT DEFAULT 'active',   -- active / revoked / expired
                expire_at       TEXT,
                last_used_at    TEXT,
                rotated_at      TEXT,
                rotated_from_key_id INTEGER DEFAULT 0,
                calls_today     INTEGER DEFAULT 0,
                calls_total     INTEGER DEFAULT 0,
                last_reset      TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_agent_keys_agent ON agent_api_keys(agent_id);
            CREATE INDEX IF NOT EXISTS idx_agent_keys_user ON agent_api_keys(user_id);
            CREATE INDEX IF NOT EXISTS idx_agent_keys_hash ON agent_api_keys(key_hash);

            CREATE TABLE IF NOT EXISTS agent_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id        INTEGER REFERENCES user_agents(id),
                user_id         INTEGER REFERENCES users(id),
                action          TEXT NOT NULL,  -- create / revoke_key / rotate_key / suspend / activate
                detail          TEXT DEFAULT '',
                ip_address      TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON agent_logs(agent_id);
            CREATE INDEX IF NOT EXISTS idx_agent_logs_user ON agent_logs(user_id);

            CREATE TABLE IF NOT EXISTS user_sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                token_hash      TEXT NOT NULL,
                device_name     TEXT DEFAULT '',
                device_type     TEXT DEFAULT '',  -- mobile / desktop / api
                ip_address      TEXT DEFAULT '',
                user_agent      TEXT DEFAULT '',
                location        TEXT DEFAULT '',
                is_current      INTEGER DEFAULT 0,
                last_active     TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                expired_at      TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
            
            CREATE TABLE IF NOT EXISTS agent_experiences (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                agent_id        TEXT NOT NULL,
                title           TEXT NOT NULL,
                content         TEXT NOT NULL,
                category        TEXT DEFAULT 'analysis',
                tags            TEXT DEFAULT '',
                status          TEXT DEFAULT 'draft',
                is_published    INTEGER DEFAULT 0,
                like_count      INTEGER DEFAULT 0,
                view_count      INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS favorites (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                target_type     TEXT NOT NULL,
                target_id       INTEGER NOT NULL,
                created_at      TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, target_type, target_id)
            );
            CREATE TABLE IF NOT EXISTS user_activity (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                type            TEXT NOT NULL DEFAULT 'system',
                title           TEXT NOT NULL,
                content         TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS admin_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id        INTEGER REFERENCES users(id),
                action          TEXT NOT NULL,
                target_type     TEXT DEFAULT '',
                target_id       TEXT DEFAULT '',
                detail          TEXT DEFAULT '',
                ip_address      TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sms_templates (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                category        TEXT NOT NULL,
                name            TEXT NOT NULL,
                template_code   TEXT NOT NULL,
                note            TEXT DEFAULT '',
                sort_order      INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
                UNIQUE(category, name)
            );
            INSERT OR IGNORE INTO sms_templates (category, name, template_code, note, sort_order) VALUES
                ('captcha', '新用户注册',   'SMS_506350148', '新用户注册验证码', 1),
                ('captcha', '用户登录',     'SMS_506430157', '用户登录验证码', 2),
                ('captcha', '忘记/重置密码', 'SMS_506140192', '密码重置验证码', 3),
                ('captcha', '变更手机号',   'SMS_506175167', '手机号变更验证码', 4),
                ('notice',  '订阅通知',     'SMS_506235155', '会员订阅成功通知', 5),
                ('promo',   '新用户礼包',   'SMS_506455152', '新用户注册赠送优惠券通知', 6);
                        CREATE TABLE IF NOT EXISTS agents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                type            TEXT NOT NULL DEFAULT 'child',
                alias           TEXT NOT NULL,
                mission         TEXT NOT NULL DEFAULT '',
                system_prompt   TEXT NOT NULL DEFAULT '',
                -- ↓ 以下字段废弃，由 provider_models 统一管理
                provider        TEXT NOT NULL DEFAULT '',
                model_name      TEXT NOT NULL DEFAULT '',
                base_url        TEXT NOT NULL DEFAULT '',
                api_key_enc     TEXT NOT NULL DEFAULT '',
                capabilities    TEXT NOT NULL DEFAULT 'text',
                -- ↑ 废弃字段
                provider_model_id INTEGER DEFAULT NULL,
                -- ↓ 旧迁移兼容，废弃
                model_provider_id INTEGER DEFAULT NULL,
                -- ↑ 废弃
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            -- 模型提供商（顶层级联）
            CREATE TABLE IF NOT EXISTS providers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                slug            TEXT NOT NULL UNIQUE DEFAULT '',
                name            TEXT NOT NULL DEFAULT '',
                description     TEXT NOT NULL DEFAULT '',
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            -- 提供商下的模型（端点 + Key + model_name）
            CREATE TABLE IF NOT EXISTS provider_models (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id     INTEGER NOT NULL REFERENCES providers(id),
                name            TEXT NOT NULL DEFAULT '',
                model_name      TEXT NOT NULL DEFAULT '',
                endpoint_url    TEXT NOT NULL DEFAULT '',
                api_key_ref     TEXT NOT NULL DEFAULT '',
                capabilities    TEXT NOT NULL DEFAULT 'text',
                sort_order      INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_pm_provider ON provider_models(provider_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_pm_provider_model_unique ON provider_models(provider_id, model_name);
            CREATE TABLE IF NOT EXISTS billing_orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                order_no        TEXT UNIQUE NOT NULL,
                amount          REAL NOT NULL DEFAULT 0,
                currency        TEXT DEFAULT 'CNY',
                item_type       TEXT NOT NULL,
                item_desc       TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                payment_method  TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                paid_at         TEXT
            );


            CREATE TABLE IF NOT EXISTS sms_codes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT NOT NULL,
                code            TEXT NOT NULL,
                purpose         TEXT DEFAULT 'login',
                expires_at      TEXT NOT NULL,
                used            INTEGER DEFAULT 0,
                attempts        INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sms_rate_limits (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT NOT NULL,
                hour_bucket     TEXT NOT NULL,
                count           INTEGER DEFAULT 0,
                UNIQUE(phone, hour_bucket)
            );
            CREATE TABLE IF NOT EXISTS email_codes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT NOT NULL,
                code            TEXT NOT NULL,
                purpose         TEXT DEFAULT 'login',
                expires_at      TEXT NOT NULL,
                used            INTEGER DEFAULT 0,
                attempts        INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_email_code ON email_codes(email, code, purpose);
            CREATE TABLE IF NOT EXISTS login_attempts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT DEFAULT '',
                ip              TEXT NOT NULL DEFAULT '',
                success         INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip);
            CREATE INDEX IF NOT EXISTS idx_login_attempts_phone ON login_attempts(phone);
            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                app_name        TEXT NOT NULL,
                order_id        TEXT UNIQUE NOT NULL,
                tier_bought     TEXT,
                amount          REAL,
                pay_method      TEXT,
                status          TEXT DEFAULT 'pending',
                created_at      TEXT DEFAULT (datetime('now')),
                paid_at         TEXT
            );
            CREATE TABLE IF NOT EXISTS chat_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                app_name        TEXT DEFAULT 'trademind',
                session_id      TEXT,
                role            TEXT,
                content         TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_app_auth_user ON app_authorizations(user_id);
            CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
            CREATE INDEX IF NOT EXISTS idx_sms_phone ON sms_codes(phone);
            CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);

            CREATE TABLE IF NOT EXISTS site_configs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                domain          TEXT NOT NULL UNIQUE,
                name            TEXT NOT NULL,
                industry        TEXT NOT NULL DEFAULT '',
                theme_color     TEXT DEFAULT '#6366f1',
                accent_color    TEXT DEFAULT '#8b5cf6',
                logo_url        TEXT DEFAULT '',
                favicon_url     TEXT DEFAULT '',
                tier            TEXT DEFAULT 'free',
                features        TEXT DEFAULT '[]',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_site_configs_domain ON site_configs(domain);

            CREATE TABLE IF NOT EXISTS site_blocks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id         INTEGER NOT NULL REFERENCES site_configs(id),
                page            TEXT NOT NULL,
                section         TEXT NOT NULL,
                block_type      TEXT NOT NULL DEFAULT 'text',
                position        INTEGER NOT NULL DEFAULT 0,
                title           TEXT DEFAULT '',
                subtitle        TEXT DEFAULT '',
                content         TEXT DEFAULT '',
                image_url       TEXT DEFAULT '',
                link_url        TEXT DEFAULT '',
                link_text       TEXT DEFAULT '',
                icon            TEXT DEFAULT '',
                extra_json      TEXT DEFAULT '{}',
                is_published    INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_site_blocks_site ON site_blocks(site_id, page, position);

            CREATE TABLE IF NOT EXISTS site_plans (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id         INTEGER NOT NULL REFERENCES site_configs(id),
                name            TEXT NOT NULL,
                tier            TEXT NOT NULL DEFAULT 'free',
                price           REAL NOT NULL DEFAULT 0,
                period          TEXT DEFAULT 'month',
                features        TEXT DEFAULT '[]',
                sort_order      INTEGER DEFAULT 0,
                is_published    INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_site_plans_site ON site_plans(site_id);
            CREATE TABLE IF NOT EXISTS contact_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                email           TEXT NOT NULL,
                subject         TEXT NOT NULL,
                message         TEXT NOT NULL,
                status          TEXT DEFAULT 'unread',
                admin_reply     TEXT,
                replied_at      TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS user_feedback (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                type            TEXT NOT NULL DEFAULT 'suggestion',
                category        TEXT NOT NULL DEFAULT 'other',
                title           TEXT NOT NULL,
                content         TEXT NOT NULL,
                contact         TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                admin_note      TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS user_tickets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER REFERENCES users(id),
                type            TEXT DEFAULT 'aftersale',
                category        TEXT DEFAULT '',
                title           TEXT NOT NULL,
                content         TEXT NOT NULL,
                contact         TEXT DEFAULT '',
                status          TEXT DEFAULT 'open',
                priority        TEXT DEFAULT 'normal',
                admin_reply     TEXT DEFAULT '',
                replied_at      TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_user_tickets_user ON user_tickets(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_tickets_status ON user_tickets(status);
            CREATE TABLE IF NOT EXISTS email_sent (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                from_addr       TEXT NOT NULL,
                to_addr         TEXT NOT NULL,
                subject         TEXT NOT NULL,
                body_text       TEXT,
                body_html       TEXT,
                in_reply_to     INTEGER,
                sent_at         TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_contact_status ON contact_messages(status);
            CREATE INDEX IF NOT EXISTS idx_email_sent_from ON email_sent(from_addr);
            CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
            CREATE TABLE IF NOT EXISTS social_push_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                platform        TEXT NOT NULL DEFAULT 'wechat',
                content_type    TEXT DEFAULT 'article',
                title           TEXT DEFAULT '',
                summary         TEXT DEFAULT '',
                article_json    TEXT DEFAULT '',
                media_id        TEXT DEFAULT '',
                publish_id      TEXT DEFAULT '',
                status          TEXT DEFAULT 'draft',
                push_time       TEXT,
                admin_id        INTEGER REFERENCES users(id),
                error_msg       TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS brand_settings (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                company_name    TEXT NOT NULL DEFAULT '',
                site_name_cn    TEXT NOT NULL DEFAULT '',
                site_name_en    TEXT NOT NULL DEFAULT '',
                slogan          TEXT NOT NULL DEFAULT '',
                tagline         TEXT NOT NULL DEFAULT '',
                description     TEXT NOT NULL DEFAULT '',
                copyright       TEXT NOT NULL DEFAULT '',
                seo_title       TEXT NOT NULL DEFAULT '',
                seo_desc        TEXT NOT NULL DEFAULT '',
                logo_url        TEXT NOT NULL DEFAULT '',
                favicon_url     TEXT NOT NULL DEFAULT '',
                icp_number      TEXT NOT NULL DEFAULT '',
                security_number TEXT NOT NULL DEFAULT '',
                contact_email   TEXT NOT NULL DEFAULT '',
                software_name   TEXT NOT NULL DEFAULT '',
                software_slogan TEXT NOT NULL DEFAULT '',
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT OR IGNORE INTO brand_settings (id) VALUES (1);
        """)
        # ── 迁移：为已有 user_tickets 表补字段 ──
        import logging
        try:
            conn.execute("ALTER TABLE user_tickets ADD COLUMN type TEXT DEFAULT 'aftersale'")
        except Exception as e:
            logging.warning(f"[Migration] Failed to add type column to user_tickets: {e}")
        try:
            conn.execute("ALTER TABLE user_tickets ADD COLUMN category TEXT DEFAULT ''")
        except Exception as e:
            logging.warning(f"[Migration] Failed to add category column to user_tickets: {e}")
        try:
            conn.execute("ALTER TABLE user_tickets ADD COLUMN contact TEXT DEFAULT ''")
        except Exception as e:
            logging.warning(f"[Migration] Failed to add contact column to user_tickets: {e}")
        try:
            conn.execute("ALTER TABLE user_tickets ADD COLUMN priority TEXT DEFAULT 'normal'")
        except Exception as e:
            logging.warning(f"[Migration] Failed to add priority column to user_tickets: {e}")
        # -- social_links: 后台社媒图标管理 --
        with get_db() as c2:
            c2.execute("""
                CREATE TABLE IF NOT EXISTS social_links (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT NOT NULL,
                    url             TEXT NOT NULL DEFAULT '#',
                    icon_url        TEXT NOT NULL DEFAULT '',
                    platform        TEXT NOT NULL DEFAULT '',
                    sort_order      INTEGER DEFAULT 0,
                    is_active       INTEGER DEFAULT 1,
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                )
            """)
            c2.commit()
        # service_plans 表 — 套餐管理
        with get_db() as c3:
            c3.execute("""
                CREATE TABLE IF NOT EXISTS service_plans (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_key        TEXT UNIQUE NOT NULL,
                    name            TEXT NOT NULL,
                    description     TEXT DEFAULT '',
                    price_month     REAL DEFAULT 0,
                    price_year      REAL DEFAULT 0,
                    daily_limit     INTEGER DEFAULT 0,
                    features        TEXT DEFAULT '[]',
                    sort_order      INTEGER DEFAULT 0,
                    is_active       INTEGER DEFAULT 1,
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                )
            """)
            c3.execute("INSERT OR IGNORE INTO service_plans (plan_key, name, description, price_month, price_year, daily_limit, features, sort_order) VALUES "
                       "('free', 'Free', '每日20次调用', 0, 0, 20, '[\"basic\"]', 1)")
            c3.execute("INSERT OR IGNORE INTO service_plans (plan_key, name, description, price_month, price_year, daily_limit, features, sort_order) VALUES "
                       "('standard', 'Standard', '每日100次调用', 88, 888, 100, '[\"basic\",\"sentiment\",\"market\"]', 2)")
            c3.execute("INSERT OR IGNORE INTO service_plans (plan_key, name, description, price_month, price_year, daily_limit, features, sort_order) VALUES "
                       "('pro', 'Pro', '每日1000次调用', 188, 1888, 1000, '[\"all\"]', 3)")
            c3.commit()
        # ── 内容工厂 4 张表 (2026-05-08) ──
        with get_db() as c4:
            c4.executescript("""
                CREATE TABLE IF NOT EXISTS content_sources (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT NOT NULL,
                    source_type     TEXT NOT NULL DEFAULT 'rss',   -- rss / api / web
                    platform        TEXT DEFAULT '',               -- 标识: xueqiu/sec/rss
                    url             TEXT DEFAULT '',
                    config_json     TEXT DEFAULT '{}',
                    crawl_interval  INTEGER DEFAULT 0,            -- 秒, 0=手动
                    keywords        TEXT DEFAULT '',
                    max_per_run     INTEGER DEFAULT 10,
                    is_active       INTEGER DEFAULT 1,
                    sort_order      INTEGER DEFAULT 0,
                    last_crawled_at TEXT,
                    created_at      TEXT DEFAULT (datetime('now')),
                    created_by      INTEGER REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS raw_contents (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id       INTEGER REFERENCES content_sources(id),
                    task_id         INTEGER,
                    title           TEXT DEFAULT '',
                    author          TEXT DEFAULT '',
                    source_url      TEXT DEFAULT '',
                    content_text    TEXT DEFAULT '',
                    content_html    TEXT DEFAULT '',
                    content_json    TEXT DEFAULT '{}',
                    summary         TEXT DEFAULT '',
                    content_hash    TEXT UNIQUE,
                    publish_time    TEXT,
                    language        TEXT DEFAULT 'zh',
                    tags            TEXT DEFAULT '',
                    status          TEXT DEFAULT 'pending',   -- pending / processing / processed / failed
                    error_msg       TEXT DEFAULT '',
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS processed_contents (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_id          INTEGER REFERENCES raw_contents(id),
                    content_type    TEXT DEFAULT 'article',    -- article / short_comment / social_card
                    title           TEXT DEFAULT '',
                    summary         TEXT DEFAULT '',
                    body            TEXT DEFAULT '',
                    body_html       TEXT DEFAULT '',
                    keywords        TEXT DEFAULT '',
                    risk_level      TEXT DEFAULT 'normal',
                    image_url       TEXT DEFAULT '',
                    agent_chain     TEXT DEFAULT '[]',
                    is_published    INTEGER DEFAULT 0,
                    status          TEXT DEFAULT 'draft',      -- draft / review / approved / rejected / published
                    reviewed_by     INTEGER REFERENCES users(id),
                    reviewed_at     TEXT,
                    created_by      INTEGER REFERENCES users(id),
                    created_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS content_tasks (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id       INTEGER REFERENCES content_sources(id),
                    task_type       TEXT NOT NULL,              -- crawl / process / publish / batch
                    trigger_type    TEXT DEFAULT 'manual',      -- manual / scheduled / keyword
                    status          TEXT DEFAULT 'pending',     -- pending / running / completed / failed
                    total_items     INTEGER DEFAULT 0,
                    done_items      INTEGER DEFAULT 0,
                    error_count     INTEGER DEFAULT 0,
                    log_text        TEXT DEFAULT '',
                    started_at      TEXT,
                    finished_at     TEXT,
                    created_by      INTEGER REFERENCES users(id),
                    created_at      TEXT DEFAULT (datetime('now'))
                );
            """)
            # Migration: add content_sources automation fields (idempotent)
            cs_cols = [r[1] for r in c4.execute("PRAGMA table_info(content_sources)").fetchall()]
            if 'ai_prompt_template' not in cs_cols:
                c4.execute("ALTER TABLE content_sources ADD COLUMN ai_prompt_template TEXT DEFAULT ''")
            if 'skip_review' not in cs_cols:
                c4.execute("ALTER TABLE content_sources ADD COLUMN skip_review INTEGER DEFAULT 0")
            if 'auto_publish' not in cs_cols:
                c4.execute("ALTER TABLE content_sources ADD COLUMN auto_publish INTEGER DEFAULT 0")
            c4.commit()
        # ── Skill推送表 (2026-05-08) ──
        with get_db() as c5:
            c5.executescript("""
                CREATE TABLE IF NOT EXISTS skill_pushes (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    processed_id    INTEGER REFERENCES processed_contents(id),
                    title           TEXT NOT NULL,
                    description     TEXT DEFAULT '',
                    skill_name      TEXT NOT NULL,
                    skill_category  TEXT DEFAULT 'content',
                    skill_content   TEXT NOT NULL,
                    skill_version   TEXT DEFAULT '1.0',
                    status          TEXT DEFAULT 'pushed',   -- pushed / installed / withdrawn
                    target_agent    TEXT DEFAULT 'hermes',    -- hermes / openclaw
                    push_count      INTEGER DEFAULT 0,
                    last_pushed_at  TEXT,
                    created_by      INTEGER REFERENCES users(id),
                    created_at      TEXT DEFAULT (datetime('now'))
                )
            """)
            c5.commit()
        
        # ── 管理员配置表 (2026-05-10) ──
        with get_db() as c_adm:
            c_adm.executescript("""
                CREATE TABLE IF NOT EXISTS admin_profiles (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER UNIQUE REFERENCES users(id),
                    role            TEXT DEFAULT 'admin',           -- super_admin / admin / operator
                    permissions     TEXT DEFAULT '[]',              -- JSON array
                    real_name       TEXT DEFAULT '',
                    internal_phone  TEXT DEFAULT '',
                    internal_email  TEXT DEFAULT '',
                    notes           TEXT DEFAULT '',
                    created_by      INTEGER DEFAULT 0,
                    last_login_ip   TEXT DEFAULT '',
                    last_login_at   TEXT,
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                )
            """)
            # 种子：***REMOVED*** (user_id=7) 为 super_admin，全部权限
            try:
                c_adm.execute(
                    "INSERT OR IGNORE INTO admin_profiles (user_id, role, permissions, real_name, notes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (7, 'super_admin', '["users","content","finance","system","matrix","admins"]', '***REMOVED***', '初始超级管理员')
                )
            except Exception:
                pass  # 用户可能还不存在，跳过
            c_adm.commit()
        # ── 主题管理 (2026-05-16) ──
        with get_db() as c_th:
            c_th.executescript("""
                CREATE TABLE IF NOT EXISTS themes (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT NOT NULL,
                    slug            TEXT UNIQUE NOT NULL,
                    version         TEXT DEFAULT '1.0.0',
                    author          TEXT DEFAULT '',
                    author_url      TEXT DEFAULT '',
                    description     TEXT DEFAULT '',
                    industry        TEXT DEFAULT '',
                    tags            TEXT DEFAULT '[]',
                    config_json     TEXT DEFAULT '{}',
                    dir_name        TEXT NOT NULL,
                    installed_at    TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS site_theme_config (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_key        TEXT UNIQUE NOT NULL,
                    theme_id        INTEGER,
                    overrides_json  TEXT DEFAULT '{}',
                    updated_at      TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (theme_id) REFERENCES themes(id) ON DELETE SET NULL
                );
            """)
            # 种子：默认主题
            c_th.execute(
                "INSERT OR IGNORE INTO themes (id, name, slug, version, author, description, industry, tags, config_json, dir_name) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (0, '默认主题', 'default', '1.0.0', '', 
                 '内置默认主题 — FinTech/AI 暗色科幻风格',
                 'finance', '["dark","fintech","ai"]',
                 '{"name":"默认主题","slug":"default","version":"1.0.0","builtin":true}',
                 'default')
            )
            # 种子：4 个站点默认使用默认主题（theme_id=NULL）
            c_th.execute("INSERT OR IGNORE INTO site_theme_config (site_key) VALUES ('main')")
            c_th.execute("INSERT OR IGNORE INTO site_theme_config (site_key) VALUES ('platform')")
            c_th.execute("INSERT OR IGNORE INTO site_theme_config (site_key) VALUES ('admin')")
            # community site key removed (智体广场已下线)
            c_th.commit()
        with get_db() as cs:
            cs.executescript('''
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_key        TEXT UNIQUE NOT NULL,
                    name            TEXT NOT NULL,
                    description     TEXT DEFAULT '',
                    price_month     INTEGER NOT NULL DEFAULT 0,
                    price_year      INTEGER NOT NULL DEFAULT 0,
                    trial_days      INTEGER DEFAULT 0,
                    tier            TEXT NOT NULL DEFAULT 'premium',
                    features_json   TEXT DEFAULT '[]',
                    sort_order      INTEGER DEFAULT 0,
                    is_active       INTEGER DEFAULT 1,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO subscription_plans (plan_key, name, description, price_month, price_year, trial_days, tier, features_json, sort_order) VALUES
                    ('deploy_basic', '基础版', '个人创业者/小微企业快速建站', 19900, 199900, 0, 'basic', '["AI智能建站(响应式+自定义域名)","AI智能客服(基础问答)","AI内容生成","基础SEO优化","CMS内容管理","多AI供应商切换(可自配APIKey)","AI分析报告","赠送¥50 AI金(额度,用尽可自购)","小程序增值入口(定制费另计)"]', 1);
                INSERT OR IGNORE INTO subscription_plans (plan_key, name, description, price_month, price_year, trial_days, tier, features_json, sort_order) VALUES
                    ('deploy_pro', '专业版', '小微企业/电商卖家线上业务首选', 39900, 399900, 0, 'popular', '["AI智能建站","AI客服RAG知识库","CMS内容管理","完整电商商城(商品/购物车/订单/支付)","1688供应链对接(采集→AI优化→商城发布)","知识库+RAG检索","AI持续SEO+排名跟踪","用户画像+分析报告","赠送¥80 AI金(额度,用尽可自购)","小程序增值入口(定制费另计)"]', 2);
                INSERT OR IGNORE INTO subscription_plans (plan_key, name, description, price_month, price_year, trial_days, tier, features_json, sort_order) VALUES
                    ('deploy_enterprise', '企业版', '品牌企业全链路AI运营', 69900, 699900, 0, 'premium', '["AI智能建站","AI高级客服(多轮对话+CRM+飞书通知)","AI内容工厂(RSS→AI加工→CMS→社媒推送)","Agent矩阵(1+12智能体协作)","1688批量供应链管理+自动铺货","社媒自动发布(微信/微博/头条/抖音)","云服务自动开通","12维用户画像+意向分级","数据看板+AI洞察报告","月度巡检+专属客服","赠送¥120 AI金(额度,用尽可自购)","小程序增值入口(定制费另计)"]', 3);
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id             INTEGER NOT NULL UNIQUE,
                    plan_key            TEXT NOT NULL,
                    period              TEXT NOT NULL,
                    status              TEXT NOT NULL DEFAULT 'active',
                    current_period_start TEXT NOT NULL,
                    current_period_end   TEXT NOT NULL,
                    trial_end           TEXT,
                    canceled_at         TEXT,
                    cancel_reason       TEXT DEFAULT '',
                    cancel_feedback     TEXT DEFAULT '',
                    auto_renew          INTEGER DEFAULT 1,
                    payment_method      TEXT,
                    alipay_agreement_id TEXT,
                    wechat_contract_id  TEXT,
                    pending_plan_key    TEXT,
                    pending_period      TEXT,
                    pending_at          TEXT,
                    created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS subscription_orders (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_no        TEXT UNIQUE NOT NULL,
                    user_id         INTEGER NOT NULL,
                    sub_id          INTEGER REFERENCES subscriptions(id),
                    amount_fen      INTEGER NOT NULL,
                    currency        TEXT DEFAULT 'CNY',
                    item_type       TEXT NOT NULL,
                    plan_key        TEXT NOT NULL,
                    period          TEXT NOT NULL,
                    payment_method  TEXT,
                    channel_order_id TEXT,
                    status          TEXT NOT NULL DEFAULT 'pending',
                    paid_at         TEXT,
                    fail_reason     TEXT,
                    notify_id       TEXT,
                    notify_raw      TEXT,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sub_orders_user ON subscription_orders(user_id);
                CREATE INDEX IF NOT EXISTS idx_sub_orders_status ON subscription_orders(status);
                CREATE INDEX IF NOT EXISTS idx_sub_orders_notify ON subscription_orders(notify_id);
                CREATE TABLE IF NOT EXISTS payment_events (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL,
                    sub_id          INTEGER REFERENCES subscriptions(id),
                    event_type      TEXT NOT NULL,
                    channel         TEXT NOT NULL,
                    channel_event_id TEXT,
                    amount_fen      INTEGER,
                    result          TEXT,
                    fail_reason     TEXT,
                    raw_response    TEXT,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_pay_events_sub ON payment_events(sub_id);

                CREATE TABLE IF NOT EXISTS subscription_audit_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL,
                    sub_id          INTEGER,
                    action          TEXT NOT NULL,
                    detail          TEXT,
                    ip_address      TEXT,
                    admin_id        INTEGER,
                    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sub_audit_user ON subscription_audit_log(user_id);
            ''')
            cs.commit()
        conn.commit()
    # ── 品牌设置字段迁移：logo_url → logo_full_url + 新增 logo_icon_url ──
    with get_db() as bm:
        try:
            bm.execute("ALTER TABLE brand_settings ADD COLUMN logo_full_url TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            bm.execute("ALTER TABLE brand_settings ADD COLUMN logo_icon_url TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        bm.execute("UPDATE brand_settings SET logo_full_url = logo_url WHERE logo_full_url = '' AND logo_url != ''")
        bm.commit()
    # ── 品牌设置字段迁移：新增 company_name / tagline / icp / security / contact_email ──
    with get_db() as bm:
        for col, default_val in [
            ('company_name',   "''"),
            ('tagline',         "''"),
            ('icp_number',      "''"),
            ('security_number', "''"),
            ('contact_email',   "''"),
        ]:
            try:
                bm.execute(f"ALTER TABLE brand_settings ADD COLUMN {col} TEXT NOT NULL DEFAULT {default_val}")
            except sqlite3.OperationalError:
                pass
        bm.commit()
    # ── Migration: brand_settings site_domain ──
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(brand_settings)').fetchall()]
        if 'site_domain' not in cols:
            m.execute("ALTER TABLE brand_settings ADD COLUMN site_domain TEXT NOT NULL DEFAULT ''")
            m.commit()
            print('[Migration] brand_settings.site_domain added')
    # ── Migration: migrate users.agent_id → user_agents (2026-05-10) ──
    with get_db() as m:
        # Check if legacy agent_id column exists in users table
        user_cols = [c['name'] for c in m.execute('PRAGMA table_info(users)').fetchall()]
        has_legacy_agent = 'agent_id' in user_cols
        
        if has_legacy_agent:
            count = m.execute('SELECT COUNT(*) as c FROM user_agents').fetchone()
            if count['c'] == 0:
                rows = m.execute(
                    "SELECT id, agent_id, agent_nickname, agent_avatar_url, display_name "
                    "FROM users WHERE agent_id IS NOT NULL AND agent_id != ''"
                ).fetchall()
                migrated = 0
                for r in rows:
                    agent_name = r['agent_nickname'] or r['display_name'] or f"agent_{r['id']}"
                    m.execute(
                        "INSERT OR IGNORE INTO user_agents "
                        "(user_id, agent_name, agent_type, avatar_url, status, created_at) "
                        "VALUES (?, ?, 'personal', ?, 'active', datetime('now'))",
                        (r['id'], agent_name, r['agent_avatar_url'] or '')
                    )
                    migrated += 1
                if migrated:
                    m.commit()
                    print(f'[Migration] {migrated} user agents created from legacy agent_id')
                else:
                    print('[Migration] No legacy user agent data to migrate')
        else:
            print('[Migration] No legacy agent_id column — skipping migration')
        
        # Add agent_id FK column to api_keys if not present
        cols = [c['name'] for c in m.execute('PRAGMA table_info(api_keys)').fetchall()]
        if 'associated_agent_id' not in cols:
            try:
                m.execute('ALTER TABLE api_keys ADD COLUMN associated_agent_id INTEGER DEFAULT 0')
                m.commit()
                print('[Migration] api_keys.associated_agent_id added')
            except Exception:
                pass
    
    # Migration: add agent_avatar_url if missing
    with get_db() as m:
        # Also ensure admin_profiles users have is_admin=1
        m.execute(
            "UPDATE users SET is_admin=1 WHERE id IN ("
            "  SELECT user_id FROM admin_profiles"
            ") AND is_admin=0"
        )
        m.commit()
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(users)').fetchall()]
        if 'agent_avatar_url' not in cols:
            m.execute('ALTER TABLE users ADD COLUMN agent_avatar_url TEXT DEFAULT \'\'')
            m.commit()
            print('[Migration] agents.agent_avatar_url added')

    # ── IAM v2 migration: add new columns (2026-05-11) ──
    with get_db() as m:
        cur = m.execute('PRAGMA table_info(users)')
        cols = [r['name'] for r in cur.fetchall()]
        if 'display_name' not in cols:
            for col_def in [
                ("display_name", "TEXT DEFAULT ''"),
                ("email_verified", "INTEGER DEFAULT 0"),
                ("password_changed_at", "TEXT"),
                ("totp_secret", "TEXT DEFAULT ''"),
                ("totp_enabled", "INTEGER DEFAULT 0"),
                ("security_level", "INTEGER DEFAULT 0"),
            ]:
                try:
                    m.execute(f"ALTER TABLE users ADD COLUMN {col_def[0]} {col_def[1]}")
                except Exception:
                    pass
            m.commit()
            print('[Migration] IAM v2 columns added to users table')
        # Backfill existing users
        m.execute("UPDATE users SET username = phone WHERE username IS NULL AND phone IS NOT NULL")
        m.execute("UPDATE users SET display_name = COALESCE(display_name, phone, 'User') WHERE display_name = '' OR display_name IS NULL")
        m.commit()
        print('[Migration] IAM v2 backfill complete')
    # ── Real-name verification migration v2 (2026-05-19) ──
    # 合规要求：不存储身份证号（明文或加密），只存认证状态标记
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(users)').fetchall()]
        # 保留旧字段以兼容，但不再写入 id_number_encrypted
        for col_name, col_def in [
            ('verified_by', "TEXT DEFAULT ''"),
            ('verified_at', "TEXT"),
            ('id_number_encrypted', "TEXT DEFAULT ''"),
            ('is_real_name_verified', "INTEGER DEFAULT 0"),
            ('real_name_verified_at', "TEXT"),
        ]:
            if col_name not in cols:
                try:
                    m.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass
        # 清空历史遗留的加密身份证号（合规要求：不存储）
        m.execute("UPDATE users SET id_number_encrypted = '' WHERE id_number_encrypted != ''")
        m.commit()
        print('[Migration] Real-name verification v2: is_real_name_verified + real_name_verified_at added, id_number_encrypted cleared')

    # ── Verification provider config seeds (admin fills in credentials later) ──
    with get_db() as m:
        provider_seeds = [
            ('verification.provider', 'alipay', '实名认证服务商: alipay / wechat / stub'),
            ('verification.alipay.app_id', '', '支付宝开放平台 App ID'),
            ('verification.alipay.private_key', '', '支付宝应用私钥 (PKCS8)'),
            ('verification.alipay.alipay_public_key', '', '支付宝公钥'),
            ('verification.alipay.auth_url', 'https://openapi.alipay.com/gateway.do', '支付宝网关地址'),
            ('verification.alipay.return_url', '', '认证完成后回跳URL'),
            ('verification.wechat.app_id', '', '微信开放平台 App ID'),
            ('verification.wechat.app_secret', '', '微信开放平台 App Secret'),
            ('verification.wechat.auth_url', 'https://api.weixin.qq.com/sns/oauth2/access_token', '微信OAuth地址'),
            ('verification.enabled', 'false', '是否启用第三方实名认证 (true/false)'),
            ('verification.stub_mode', 'true', '开发模式：true=跳过真实第三方调用，直接模拟通过'),
        ]
        for key, value, desc in provider_seeds:
            m.execute(
                "INSERT OR IGNORE INTO system_config (key, value, description) VALUES (?,?,?)",
                (key, value, desc)
            )
        m.commit()
        print('[Migration] Verification provider config seeds added')

    # ── Verification requests log table ──
    with get_db() as m:
        m.execute("""
            CREATE TABLE IF NOT EXISTS verification_requests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                request_id      TEXT UNIQUE NOT NULL,
                provider        TEXT NOT NULL DEFAULT '',
                return_url      TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                created_at      TEXT DEFAULT (datetime('now')),
                completed_at    TEXT
            )
        """)
        m.execute("CREATE INDEX IF NOT EXISTS idx_vr_request_id ON verification_requests(request_id)")
        m.execute("CREATE INDEX IF NOT EXISTS idx_vr_user_id ON verification_requests(user_id)")
        m.commit()

    # ── Migration: seed providers + provider_models (replaces model_providers) ──
    with get_db() as m:
        # Ensure new tables exist (CREATE TABLE IF NOT EXISTS handles fresh installs)
        # Ensure UNIQUE index to prevent duplicate model seeds
        m.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_pm_provider_model_unique ON provider_models(provider_id, model_name)')
        # Seed providers
        provider_seeds = [
            ('volcengine', '火山引擎', '语音合成、声音复刻、数字人视频'),
            ('dashscope',  '阿里云 DashScope', '通义千问、图像生成、CosyVoice'),
            ('deepseek',   'DeepSeek', '深度求索大语言模型'),
            ('openai',     'OpenAI', 'GPT-4o、DALL-E、TTS'),
            ('openrouter', 'OpenRouter', '多模型聚合路由'),
            ('ollama',     'Ollama', '本地开源模型部署'),
        ]
        for slug, name, desc in provider_seeds:
            m.execute(
                "INSERT OR IGNORE INTO providers (slug, name, description) VALUES (?,?,?)",
                (slug, name, desc)
            )
        # Resolve provider IDs
        pids = {slug: m.execute("SELECT id FROM providers WHERE slug=?", (slug,)).fetchone()['id']
                for slug, _, _ in provider_seeds}
        # Seed provider_models — 每个提供商下多个模型
        model_seeds = [
            # 火山引擎
            (pids['volcengine'], '声音复刻 v2',       'volc-voice-clone-v2',   'https://openspeech.bytedance.com/api/v1/mega_tts/audio',     'volcengine_credentials', 'voice',    1),
            (pids['volcengine'], '流式语音合成 TTS',   'volc-tts-stream',        'https://openspeech.bytedance.com/api/v1/tts',               'volcengine_credentials', 'tts',      2),
            (pids['volcengine'], '照片驱动数字人 v3',  'volc-avatar-v3',         'https://open.byteplus.com/api/v1/avatar',                    'volcengine_credentials', 'video',    3),
            # 阿里云 DashScope
            (pids['dashscope'],  '通义千问 Turbo',     'qwen-turbo',             'https://dashscope.aliyuncs.com/compatible-mode/v1',          'dashscope_text_key',    'text',     10),
            (pids['dashscope'],  '通义千问 Max',        'qwen-max',               'https://dashscope.aliyuncs.com/compatible-mode/v1',          'dashscope_text_key',    'text',     11),
            (pids['dashscope'],  '通义千问 Plus',       'qwen-plus',              'https://dashscope.aliyuncs.com/compatible-mode/v1',          'dashscope_text_key',    'text',     12),
            (pids['dashscope'],  '通义千问 2.5 72B',    'qwen2.5-72b-instruct',   'https://dashscope.aliyuncs.com/compatible-mode/v1',          'dashscope_text_key',    'text',     13),
            (pids['dashscope'],  'DeepSeek R1',          'deepseek-r1',            'https://dashscope.aliyuncs.com/compatible-mode/v1',          'dashscope_text_key',    'text',     14),
            (pids['dashscope'],  'DeepSeek V3',          'deepseek-v3',            'https://dashscope.aliyuncs.com/compatible-mode/v1',          'dashscope_text_key',    'text',     15),
            (pids['dashscope'],  '图像生成 Wan2.7',      'wan2.7-image',           'https://dashscope.aliyuncs.com/api/v1/services/aigc/image-generation/generation', 'dashscope_api_key', 'image', 20),
            (pids['dashscope'],  'CosyVoice 声音克隆',   'cosyvoice-v1',           'https://dashscope.aliyuncs.com/api/v1/services/audio/tts',  'dashscope_api_key',     'voice',    21),
            # DeepSeek
            (pids['deepseek'],   'DeepSeek Chat',       'deepseek-chat',          'https://api.deepseek.com/v1',                               'deepseek_api_key',      'text',     30),
            (pids['deepseek'],   'DeepSeek Reasoner',   'deepseek-reasoner',      'https://api.deepseek.com/v1',                               'deepseek_api_key',      'text',     31),
            # OpenAI
            (pids['openai'],     'GPT-4o',               'gpt-4o',                 'https://api.openai.com/v1',                                 'openai_api_key',        'text',     40),
            (pids['openai'],     'GPT-4o Mini',          'gpt-4o-mini',            'https://api.openai.com/v1',                                 'openai_api_key',        'text',     41),
            (pids['openai'],     'GPT-4 Turbo',          'gpt-4-turbo',            'https://api.openai.com/v1',                                 'openai_api_key',        'text',     42),
            (pids['openai'],     'DALL-E 3',             'dall-e-3',               'https://api.openai.com/v1',                                 'openai_api_key',        'image',    43),
            (pids['openai'],     'TTS-1',                'tts-1',                  'https://api.openai.com/v1',                                 'openai_api_key',        'voice',    44),
            # OpenRouter
            (pids['openrouter'], 'OpenAI GPT-4o',        'openai/gpt-4o',          'https://openrouter.ai/api/v1',                              'openrouter_api_key',    'text',     50),
            (pids['openrouter'], 'Claude Sonnet 4',      'anthropic/claude-sonnet-4','https://openrouter.ai/api/v1',                             'openrouter_api_key',    'text',     51),
            (pids['openrouter'], 'Claude 3 Opus',        'anthropic/claude-3-opus','https://openrouter.ai/api/v1',                              'openrouter_api_key',    'text',     52),
            (pids['openrouter'], 'Gemini 2.5 Pro',       'google/gemini-2.5-pro',  'https://openrouter.ai/api/v1',                              'openrouter_api_key',    'text',     53),
            (pids['openrouter'], 'Llama 4 Maverick',     'meta-llama/llama-4-maverick','https://openrouter.ai/api/v1',                           'openrouter_api_key',    'text',     54),
            # Ollama
            (pids['ollama'],     'Llama 3',              'llama3',                 'http://localhost:11434/v1',                                 '',                     'text',     60),
            (pids['ollama'],     'Qwen 2.5 14B',         'qwen2.5:14b',            'http://localhost:11434/v1',                                 '',                     'text',     61),
        ]
        for pid, name, model, url, key_ref, caps, sort in model_seeds:
            m.execute(
                "INSERT OR IGNORE INTO provider_models (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities, sort_order) VALUES (?,?,?,?,?,?,?)",
                (pid, name, model, url, key_ref, caps, sort)
            )
        m.commit()
        print('[Migration] Providers + provider_models seed data added')

    # ── Migration: add provider_model_id to agents table ──
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(agents)').fetchall()]
        if 'provider_model_id' not in cols:
            m.execute('ALTER TABLE agents ADD COLUMN provider_model_id INTEGER DEFAULT NULL')
            print('[Migration] Added agents.provider_model_id')
        # Migrate OLD model_provider_id → provider_model_id
        rows = m.execute(
            "SELECT id, model_provider_id FROM agents WHERE provider_model_id IS NULL AND model_provider_id IS NOT NULL"
        ).fetchall()
        for a in rows:
            m.execute("UPDATE agents SET provider_model_id=? WHERE id=?",
                      (a['model_provider_id'], a['id']))
        if rows:
            m.commit()
            print(f'[Migration] Migrated {len(rows)} agents from model_provider_id → provider_model_id')

        print('[Migration] verification_requests table created')

    # ── Migration: seed OpenRouter free models ──
    with get_db() as m:
        or_id = m.execute("SELECT id FROM providers WHERE slug='openrouter'").fetchone()
        if or_id:
            pid = or_id['id']
            or_free_models = [
                (pid, 'DeepSeek V4 Flash (免费)',   'deepseek/deepseek-v4-flash:free',                        'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 70),
                (pid, 'Llama 3.3 70B (免费)',       'meta-llama/llama-3.3-70b-instruct:free',               'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 71),
                (pid, 'Hermes 3 405B (免费)',        'nousresearch/hermes-3-llama-3.1-405b:free',            'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 72),
                (pid, 'Gemma 4 31B (免费)',          'google/gemma-4-31b-it:free',                            'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 73),
                (pid, 'Gemma 4 26B MoE (免费)',      'google/gemma-4-26b-a4b-it:free',                        'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 74),
                (pid, 'Qwen3 Next 80B (免费)',       'qwen/qwen3-next-80b-a3b-instruct:free',                 'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 75),
                (pid, 'Qwen3 Coder (免费)',          'qwen/qwen3-coder:free',                                 'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 76),
                (pid, 'Nemotron 3 Super 120B (免费)','nvidia/nemotron-3-super-120b-a12b:free',                'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 77),
                (pid, 'MiniMax M2.5 (免费)',         'minimax/minimax-m2.5:free',                             'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 78),
                (pid, 'GLM-4.5 Air (免费)',          'z-ai/glm-4.5-air:free',                                'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 79),
                (pid, 'GPT-OSS 120B (免费)',         'openai/gpt-oss-120b:free',                              'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 80),
                (pid, 'GPT-OSS 20B (免费)',          'openai/gpt-oss-20b:free',                               'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 81),
                (pid, 'CoBuddy 编程 (免费)',          'baidu/cobuddy:free',                                    'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 82),
                (pid, 'Trinity Large Thinking (免费)','arcee-ai/trinity-large-thinking:free',                'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 83),
                (pid, 'Nemotron Nano 30B (免费)',    'nvidia/nemotron-3-nano-30b-a3b:free',                  'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 84),
                (pid, 'Nemotron Nano Omni (免费)',   'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free',    'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 85),
                (pid, 'Nemotron Nano 9B V2 (免费)',  'nvidia/nemotron-nano-9b-v2:free',                       'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 86),
                (pid, 'Nemotron Nano 12B VL (免费)', 'nvidia/nemotron-nano-12b-v2-vl:free',                   'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 87),
                (pid, 'Llama 3.2 3B (免费)',         'meta-llama/llama-3.2-3b-instruct:free',                'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 88),
                (pid, 'Venice Uncensored (免费)',    'cognitivecomputations/dolphin-mistral-24b-venice-edition:free', 'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 89),
                (pid, 'LFM 2.5 Thinking (免费)',     'liquid/lfm-2.5-1.2b-thinking:free',                     'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 90),
                (pid, 'LFM 2.5 Instruct (免费)',     'liquid/lfm-2.5-1.2b-instruct:free',                     'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 91),
                (pid, 'Laguna XS.2 (免费)',          'poolside/laguna-xs.2:free',                             'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 92),
                (pid, 'Laguna M.1 (免费)',           'poolside/laguna-m.1:free',                              'https://openrouter.ai/api/v1', 'openrouter_api_key', 'text', 93),
            ]
            for pid_val, name, model, url, key_ref, caps, sort in or_free_models:
                m.execute(
                    "INSERT OR IGNORE INTO provider_models (provider_id, name, model_name, endpoint_url, api_key_ref, capabilities, sort_order) VALUES (?,?,?,?,?,?,?)",
                    (pid_val, name, model, url, key_ref, caps, sort)
                )
            m.commit()
            print('[Migration] OpenRouter free models seeded')

    # Check and add username_changed_at
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(users)').fetchall()]
        for col_name in ('username_changed_at',):
            if col_name not in cols:
                m.execute(f'ALTER TABLE users ADD COLUMN {col_name} TEXT')
                m.commit()
                print(f'[Migration] users.{col_name} added')

    # Migration: add social_links.platform column (2026-05-14)
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(social_links)').fetchall()]
        if 'platform' not in cols:
            m.execute("ALTER TABLE social_links ADD COLUMN platform TEXT NOT NULL DEFAULT ''")
            m.commit()
            print('[Migration] social_links.platform added')

    # ── channel_configs: 频道管理（飞书/微信/QQ/钉钉）──
    with get_db() as m:
        m.execute("""
            CREATE TABLE IF NOT EXISTS channel_configs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                channel         TEXT NOT NULL UNIQUE,
                config_json     TEXT NOT NULL DEFAULT '{}',
                is_enabled      INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        # seed feishu record if not exists
        existing = m.execute("SELECT id FROM channel_configs WHERE channel='feishu'").fetchone()
        if not existing:
            import os as _os
            m.execute(
                "INSERT INTO channel_configs (channel, config_json, is_enabled) VALUES ('feishu', ?, 1)",
                ('{}',)
            )
            m.commit()
            print('[Migration] channel_configs table + feishu seed created')

        # seed wecom record if not exists
        existing_wecom = m.execute("SELECT id FROM channel_configs WHERE channel='wecom'").fetchone()
        if not existing_wecom:
            m.execute(
                "INSERT INTO channel_configs (channel, config_json, is_enabled) VALUES ('wecom', '{}', 1)"
            )
            m.commit()
            print('[Migration] channel_configs wecom seed created')

        # seed qq record if not exists
        existing_qq = m.execute("SELECT id FROM channel_configs WHERE channel='qq'").fetchone()
        if not existing_qq:
            m.execute(
                "INSERT INTO channel_configs (channel, config_json, is_enabled) VALUES ('qq', '{}', 0)"
            )
            m.commit()
            print('[Migration] channel_configs qq seed created')

        # seed dingtalk record if not exists
        existing_dingtalk = m.execute("SELECT id FROM channel_configs WHERE channel='dingtalk'").fetchone()
        if not existing_dingtalk:
            m.execute(
                "INSERT INTO channel_configs (channel, config_json, is_enabled) VALUES ('dingtalk', '{}', 0)"
            )
            m.commit()
            print('[Migration] channel_configs dingtalk seed created')

    # ── Payment / Third-party config seeds (admin fills in credentials later) ──
    with get_db() as m:
        payment_seeds = [
            # 支付回调域名
            ('payment.notify_base',           '',    '支付回调通知域名 (如 https://your-domain.com)'),
            # 支付宝商城支付（payment_service.py 使用，无点前缀）
            ('alipay_app_id',                 '',    '支付宝 App ID（商城支付）'),
            ('alipay_private_key',            '',    '支付宝应用私钥 PKCS8（商城支付）'),
            ('alipay_public_key',             '',    '支付宝公钥（商城支付）'),
            # 微信支付
            ('wechat_app_id',                 '',    '微信支付 AppID（公众号/小程序 AppID）'),
            ('wechat_mchid',                  '',    '微信支付商户号'),
            ('wechat_api_v3_key',             '',    '微信支付 API v3 密钥'),
            ('wechat_cert_serial',            '',    '微信支付证书序列号'),
            ('wechat_plan_id',                '',    '微信支付扣费计划ID'),
            # 快递鸟物流（kdniao_service.py 读取）
            ('kdniao_eid',                    '',    '快递鸟商户ID (EBusinessID)'),
            ('kdniao_api_key',                '',    '快递鸟 API Key'),
        ]
        for key, value, desc in payment_seeds:
            m.execute(
                "INSERT OR IGNORE INTO system_config (key, value, description) VALUES (?,?,?)",
                (key, value, desc)
            )
        m.commit()
        print('[Migration] Payment/third-party config seeds added')

    # ── Shop AI 商城商品优化配置 ──
    with get_db() as m:
        shop_ai_seeds = [
            ('shop_ai_provider',                'deepseek',     '商城AI商品优化 — 供应商 (deepseek/dashscope/openai/openrouter/siliconflow/ollama)'),
            ('shop_ai_model',                   'deepseek-chat','商城AI商品优化 — 模型名 (如 deepseek-chat, qwen-max, gpt-4o-mini)'),
        ]
        for key, value, desc in shop_ai_seeds:
            m.execute(
                "INSERT OR IGNORE INTO system_config (key, value, description) VALUES (?,?,?)",
                (key, value, desc)
            )
        m.commit()
        print('[Migration] Shop AI config seeds added')

    # ── cluster_services: 站群服务管理 ──
    with get_db() as m2:
        m2.execute("""
            CREATE TABLE IF NOT EXISTS cluster_services (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name    TEXT NOT NULL UNIQUE,
                display_name    TEXT NOT NULL,
                domain          TEXT NOT NULL,
                port            INTEGER NOT NULL,
                health_url      TEXT DEFAULT '/health',
                manager_type    TEXT NOT NULL DEFAULT 'tmux',
                manager_name    TEXT NOT NULL,
                workdir         TEXT,
                start_cmd       TEXT,
                sort_order      INTEGER DEFAULT 0,
                is_enabled      INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        m2.commit()
    # ── Notification System: templates + logs tables ──
    with get_db() as m:
        m.execute("""
            CREATE TABLE IF NOT EXISTS notification_templates (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type          TEXT NOT NULL UNIQUE,
                title_template      TEXT NOT NULL,
                content_template    TEXT NOT NULL,
                link_url_template   TEXT DEFAULT '',
                type                TEXT NOT NULL DEFAULT 'system',
                is_active           INTEGER DEFAULT 1,
                sort_order          INTEGER DEFAULT 0,
                created_at          TEXT DEFAULT (datetime('now')),
                updated_at          TEXT DEFAULT (datetime('now'))
            )
        """)
        m.execute("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id     INTEGER DEFAULT NULL,
                user_id         INTEGER REFERENCES users(id),
                event_type      TEXT DEFAULT '',
                notification_id INTEGER DEFAULT NULL,
                result          TEXT DEFAULT 'success',
                error_msg       TEXT DEFAULT '',
                sent_at         TEXT DEFAULT (datetime('now'))
            )
        """)
        m.execute("CREATE INDEX IF NOT EXISTS idx_notif_logs_user ON notification_logs(user_id)")
        m.execute("CREATE INDEX IF NOT EXISTS idx_notif_logs_template ON notification_logs(template_id)")
        m.commit()
    # Migration: add read_at + extra_data to user_notifications
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(user_notifications)').fetchall()]
        if 'read_at' not in cols:
            m.execute("ALTER TABLE user_notifications ADD COLUMN read_at TEXT DEFAULT NULL")
        if 'extra_data' not in cols:
            m.execute("ALTER TABLE user_notifications ADD COLUMN extra_data TEXT DEFAULT '{}'")
        m.commit()
        print('[Migration] user_notifications: read_at + extra_data added')

    # ── Migration: completion_percentage on users ──
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(users)').fetchall()]
        if 'completion_percentage' not in cols:
            m.execute("ALTER TABLE users ADD COLUMN completion_percentage INTEGER DEFAULT 0")
        if 'completion_last_updated' not in cols:
            m.execute("ALTER TABLE users ADD COLUMN completion_last_updated TEXT")
        m.commit()
        print('[Migration] users: completion_percentage + completion_last_updated added')

    # ── Reward rules + claims tables ──
    with get_db() as m:
        m.execute("""
            CREATE TABLE IF NOT EXISTS reward_rules (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                condition_key   TEXT NOT NULL,
                condition_value TEXT NOT NULL,
                reward_type     TEXT NOT NULL DEFAULT 'coupon',
                reward_id       INTEGER DEFAULT NULL,
                reward_name     TEXT DEFAULT '',
                sort_order      INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        m.execute("""
            CREATE TABLE IF NOT EXISTS reward_claims (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER REFERENCES users(id),
                rule_id     INTEGER NOT NULL,
                claimed_at  TEXT DEFAULT (datetime('now')),
                coupon_id   INTEGER DEFAULT NULL,
                UNIQUE(user_id, rule_id)
            )
        """)
        m.execute("CREATE INDEX IF NOT EXISTS idx_reward_claims_user ON reward_claims(user_id)")
        m.execute("CREATE INDEX IF NOT EXISTS idx_reward_claims_rule ON reward_claims(rule_id)")
        m.commit()
        print('[Migration] reward_rules + reward_claims tables created')

    # ── Interests + user_interests tables ──
    with get_db() as m:
        m.executescript("""
            CREATE TABLE IF NOT EXISTS interests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                category    TEXT NOT NULL,
                sort_order  INTEGER DEFAULT 0,
                is_hot      INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS user_interests (
                user_id     INTEGER NOT NULL,
                interest_id INTEGER NOT NULL,
                created_at  TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, interest_id),
                FOREIGN KEY (interest_id) REFERENCES interests(id) ON DELETE CASCADE
            );
        """)
        m.execute("CREATE INDEX IF NOT EXISTS idx_user_interests_user ON user_interests(user_id)")
        m.execute("CREATE INDEX IF NOT EXISTS idx_interests_category ON interests(category, sort_order)")
        m.commit()
        print('[Migration] interests + user_interests tables created')

    # ── Seed default interest tags ──
    with get_db() as m:
        existing = m.execute("SELECT COUNT(*) FROM interests").fetchone()[0]
        if existing < 10:
            tags = _get_default_interests()
            m.executemany(
                "INSERT OR IGNORE INTO interests (name, category, sort_order, is_hot) VALUES (?,?,?,?)",
                tags
            )
            m.commit()
            print(f'[Migration] {len(tags)} interest tags seeded')

    # ── Seed notification templates ──
    with get_db() as m:
        templates = [
            ('user.realname_verified',      '实名认证通过',   '恭喜您已通过实名认证，解锁全部功能权益。',                                                          '',                   'reward', 1, 1),
            ('user.profile_completion.100',  '资料完成度100%', '您已完成全部个人资料填写，获得专属福利！',                                                            '',                   'reward', 2, 2),
            ('user.phone_verified',          '手机验证成功',   '您已成功验证手机号，账户安全等级已提升。',                                                            '',                   'system', 3, 3),
            ('reward.issued',               '获得奖励',       '恭喜您获得 {reward_name}！请前往优惠券中心查看。',                                               '',                   'reward', 4, 4),
            ('referral.referee_registered', '邀请成功',       '恭喜邀请成功！您的好友 {friend_name} 已注册，奖励已发放。',                                      '',                   'reward', 5, 5),
            ('referral.referee_completed_action', '好友完成首单', '您的好友 {friend_name} 已完成首次操作，您的推广奖励已到账。',                                '',                   'reward', 6, 6),
            ('coupon.expiring',             '优惠券即将过期', '您有一张 {coupon_name} 即将在 {expire_days} 天后过期，请尽快使用。',                         '',                   'promo',  7, 7),
        ]
        for t in templates:
            existing = m.execute("SELECT id FROM notification_templates WHERE event_type=?", (t[0],)).fetchone()
            if not existing:
                m.execute(
                    "INSERT INTO notification_templates (event_type, title_template, content_template, link_url_template, type, sort_order, is_active) VALUES (?,?,?,?,?,?,?)",
                    t
                )
        m.commit()
        print('[Migration] notification templates seeded')

        # ── Migration: ad_placements table (2026-05-20) ──
        m.execute('''CREATE TABLE IF NOT EXISTS ad_placements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            position        TEXT NOT NULL DEFAULT 'sidebar',
            page            TEXT NOT NULL DEFAULT '*',
            ad_type         TEXT NOT NULL DEFAULT 'image',
            image_url       TEXT DEFAULT '',
            link_url        TEXT DEFAULT '',
            ad_code         TEXT DEFAULT '',
            width           INTEGER DEFAULT 320,
            height          INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            sort_order      INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_ad_page ON ad_placements(page, position)')
        m.commit()
        print('[Migration] ad_placements table created')

    # ── Migration: voice_templates + video_tasks (口播视频 — 2026-05-22) ──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS voice_templates (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL DEFAULT 1,
            name                TEXT NOT NULL,
            sample_url          TEXT DEFAULT '',
            external_voice_id   TEXT DEFAULT '',
            provider            TEXT DEFAULT 'volcengine',
            provider_model_id   INTEGER DEFAULT NULL,
            status              TEXT DEFAULT 'pending',
            duration_seconds    REAL DEFAULT 0,
            error_msg           TEXT DEFAULT '',
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_vt_status ON voice_templates(status)')
        m.execute('''CREATE TABLE IF NOT EXISTS video_tasks (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL DEFAULT 1,
            title               TEXT NOT NULL,
            voice_template_id   INTEGER DEFAULT NULL,
            text_content        TEXT NOT NULL,
            avatar_image_url    TEXT DEFAULT '',
            output_url          TEXT DEFAULT '',
            provider            TEXT DEFAULT 'volcengine',
            provider_model_id   INTEGER DEFAULT NULL,
            external_task_id    TEXT DEFAULT '',
            status              TEXT DEFAULT 'pending',
            error_msg           TEXT DEFAULT '',
            published_douyin    INTEGER DEFAULT 0,
            douyin_video_id     TEXT DEFAULT '',
            is_homepage         INTEGER DEFAULT 0,
            media_type          TEXT DEFAULT 'avatar_video',
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_vdt_status ON video_tasks(status)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_vdt_homepage ON video_tasks(is_homepage)')
        m.commit()
        print('[Migration] voice_templates + video_tasks tables created')

    # ── Migration: media_files table（本地媒体库 — 2026-05-24）──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS media_files (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            filename        TEXT NOT NULL,
            original_name   TEXT NOT NULL,
            mime_type       TEXT NOT NULL DEFAULT 'application/octet-stream',
            file_size       INTEGER DEFAULT 0,
            file_path       TEXT NOT NULL,
            thumb_path      TEXT DEFAULT '',
            push_status     TEXT DEFAULT 'none',
            push_target     TEXT DEFAULT '',
            pushed_at       TEXT DEFAULT NULL,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_mf_push_status ON media_files(push_status)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_mf_created ON media_files(created_at)')
        m.commit()
        print('[Migration] media_files table created')
    # ── Migration: knowledge_blocks table（RAG知识库 — 2026-06-10）──
    with get_db() as m:
        m.execute("""CREATE TABLE IF NOT EXISTS knowledge_blocks (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            content         TEXT NOT NULL,
            keywords        TEXT DEFAULT '',
            category        TEXT DEFAULT '',
            priority        INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        )""")
        m.execute('CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_blocks(category)')
        # Seed knowledge blocks from mini-program
        row = m.execute("SELECT COUNT(*) as c FROM knowledge_blocks").fetchone()
        if row['c'] == 0:
            kb_seeds = [
                ('kb_company_001','公司基本信息','Demo Company，位于示例地址。服务热线：400-000-0000，工作时间：周一至周五 9:00-18:00。','公司,地址,电话,邮箱,联系方式,工作时间','company',10),
                ('kb_company_002','公司定位与愿景','本平台由专业团队研发，定位为AI驱动的企业智能运营平台。公司愿景是通过AI技术降低企业运营门槛，助力中小企业数字化转型。','定位,愿景,使命,AI驱动,企业运营,数字化转型,中小企业','company',8),
                ('kb_product_001','平台概述','企业智能运营平台，核心功能包括：AI智能体社区、自动生成文案/图片/SEO、可视化搭建工作流、多端适配等。','平台,概述,功能,智能体,工作流,多端适配','product',10),
                ('kb_product_002','AI智能体社区','AI智能体社区是核心模块，内置多种AI助手：SEO优化助手、文案生成助手、图片设计助手、数据分析助手、客服助手等。每个智能体专注于特定任务。','智能体,AI助手,SEO,文案,图片,数据分析,客服,协作','product',9),
                ('kb_product_003','AI内容工厂','AI内容工厂可自动生成运营所需的各类内容：产品描述文案、企业介绍、新闻资讯、SEO优化文章、营销配图、Banner广告图等。支持批量生成和人工微调。','内容工厂,文案生成,图片生成,SEO文章,批量生成,Banner','product',9),
                ('kb_product_004','智能工作流引擎','智能工作流引擎提供可视化拖拽式页面搭建体验，无需编程即可完成页面配置。支持组件库、页面模板、样式自定义、实时预览等功能。','工作流,拖拽,可视化,组件,模板,预览','product',9),
                ('kb_product_005','多端适配能力','支持一次搭建、多端发布：PC网站、移动H5、微信小程序、抖音小程序、支付宝小程序等。自动适配不同终端的屏幕尺寸和交互方式。','多端,适配,PC,H5,小程序,响应式,跨平台','product',8),
                ('kb_price_001','价格体系概述','平台提供灵活的定价方案：基础版适合个人/初创企业，专业版适合中小企业，企业版适合大型企业。具体价格请咨询客服获取最新报价。','价格,多少钱,费用,报价,定价,收费,套餐,基础版,专业版,企业版','price',10),
                ('kb_price_002','基础版方案','基础版适合个人或初创企业，包含基础功能搭建、页面上限、基础SEO优化、响应式适配。价格亲民，是入门的最佳选择。','基础版,入门,个人,初创,便宜,低价','price',8),
                ('kb_price_003','专业版方案','专业版适合中小企业，包含企业级功能搭建、AI内容工厂、SEO深度优化、数据分析看板、多端适配。性价比最高，适合有线上运营需求的企业。','专业版,中小企业,性价比,营销,SEO深度','price',8),
                ('kb_price_004','企业版方案','企业版适合大型企业/集团，包含全部功能、定制化开发、专属客服、API接口对接、技术支持。适合有复杂定制需求的大型组织。','企业版,大型企业,定制,API,专属客服','price',8),
                ('kb_tech_001','AI技术优势','平台采用最新大语言模型技术，结合自研的运营领域知识图谱，实现智能化的系统配置。AI可理解用户需求描述，自动推荐合适的方案、布局和内容配置。','AI技术,大模型,知识图谱,智能推荐,技术优势','tech',8),
                ('kb_tech_002','部署说明','平台支持多种部署方式，签约后客户可获得完整的部署方案。交付物包含前端代码、后端接口、数据库脚本等，客户可自行部署和二次开发。','部署,交付,代码,二次开发,前端,后端,数据库','tech',9),
                ('kb_tech_003','安全与性能','平台采用HTTPS加密传输、数据备份、DDoS防护等安全措施。网站性能方面：CDN加速、图片懒加载、代码压缩、缓存策略等，确保网站加载速度快、运行稳定。','安全,性能,HTTPS,备份,CDN,加速,加载速度,稳定,防护','tech',7),
                ('kb_service_001','合作流程','合作流程：1.需求沟通（了解您的业务需求和预算）；2.方案定制（AI生成个性化方案）；3.合同签订（明确交付内容和时间节点）；4.开发搭建（AI+人工协作高效交付）；5.验收上线（测试通过后正式发布）；6.售后维护（持续技术支持）。','流程,合作,步骤,需求,方案,合同,开发,验收,售后,维护','service',9),
                ('kb_service_002','售后服务','平台提供完善的售后服务：免费维护期、7×24小时技术支持、定期系统更新、紧急故障2小时响应、免费培训。维护期后可续费延长。','售后,维护,技术支持,更新,故障,培训,续费,服务','service',8),
                ('kb_service_003','行业解决方案','针对不同行业提供专属解决方案：电商零售（商品展示+在线支付）、教育培训（课程展示+在线报名）、餐饮美食（菜单展示+外卖对接）、企业服务（品牌展示+线索收集）、房地产（楼盘展示+VR看房）等。','行业,解决方案,电商,教育,餐饮,企业服务,房地产,VR看房,外卖','service',8),
                ('kb_faq_001','搭建需要多长时间','展示型页面最快1天即可上线，企业官网通常3-5个工作日，含综合方案约7-10个工作日。具体时间取决于需求复杂度和定制化程度。','时间,多久,周期,上线,工作日,快速,几天','faq',9),
                ('kb_faq_002','是否需要技术基础','平台采用可视化拖拽操作，无需编程基础即可使用。AI助手会引导您完成每一步操作。如果有特殊定制需求，技术支持团队会提供专业支持。','技术基础,编程,代码,不会,简单,操作,难不难,容易','faq',9),
                ('kb_faq_003','是否支持SEO优化','平台内置SEO优化功能，AI可自动生成TDK（标题、描述、关键词）、优化页面结构、生成sitemap、配置301重定向等。同时提供SEO分析报告和改进建议。','SEO,优化,搜索引擎,排名,TDK,sitemap,百度,Google','faq',8),
                ('kb_faq_004','域名和服务器说明','平台可协助客户完成域名注册和服务器配置。客户可使用自有域名，也可通过平台代购。服务器采用云部署方案，自动扩容，保障稳定运行。域名和服务器费用不包含在套餐内。','域名,服务器,云部署,扩容,注册,代购,备案','faq',7),
            ]
            for s in kb_seeds:
                m.execute('INSERT OR IGNORE INTO knowledge_blocks (id,title,content,keywords,category,priority) VALUES (?,?,?,?,?,?)', s)
            m.commit()
            print(f'[Migration] knowledge_blocks seeded: {len(kb_seeds)} blocks')

    # ── Migration: seed FAQ and white paper from community/ (2026-06-11) ──
    with get_db() as ms:
        # Only seed if fewer than 25 entries (commercial FAQ not yet seeded)
        cnt = ms.execute("SELECT COUNT(*) as c FROM knowledge_blocks").fetchone()
        if cnt['c'] < 25:
            faq_seeds_data = [
                ('kb_faq_faq_p1', '你们的产品有哪些功能？', 'VeroRun(RuiCe AI)是生成式AI平台，支持智能对话（多模型）、AI建站、AI内容生成、数据清洗、知识库管理等。具体可查看官网产品页面或试用体验。', '功能,产品,能力,特性', 'faq', 6),
                ('kb_faq_faq_p2', '支持哪些AI模型？', '我们通过 Agent Matrix 体系支持多种AI模型，包括 DeepSeek（推荐）、阿里通义千问、以及 OpenAI 兼容接口。模型选择可在系统设置中配置。', '模型,AI,DeepSeek,千问,OpenAI', 'tech', 6),
                ('kb_faq_faq_p3', '怎么收费？有哪些套餐？', '我们提供基础版(¥299/月)、专业版(¥899/月)、企业版(¥2999/月)三档套餐。每个套餐赠送不同额度的API调用量。具体价格请查看官网定价页面或联系商务获取最新报价。', '价格,多少钱,费用,报价,收费,套餐,月付', 'price', 7),
                ('kb_faq_faq_p4', '有免费试用吗？', '是的！新用户注册即享免费体验额度。无需绑定支付方式即可试用。基础版可免费使用部分核心功能。', '免费,试用,体验,测试', 'price', 7),
                ('kb_faq_faq_p5', '如何注册账号？', '访问官网点击注册，填写用户名和密码即可完成注册。注册后即可使用免费额度体验平台功能。', '注册,账号,登录,开通', 'service', 7),
                ('kb_faq_faq_p6', '支持API接入吗？', '支持标准 OpenAI 兼容 API 接口。在后台管理控制台中生成 API Key 后即可调用。', 'API,接入,对接,接口,开发', 'tech', 6),
                ('kb_faq_faq_a1', '回复很慢怎么办？', '回复速度受模型负载和网络影响。建议：1）检查网络连接 2）避开高峰期使用 3）尝试切换模型。如持续异常，请提交工单。', '慢,卡,延迟,响应速度', 'service', 5),
                ('kb_faq_faq_a2', '对话记录在哪里查看？', '登录用户控制台，在「对话历史」中可以查看和搜索所有历史对话记录。', '记录,历史,对话,查看,搜索', 'service', 5),
                ('kb_faq_faq_a4', '忘记密码了怎么办？', '在登录页面点击「忘记密码」，输入注册时绑定的信息即可重置密码。如未绑定，请联系客服协助处理。', '密码,忘记,重置,找回', 'service', 6),
                ('kb_faq_faq_o2', '数据安全吗？隐私如何保护？', '我们高度重视数据安全：对话内容加密传输和存储，不会用于模型训练，用户可随时管理自己的数据。详细请查看官网法律声明。', '安全,隐私,数据,加密,保护', 'company', 7),
                ('kb_faq_whitepaper', 'VeroRun白皮书', 'VeroRun(RuiCe AI)是新一代AI驱动的智能建站与企业数字化平台。系统集成了AI聊天机器人、知识库管理（RAG）、数据清洗、内容工厂、CMS门户、订阅计费、多站点管理等完整功能。核心优势：AI原生架构、一体化SSO、开箱即用支付、强大的后台管理和灵活的主题系统。', '白皮书,产品介绍,技术架构,AI建站,功能概述', 'company', 10),
                ('kb_faq_whitepaper_tech', '技术架构说明', '系统采用Python 3.12 + Flask多服务微架构，SQLite (WAL模式)数据库，Vanilla JS SPA前端。支持SSO统一登录、多种支付网关、SSE流式对话、RAG知识库检索、Agent矩阵智能体编排等核心技术。', '技术,架构,Flask,Python,SSO,支付', 'tech', 8),
            ]
            for s in faq_seeds_data:
                ms.execute('INSERT OR IGNORE INTO knowledge_blocks (id,title,content,keywords,category,priority) VALUES (?,?,?,?,?,?)', s)
            ms.commit()
            print(f'[Migration] FAQ & whitepaper seeded: {len(faq_seeds_data)} blocks')

    # ── Migration: knowledge_queue（数据清洗 — 2026-06-10）──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS knowledge_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source          TEXT DEFAULT 'manual',
            raw_content     TEXT NOT NULL,
            status          TEXT DEFAULT 'pending',
            cleaned_id      TEXT,
            error_msg       TEXT DEFAULT '',
            admin_id        INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_kq_status ON knowledge_queue(status)')
        m.commit()
        print('[Migration] knowledge_queue table created')

    # ── Migration: shop tables（商城 — 2026-06-10）──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            subtitle        TEXT DEFAULT '',
            product_type    TEXT NOT NULL DEFAULT 'service',
                        -- vip/template/token/service/plugin
            category        TEXT DEFAULT '',
            price           REAL NOT NULL DEFAULT 0,
            original_price  REAL DEFAULT 0,
            stock           INTEGER DEFAULT 0,
            sales_count     INTEGER DEFAULT 0,
            thumbnail       TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            features        TEXT DEFAULT '[]',
            ai_config       TEXT DEFAULT '{}',
            sort_order      INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            updated_at      TEXT DEFAULT (datetime('now','localtime'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_products_type ON products(product_type)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active)')
        m.execute('''CREATE TABLE IF NOT EXISTS carts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            product_id      INTEGER NOT NULL REFERENCES products(id),
            quantity        INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(user_id, product_id)
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_carts_user ON carts(user_id)')
        m.execute('''CREATE TABLE IF NOT EXISTS user_purchases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            product_id      INTEGER NOT NULL REFERENCES products(id),
            order_id        TEXT DEFAULT '',
            purchase_type   TEXT NOT NULL DEFAULT 'once',
                        -- once / subscription
            expire_at       TEXT,
            status          TEXT DEFAULT 'active',
                        -- active / expired / cancelled
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_up_user ON user_purchases(user_id)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_up_status ON user_purchases(status)')

        m.execute('''CREATE TABLE IF NOT EXISTS order_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        TEXT NOT NULL,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            product_id      INTEGER NOT NULL REFERENCES products(id),
            product_title   TEXT NOT NULL DEFAULT '',
            quantity        INTEGER DEFAULT 1,
            unit_price      REAL NOT NULL DEFAULT 0,
            subtotal        REAL NOT NULL DEFAULT 0,
            coupon_id       INTEGER DEFAULT NULL,
            discount        REAL DEFAULT 0,
            status          TEXT DEFAULT 'pending',
                        -- pending / paid / refunded
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            paid_at         TEXT
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_oi_order ON order_items(order_id)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_oi_user ON order_items(user_id)')
        m.commit()
        print('[Migration] shop tables created (products/carts/user_purchases/coupons/order_items)')

    # ── Migration: order_items idempotency_key ──
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(order_items)').fetchall()]
        if 'idempotency_key' not in cols:
            try:
                m.execute("ALTER TABLE order_items ADD COLUMN idempotency_key TEXT DEFAULT ''")
                m.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_oi_idempotency ON order_items(idempotency_key) WHERE idempotency_key != \'\'')
                m.commit()
                print('[Migration] order_items.idempotency_key added')
            except Exception as e:
                print(f'[Migration] idempotency_key migration skipped: {e}')

    # ── Migration: seed extra themes (light/nature/warm/ocean) ──
    with get_db() as m:
        theme_seeds = [
            ('light', '纯净白', '1.0.0', '',
             '纯净白色风格 — 适合教育、咨询、法律服务。干净、通透、可信赖。',
             'education', '["light","clean","professional","education"]'),
            ('nature', '自然绿', '1.0.0', '',
             '自然绿色风格 — 适合餐饮、健康、农业、环保。清新、有机、生命力。',
             'food', '["green","nature","organic","food","health"]'),
            ('warm', '暖橙', '1.0.0', '',
             '暖橙色风格 — 适合零售、生活服务、美容、家居。温馨、亲切。',
             'retail', '["warm","orange","retail","lifestyle"]'),
            ('ocean', '深海蓝', '1.0.0', '',
             '深海蓝色风格 — 适合企业、制造、物流、金融。沉稳、专业。',
             'enterprise', '["dark","blue","enterprise","manufacturing"]'),
        ]
        for slug, name, ver, author, desc, industry, tags in theme_seeds:
            m.execute(
                "INSERT OR IGNORE INTO themes (slug, name, version, author, description, industry, tags, config_json, dir_name) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (slug, name, ver, author, desc, industry, tags,
                 '{"name":"' + name + '","slug":"' + slug + '","version":"' + ver + '","builtin":false}', slug)
            )
        m.commit()
        print(f'[Migration] seed themes: {len(theme_seeds)} themes added')

    # ── Migration: brand_settings software_name + software_slogan ──
    with get_db() as m:
        cols = [r['name'] for r in m.execute('PRAGMA table_info(brand_settings)').fetchall()]
        if 'software_name' not in cols:
            m.execute("ALTER TABLE brand_settings ADD COLUMN software_name TEXT NOT NULL DEFAULT 'VeroRon 维洛智能'")
            m.commit()
            print('[Migration] brand_settings.software_name added')
        if 'software_slogan' not in cols:
            m.execute("ALTER TABLE brand_settings ADD COLUMN software_slogan TEXT NOT NULL DEFAULT 'Multi-Agent AI Operating System / 多智能体驱动的AI内容与商业枢纽'")
            m.commit()
            print('[Migration] brand_settings.software_slogan added')

    # ── Migration: tm_brand_settings site_name_cn → VeroRun ──
    with get_db() as m:
        row = m.execute("SELECT site_name_cn FROM tm_brand_settings WHERE id=1").fetchone()
        if row and row["site_name_cn"] == 'TradeMind':
            m.execute("UPDATE tm_brand_settings SET site_name_cn='VeroRun' WHERE id=1")
            m.commit()
            print("[Migration] tm_brand_settings.site_name_cn updated to VeroRun")



    # ── Migration: drop cluster_services (2026-07-06) 合并到 site_domains ──
    with get_db() as m:
        m.execute("DROP TABLE IF EXISTS cluster_services")
        m.commit()
        print('[Migration] ✅ cluster_services table dropped (merged into site_domains)')

    # ── Migration: 合并 service_plans → subscription_plans（订阅SaaS归类 — 2026-06-10）──
    with get_db() as m:
        # 迁移套餐：service_plans → subscription_plans（不覆盖已有）
        old_plans = m.execute("SELECT * FROM service_plans").fetchall()
        migrated_plans = 0
        for p in old_plans:
            exists = m.execute("SELECT id FROM subscription_plans WHERE plan_key=?", (p['plan_key'],)).fetchone()
            if not exists:
                # daily_limit 合并到 features_json
                import json as _j
                old_features = _j.loads(p['features']) if p['features'] else []
                old_features.append(f"每日{p['daily_limit']}次调用")
                m.execute(
                    "INSERT INTO subscription_plans (plan_key, name, description, price_month, price_year, tier, features_json, sort_order, is_active, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (p['plan_key'], p['name'], p['description'],
                     int(p['price_month'] * 100), int(p['price_year'] * 100),
                     'premium', _j.dumps(old_features, ensure_ascii=False),
                     p['sort_order'], p['is_active'], p['created_at'])
                )
                migrated_plans += 1
        m.commit()
        if migrated_plans:
            print(f'[Migration] service_plans → subscription_plans: migrated {migrated_plans} plans')
        else:
            print('[Migration] service_plans → subscription_plans: no new plans to migrate')

        # 迁移订单：billing_orders → subscription_orders
        old_bills = m.execute("SELECT * FROM billing_orders").fetchall()
        migrated_bills = 0
        for b in old_bills:
            exists = m.execute("SELECT id FROM subscription_orders WHERE order_no=?", (b['order_no'],)).fetchone()
            if not exists:
                m.execute(
                    "INSERT INTO subscription_orders (order_no, user_id, amount_fen, currency, item_type, plan_key, period, status, payment_method, created_at, paid_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (b['order_no'], b['user_id'], int(b['amount'] * 100), b['currency'],
                     b['item_type'], 'unknown', 'once', b['status'],
                     b['payment_method'] or '', b['created_at'], b['paid_at'])
                )
                migrated_bills += 1
        m.commit()
        if migrated_bills:
            print(f'[Migration] billing_orders → subscription_orders: migrated {migrated_bills} orders')
        else:
            print('[Migration] billing_orders → subscription_orders: no orders to migrate')

        # 迁移订单：orders → subscription_orders
        old_orders = m.execute("SELECT * FROM orders").fetchall()
        migrated_ord = 0
        for o in old_orders:
            exists = m.execute("SELECT id FROM subscription_orders WHERE order_no=?", (o['order_id'],)).fetchone()
            if not exists:
                m.execute(
                    "INSERT INTO subscription_orders (order_no, user_id, amount_fen, currency, item_type, plan_key, period, status, payment_method, created_at, paid_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (o['order_id'], o['user_id'], int((o['amount'] or 0) * 100), 'CNY',
                     'subscription', o['tier_bought'] or 'unknown', 'once', o['status'],
                     o['pay_method'] or '', o['created_at'], o['paid_at'])
                )
                migrated_ord += 1
        m.commit()
        if migrated_ord:
            print(f'[Migration] orders → subscription_orders: migrated {migrated_ord} orders')
        else:
            print('[Migration] orders → subscription_orders: no orders to migrate')

        print('[Migration] 旧表合并完成。service_plans/billing_orders/orders 保留以兼容旧代码，新代码应使用 subscription_* 表')

    # ── 抖音小程序支持：chat_messages + mp_profiles (2026-06-11) ──
    with get_db() as m:
        m.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                openid      TEXT PRIMARY KEY,
                messages    TEXT DEFAULT '[]',
                created_at  TEXT,
                updated_at  TEXT
            )
        """)
        m.execute("""
            CREATE TABLE IF NOT EXISTS mp_profiles (
                openid      TEXT PRIMARY KEY,
                profile     TEXT DEFAULT '{}',
                summary     TEXT DEFAULT '',
                visit_count INTEGER DEFAULT 0,
                created_at  TEXT,
                updated_at  TEXT
            )
        """)
        m.commit()
        print('[Migration] chat_messages + mp_profiles 表已创建')

    # 迁移：为 mp_profiles 表添加 visit_count 字段
    try:
        with get_db() as m:
            m.execute("ALTER TABLE mp_profiles ADD COLUMN visit_count INTEGER DEFAULT 0")
    except Exception as e:
        import logging
        logging.debug(f"[Migration] mp_profiles visit_count column may already exist: {e}")

    # ── 多租户 OAuth 配置表 (2026-06-11) ──
    with get_db() as m:
        m.execute("""
            CREATE TABLE IF NOT EXISTS oauth_providers (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                site_domain   TEXT NOT NULL,
                provider      TEXT NOT NULL DEFAULT 'douyin',
                client_key    TEXT NOT NULL DEFAULT '',
                client_secret TEXT NOT NULL DEFAULT '',
                is_active     INTEGER DEFAULT 1,
                created_at    TEXT,
                updated_at    TEXT,
                UNIQUE(site_domain, provider)
            )
        """)
        m.commit()
        print('[Migration] oauth_providers 表已创建')

    # ── Migration: products.images 多图片字段 (2026-06-19) ──
    with get_db() as m:
        cols_p = [r['name'] for r in m.execute('PRAGMA table_info(products)').fetchall()]
        if 'images' not in cols_p:
            try:
                m.execute("ALTER TABLE products ADD COLUMN images TEXT DEFAULT '[]'")
                m.commit()
                print('[Migration] products.images column added')
            except Exception as e:
                print(f'[Migration] products.images skipped: {e}')

    # ── Migration: categories 商品分类表 (2026-06-19) ──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            slug        TEXT UNIQUE,
            parent_id   INTEGER DEFAULT 0,
            level       INTEGER DEFAULT 0,
            icon        TEXT DEFAULT '',
            sort_order  INTEGER DEFAULT 0,
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_cat_parent ON categories(parent_id)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_cat_level ON categories(level)')

        # 检查是否需要补充 products.category_id
        cols_p2 = [r['name'] for r in m.execute('PRAGMA table_info(products)').fetchall()]
        if 'category_id' not in cols_p2:
            try:
                m.execute("ALTER TABLE products ADD COLUMN category_id INTEGER DEFAULT 0")
                m.commit()
                print('[Migration] products.category_id column added')
            except Exception as e:
                print(f'[Migration] products.category_id skipped: {e}')

        m.commit()
        print('[Migration] categories table created')

    # ── Migration: product_specs / product_spec_values / product_skus (2026-06-19) ──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS product_specs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL REFERENCES products(id),
            spec_name   TEXT NOT NULL,
            sort_order  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_ps_product ON product_specs(product_id)')

        m.execute('''CREATE TABLE IF NOT EXISTS product_spec_values (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            spec_id     INTEGER NOT NULL REFERENCES product_specs(id),
            spec_value  TEXT NOT NULL,
            sort_order  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_psv_spec ON product_spec_values(spec_id)')

        m.execute('''CREATE TABLE IF NOT EXISTS product_skus (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL REFERENCES products(id),
            sku_code    TEXT NOT NULL,
            spec_path   TEXT NOT NULL DEFAULT '{}',
            price       REAL NOT NULL DEFAULT 0,
            stock       INTEGER DEFAULT 0,
            image       TEXT DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_psk_product ON product_skus(product_id)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_psk_code ON product_skus(sku_code)')
        m.commit()
        print('[Migration] product_specs / product_spec_values / product_skus tables created')

    # ── Migration: carts.sku_id (2026-06-19) ──
    with get_db() as m:
        cols_c2 = [r['name'] for r in m.execute('PRAGMA table_info(carts)').fetchall()]
        if 'sku_id' not in cols_c2:
            try:
                m.execute("ALTER TABLE carts ADD COLUMN sku_id INTEGER DEFAULT 0 REFERENCES product_skus(id)")
                m.commit()
                print('[Migration] carts.sku_id added')
            except Exception as e:
                print(f'[Migration] carts.sku_id skipped: {e}')

    # ── Migration: 独立部署套餐 subscription_plans (2026-06-27) ──
    with get_db() as m:
        site_plans = [
            ('deploy_basic', '基础版',
             '个人创业者/小微企业快速建站',
             19900, 199900, 0, 'basic',
             '["AI智能建站(响应式+自定义域名)","AI智能客服(基础问答)","AI内容生成","基础SEO优化","CMS内容管理","多AI供应商切换(可自配APIKey)","AI分析报告","赠送¥50 AI金(额度,用尽可自购)","小程序增值入口(定制费另计)"]', 1),
            ('deploy_pro', '专业版',
             '小微企业/电商卖家线上业务首选',
             39900, 399900, 0, 'popular',
             '["AI智能建站","AI客服RAG知识库","CMS内容管理","完整电商商城(商品/购物车/订单/支付)","1688供应链对接(采集→AI优化→商城发布)","知识库+RAG检索","AI持续SEO+排名跟踪","用户画像+分析报告","赠送¥80 AI金(额度,用尽可自购)","小程序增值入口(定制费另计)"]', 2),
            ('deploy_enterprise', '企业版',
             '品牌企业全链路AI运营',
             69900, 699900, 0, 'premium',
             '["AI智能建站","AI高级客服(多轮对话+CRM+飞书通知)","AI内容工厂(RSS→AI加工→CMS→社媒推送)","Agent矩阵(1+12智能体协作)","1688批量供应链管理+自动铺货","社媒自动发布(微信/微博/头条/抖音)","云服务自动开通","12维用户画像+意向分级","数据看板+AI洞察报告","月度巡检+专属客服","赠送¥120 AI金(额度,用尽可自购)","小程序增值入口(定制费另计)"]', 3),
        ]
        for pk, nm, desc, pm, py, td, tier, feats, so in site_plans:
            exists = m.execute("SELECT id FROM subscription_plans WHERE plan_key=?", (pk,)).fetchone()
            if exists:
                m.execute(
                    "UPDATE subscription_plans SET name=?, description=?, price_month=?, price_year=?, trial_days=?, tier=?, features_json=?, sort_order=? WHERE plan_key=?",
                    (nm, desc, pm, py, td, tier, feats, so, pk))
            else:
                m.execute(
                    "INSERT INTO subscription_plans (plan_key, name, description, price_month, price_year, trial_days, tier, features_json, sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
                    (pk, nm, desc, pm, py, td, tier, feats, so))
        m.commit()
        print(f'[Migration] 独立部署套餐 subscription_plans 已更新')

    # ── Migration: pricing_rules 价格计算器配置表 (2026-06-20) ──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS pricing_rules (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_key    TEXT UNIQUE NOT NULL,
            label       TEXT NOT NULL,
            rule_type   TEXT NOT NULL DEFAULT 'radio',
            options_json TEXT NOT NULL DEFAULT '[]',
            sort_order  INTEGER DEFAULT 0,
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        # Seed default calculator rules
        rules = [
            ('pages', '页面数量', 'radio',
             '[{"value":"5","label":"5 页面","price":0,"desc":"适合展示型官网"},{"value":"10","label":"10 页面","price":260000,"desc":"适合功能型网站"},{"value":"20","label":"20 页面","price":740000,"desc":"适合大型企业站"}]', 1),
            ('service', 'AI智能客服', 'radio',
             '[{"value":"basic","label":"基础问答","price":0,"desc":"常见问题自动回复"},{"value":"rag","label":"RAG知识库","price":100000,"desc":"基于文档智能问答+意向识别"},{"value":"pro","label":"高级多轮对话","price":480000,"desc":"多轮对话+飞书通知+CRM对接"}]', 2),
            ('miniapp', '小程序', 'radio',
             '[{"value":"none","label":"不需要","price":0,"desc":""},{"value":"wechat","label":"微信小程序","price":200000,"desc":""},{"value":"both","label":"微信+抖音小程序","price":400000,"desc":""}]', 3),
            ('content', 'AI内容生成', 'radio',
             '[{"value":"basic","label":"基础版","price":0,"desc":"AI文案生成(需自行配置API)"},{"value":"pro","label":"专业版","price":200000,"desc":"含AI配置+培训+持续优化"}]', 4),
            ('seo', 'SEO优化', 'radio',
             '[{"value":"basic","label":"基础SEO","price":0,"desc":"标题/描述/结构化数据"},{"value":"ai","label":"AI持续SEO","price":200000,"desc":"AI监控+关键词建议+排名跟踪"}]', 5),
        ]
        for rk, lbl, rt, opts, so in rules:
            exists = m.execute("SELECT id FROM pricing_rules WHERE rule_key=?", (rk,)).fetchone()
            if not exists:
                m.execute(
                    "INSERT INTO pricing_rules (rule_key, label, rule_type, options_json, sort_order) VALUES (?,?,?,?,?)",
                    (rk, lbl, rt, opts, so))
        m.commit()
        print(f'[Migration] pricing_rules seed complete')

    # ── Migration: order_items 物流字段 (2026-06-21) ──
    with get_db() as m:
        shipping_cols = [r['name'] for r in m.execute('PRAGMA table_info(order_items)').fetchall()]
        migration_cols = {
            'tracking_company': "tracking_company TEXT DEFAULT ''",
            'tracking_number': "tracking_number TEXT DEFAULT ''",
            'shipping_status': "shipping_status TEXT DEFAULT ''",
            'shipped_at': "shipped_at TEXT",
        }
        for col_name, col_def in migration_cols.items():
            if col_name not in shipping_cols:
                try:
                    m.execute(f"ALTER TABLE order_items ADD COLUMN {col_def}")
                    print(f'[Migration] order_items.{col_name} added')
                except Exception as e:
                    print(f'[Migration] order_items.{col_name} skipped: {e}')

    # ── Migration: express_companies 快递公司字典 (2026-06-21) ──
    with get_db() as m:
        m.execute('''CREATE TABLE IF NOT EXISTS express_companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            kdniao_code TEXT DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            sort_order  INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )''')
        # 常用快递公司种子数据
        companies = [
            ('shunfeng', '顺丰速运', 'SF', 1),
            ('zhongtong', '中通快递', 'ZTO', 2),
            ('yuantong', '圆通速递', 'YTO', 3),
            ('yunda', '韵达快递', 'YD', 4),
            ('shentong', '申通快递', 'STO', 5),
            ('jd', '京东物流', 'JD', 6),
            ('ems', 'EMS', 'EMS', 7),
            ('debang', '德邦快递', 'DBL', 8),
            ('huitongkuaidi', '百世快递', 'HTKY', 9),
            ('youzhengguonei', '中国邮政', 'YZGN', 10),
            ('zhaijisong', '宅急送', 'ZJS', 11),
            ('youshuwuliu', '优速物流', 'UC', 12),
            ('tiantian', '天天快递', 'TTKD', 13),
            ('kuaijie', '快捷快递', 'KJKD', 14),
            ('quanfengkuaidi', '全峰快递', 'QFKD', 15),
            ('suer', '速尔快递', 'SUER', 16),
        ]
        for code, name, kdn, so in companies:
            exists = m.execute("SELECT id FROM express_companies WHERE code=?", (code,)).fetchone()
            if not exists:
                m.execute(
                    "INSERT INTO express_companies (code, name, kdniao_code, sort_order) VALUES (?,?,?,?)",
                    (code, name, kdn, so))
        m.commit()
        print(f'[Migration] express_companies seed complete ({len(companies)} companies)')

    # ── Migration: order_items 支付字段 (2026-06-21) ──
    with get_db() as m:
        payment_cols = [r['name'] for r in m.execute('PRAGMA table_info(order_items)').fetchall()]
        for col_name, col_def in {
            'payment_method': "payment_method TEXT DEFAULT ''",
            'payment_trade_no': "payment_trade_no TEXT DEFAULT ''",
        }.items():
            if col_name not in payment_cols:
                try:
                    m.execute(f"ALTER TABLE order_items ADD COLUMN {col_def}")
                    print(f'[Migration] order_items.{col_name} added')
                except Exception as e:
                    print(f'[Migration] order_items.{col_name} skipped: {e}')

    # ── Migration: order_items completed_at / 退款字段 (2026-06-21) ──
    with get_db() as m:
        status_cols = [r['name'] for r in m.execute('PRAGMA table_info(order_items)').fetchall()]
        for col_name, col_def in {
            'completed_at': "completed_at TEXT",
            'refund_reason': "refund_reason TEXT DEFAULT ''",
            'refund_requested_at': "refund_requested_at TEXT",
            'refunded_at': "refunded_at TEXT",
        }.items():
            if col_name not in status_cols:
                try:
                    m.execute(f"ALTER TABLE order_items ADD COLUMN {col_def}")
                    print(f'[Migration] order_items.{col_name} added')
                except Exception as e:
                    print(f'[Migration] order_items.{col_name} skipped: {e}')

    # ── Migration: invoices 发票系统 ──
    with get_db() as m:
        m.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no      TEXT UNIQUE NOT NULL,
                order_no        TEXT NOT NULL,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                amount_fen      INTEGER NOT NULL DEFAULT 0,
                amount_yuan     REAL NOT NULL DEFAULT 0,
                plan_name       TEXT DEFAULT '',
                period_text     TEXT DEFAULT '',
                status          TEXT NOT NULL DEFAULT 'issued',
                                -- issued / cancelled
                pdf_path        TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        m.execute('CREATE INDEX IF NOT EXISTS idx_inv_user ON invoices(user_id)')
        m.execute('CREATE INDEX IF NOT EXISTS idx_inv_order ON invoices(order_no)')
        m.commit()
        print('[Migration] invoices table created')

    # ── Migration: orders user_deleted soft-delete ──
    with get_db() as m:
        for table in ['subscription_orders', 'order_items']:
            cols = [r['name'] for r in m.execute(f'PRAGMA table_info({table})').fetchall()]
            if 'user_deleted' not in cols:
                try:
                    m.execute(f"ALTER TABLE {table} ADD COLUMN user_deleted INTEGER DEFAULT 0")
                    print(f'[Migration] {table}.user_deleted added')
                except Exception as e:
                    print(f'[Migration] {table}.user_deleted skipped: {e}')
        m.commit()


def _get_default_interests():
    """6 大类 ~35 个兴趣标签"""
    cats = [
        ("娱乐与媒体", ["电影","电视剧","音乐","动漫","游戏","阅读","短视频","综艺","纪录片"]),
        ("运动健身",   ["足球","篮球","跑步","健身","瑜伽","户外","游泳","滑雪","骑行"]),
        ("生活休闲",   ["旅行","美食","摄影","宠物","时尚","美妆","咖啡","露营","穿搭"]),
        ("科技知识",   ["IT","数码","编程","AI","财经","科学","历史","天文","区块链"]),
        ("艺术创作",   ["绘画","写作","手工艺","摄影","设计","书法","插画"]),
        ("其他",       ["健康养生","教育","环保","汽车","星座","心理学","投资","创业"]),
    ]
    tags = []
    for cat, items in cats:
        for i, n in enumerate(items):
            tags.append((n, cat, i+1, 1))  # is_hot=1
    return tags


# ── Migration: deployment_codes 独立部署订阅表 (2026-06-27) ──
with get_db() as m:
    m.execute('''CREATE TABLE IF NOT EXISTS deployment_codes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        code            TEXT UNIQUE NOT NULL,
        code_hash       TEXT NOT NULL,
        user_id         INTEGER NOT NULL,
        plan_key        TEXT NOT NULL DEFAULT 'deploy_basic',
        duration_days   INTEGER NOT NULL DEFAULT 365,
        expires_at      TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','used','expired','revoked')),
        last_heartbeat  TEXT,
        last_hostname   TEXT DEFAULT '',
        last_version    TEXT DEFAULT '',
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    m.execute('CREATE INDEX IF NOT EXISTS idx_dc_code ON deployment_codes(code)')
    m.execute('CREATE INDEX IF NOT EXISTS idx_dc_user ON deployment_codes(user_id)')
    m.execute('CREATE INDEX IF NOT EXISTS idx_dc_status ON deployment_codes(status)')
    m.commit()
    print('[Migration] ✅ deployment_codes 独立部署订阅表')

# ── Migration: 清理旧版套餐数据 (2026-06-27) ──
with get_db() as m:
    old_plan_keys = ['free', 'standard', 'pro', 'site_basic', 'site_standard', 'site_pro']
    for pk in old_plan_keys:
        m.execute("DELETE FROM subscription_plans WHERE plan_key=?", (pk,))
    # 更新已存在的老 plan_key 的订阅记录
    m.execute("UPDATE subscription_orders SET plan_key='deploy_basic' WHERE plan_key IN ('site_basic','free')")
    m.execute("UPDATE subscription_orders SET plan_key='deploy_pro' WHERE plan_key IN ('site_pro','site_standard','standard')")
    m.execute("UPDATE subscription_orders SET plan_key='deploy_enterprise' WHERE plan_key='site_enterprise'")
    m.commit()
    print('[Migration] ✅ 旧版套餐数据已清理')

# ── 国际化: 市场特定表结构 (2026-06-29) ──
if MARKET == 'intl':
    with get_db() as m:
        # INTL 用户表补充 OAuth 字段（CN 已有的 wechat/douyin 字段在 INTL 中保持空值）
        intl_cols = [r['name'] for r in m.execute('PRAGMA table_info(users)').fetchall()]
        intl_additions = {
            'country_code': "country_code TEXT DEFAULT ''",
            'google_id': "google_id TEXT",
            'github_id': "github_id TEXT",
            'facebook_id': "facebook_id TEXT",
        }
        for col_name, col_def in intl_additions.items():
            if col_name not in intl_cols:
                try:
                    m.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
                    print(f'[i18n] users.{col_name} added')
                except Exception as e:
                    print(f'[i18n] users.{col_name} skipped: {e}')

        # INTL 地址表（自由文本）
        m.execute('''CREATE TABLE IF NOT EXISTS user_addresses_intl (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            label           TEXT DEFAULT '',
            recipient_name  TEXT NOT NULL DEFAULT '',
            phone           TEXT NOT NULL DEFAULT '',
            country         TEXT NOT NULL DEFAULT '',
            state           TEXT DEFAULT '',
            city            TEXT DEFAULT '',
            address_line1   TEXT NOT NULL DEFAULT '',
            address_line2   TEXT DEFAULT '',
            postal_code     TEXT DEFAULT '',
            is_default      INTEGER DEFAULT 0,
            status          INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )''')
        m.execute('CREATE INDEX IF NOT EXISTS idx_addr_intl_user ON user_addresses_intl(user_id)')

        # INTL subscription_plans 种子数据（美元计价）
        intl_plans = [
            ('deploy_basic', 'Starter', 'For entrepreneurs and small businesses', 999, 9999, 0, 'basic',
             '["AI Site Builder","AI Chat Assistant (basic)","AI Content Generator","Basic SEO","CMS","Multi AI provider switching","AI Analytics Report","$5 AI Credits included"]', 1),
            ('deploy_pro', 'Professional', 'For growing businesses and online sellers', 2999, 29999, 0, 'popular',
             '["AI Site Builder","AI Chat with RAG Knowledge Base","CMS","Full eCommerce","Knowledge Base + RAG","AI SEO + Ranking Tracking","User Analytics","$8 AI Credits included"]', 2),
            ('deploy_enterprise', 'Enterprise', 'Full-stack AI-powered business operations', 5999, 59999, 0, 'premium',
             '["AI Site Builder","AI Chat (multi-turn + CRM)","Content Factory (RSS→AI→CMS→Social)","Agent Matrix (1+12 agents)","Social auto-publish","Cloud service auto-provisioning","User profiling + intent scoring","Analytics dashboard + AI insights","$12 AI Credits included"]', 3),
        ]
        for pk, nm, desc, pm, py, td, tier, feats, so in intl_plans:
            exists = m.execute("SELECT id FROM subscription_plans WHERE plan_key=?", (pk,)).fetchone()
            if not exists:
                m.execute(
                    "INSERT INTO subscription_plans (plan_key, name, description, price_month, price_year, trial_days, tier, features_json, sort_order, currency) VALUES (?,?,?,?,?,?,?,?,?,'USD')",
                    (pk, nm, desc, pm, py, td, tier, feats, so))
        m.commit()
        print('[i18n] ✅ INTL-specific tables and data initialized')
else:
    # CN 区: subscription_plans 增加 currency 字段（向后兼容）
    with get_db() as m:
        plan_cols = [r['name'] for r in m.execute('PRAGMA table_info(subscription_plans)').fetchall()]
        if 'currency' not in plan_cols:
            try:
                m.execute("ALTER TABLE subscription_plans ADD COLUMN currency TEXT DEFAULT 'CNY'")
                print('[i18n] subscription_plans.currency added (CNY)')
            except Exception as e:
                print(f'[i18n] subscription_plans.currency skipped: {e}')

# ── 客户管理: 企业认证字段 + 审核表 (CN/INTL通用) ──
with get_db() as m:
    user_cols = [r['name'] for r in m.execute('PRAGMA table_info(users)').fetchall()]
    enterprise_fields = {
        'enterprise_name': "enterprise_name TEXT DEFAULT ''",
        'enterprise_tax_id': "enterprise_tax_id TEXT DEFAULT ''",
        'enterprise_address': "enterprise_address TEXT DEFAULT ''",
        'enterprise_phone': "enterprise_phone TEXT DEFAULT ''",
        'enterprise_bank': "enterprise_bank TEXT DEFAULT ''",
        'enterprise_bank_acct': "enterprise_bank_acct TEXT DEFAULT ''",
        'enterprise_verified': "enterprise_verified INTEGER DEFAULT 0",
        'enterprise_verified_at': "enterprise_verified_at TEXT",
    }
    for col_name, col_def in enterprise_fields.items():
        if col_name not in user_cols:
            try:
                m.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
            except Exception as e:
                print(f'[migration] users.{col_name} skipped: {e}')

    m.execute('''CREATE TABLE IF NOT EXISTS enterprise_verifications (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL REFERENCES users(id),
        enterprise_name TEXT NOT NULL,
        tax_id          TEXT NOT NULL,
        license_url     TEXT DEFAULT '',
        ocr_raw         TEXT DEFAULT '',
        status          TEXT NOT NULL DEFAULT 'pending',
        review_notes    TEXT DEFAULT '',
        reviewed_by     INTEGER REFERENCES users(id),
        reviewed_at     TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )''')
    m.execute('CREATE INDEX IF NOT EXISTS idx_ev_user ON enterprise_verifications(user_id)')
    m.execute('CREATE INDEX IF NOT EXISTS idx_ev_status ON enterprise_verifications(status)')
    print('[migration] ✅ enterprise_verifications table + users enterprise fields initialized')

# ── i18n 翻译表 (2026-06-30) ──
with get_db() as m:
    m.execute('''CREATE TABLE IF NOT EXISTS i18n_strings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        locale      TEXT NOT NULL DEFAULT 'zh-CN',
        source_hash TEXT NOT NULL,
        source      TEXT NOT NULL,
        translation TEXT NOT NULL DEFAULT '',
        is_auto     INTEGER DEFAULT 0,
        updated_at  TEXT DEFAULT (datetime('now')),
        created_at  TEXT DEFAULT (datetime('now')),
        UNIQUE(locale, source_hash)
    )''')
    m.execute('CREATE INDEX IF NOT EXISTS idx_i18n_locale ON i18n_strings(locale)')
    print('[i18n] ✅ i18n_strings table created')

# ── Migration: site_domains 子域名管理表 (2026-07-06) ──
with get_db() as m:
    m.execute('''CREATE TABLE IF NOT EXISTS site_domains (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        site_config_id  INTEGER NOT NULL DEFAULT 1,
        subdomain       TEXT NOT NULL,
        full_domain     TEXT NOT NULL UNIQUE,
        display_name    TEXT NOT NULL DEFAULT '',
        template        TEXT DEFAULT 'default',
        is_published    INTEGER DEFAULT 1,
        page_keys_json  TEXT DEFAULT '["home"]',
        sort_order      INTEGER DEFAULT 0,
        service_port    INTEGER DEFAULT NULL,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (site_config_id) REFERENCES site_configs(id)
    )''')
    m.execute('CREATE INDEX IF NOT EXISTS idx_sd_config ON site_domains(site_config_id)')
    m.execute('CREATE INDEX IF NOT EXISTS idx_sd_domain ON site_domains(full_domain)')
    m.commit()
    print('[Migration] ✅ site_domains 子域名管理表')

# ── Migration: site_domains 新增 service_port 列 (2026-07-06) ──
try:
    with get_db() as m:
        m.execute("ALTER TABLE site_domains ADD COLUMN service_port INTEGER DEFAULT NULL")
        m.commit()
        print('[Migration] ✅ site_domains 新增 service_port 列')
except Exception:
    pass  # 列已存在

# 默认主页站点在 site_configs 中创建（如不存在）
_default_domain = os.environ.get('DEPLOY_DOMAIN', 'localhost')
_default_brand = os.environ.get('DEPLOY_BRAND', 'VeroRon 维洛智能')
with get_db() as m:
    m.execute(
        "INSERT OR IGNORE INTO site_configs (id, domain, name, industry, tier, features) VALUES (1, ?, ?, 'ai', 'self_hosted', '[\"main\"]')",
        (_default_domain, _default_brand)
    )
    m.commit()

# site_domains 默认种子（3 个标准子域名）
with get_db() as m:
    _defaults = [
        ('www',      f'www.{_default_domain}',      f'{_default_brand} 官网',       'default', 1, 1),
        ('agent',    f'agent.{_default_domain}',    f'{_default_brand} 管理后台',   'default', 1, 2),
        ('platform', f'platform.{_default_domain}', f'{_default_brand} 用户中心',   'default', 1, 3),
    ]
    for sub, full, name, template, pub, so in _defaults:
        m.execute(
            "INSERT OR IGNORE INTO site_domains (site_config_id, subdomain, full_domain, display_name, template, is_published, sort_order) VALUES (1, ?, ?, ?, ?, ?, ?)",
            (sub, full, name, template, pub, so)
        )
        m.commit()
    print('[Migration] ✅ site_domains 默认种子 (www/agent/platform)')


def now_iso():
    return datetime.now().isoformat()


TIERS = {
    'free':     {'name': 'Free',     'daily_limit': 20,   'price_month': 0,   'price_year': 0,    'features': ['basic'],       'desc': '每日20次调用', 'max_agents': 1},
    'standard': {'name': 'Standard', 'daily_limit': 100,  'price_month': 88,  'price_year': 888,  'features': ['basic', 'sentiment', 'market'], 'desc': '每日100次调用', 'max_agents': 3},
    'pro':      {'name': 'Pro',      'daily_limit': 1000, 'price_month': 188, 'price_year': 1888,  'features': ['all'],         'desc': '每日1000次调用', 'max_agents': 10},
}

if __name__ == "__main__":
    init_db()
    print(f"OK: {DB_PATH}")
