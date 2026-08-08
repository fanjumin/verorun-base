-- mini_app_builder v2.1.0 migration — 独立数据库建表
-- =============================================================
-- 目标：插件自有数据从主库 verorun 物理迁移到独立库 mini_app。
-- 本 SQL 在 **独立库 mini_app** 上执行（数据迁移见
-- v2.1.0_migrate_to_independent.sql）。
--
-- 运行方式： psql -d mini_app -f migrations/v2.1.0.sql
-- 幂等：可重复执行。
--
-- 注意：此处创建的 4 张自有表（dev_accounts / schema_meta /
-- mini_app_projects / mini_app_versions）与插件 Python 端建表语句一致
-- （见 submodules/accounts/models.py 与 models.py）。

CREATE SCHEMA IF NOT EXISTS mini_app_builder;
CREATE SCHEMA IF NOT EXISTS platform_users;

-- ── 1. 开发者账号（原 dev_accounts，迁移自 public schema）──
CREATE TABLE IF NOT EXISTS mini_app_builder.dev_accounts (
    id               SERIAL PRIMARY KEY,
    platform         TEXT NOT NULL,
    account_name     TEXT NOT NULL,
    app_id           TEXT DEFAULT '',
    app_secret       TEXT DEFAULT '',
    bot_token        TEXT DEFAULT '',
    channel_id       TEXT DEFAULT '',
    channel_secret   TEXT DEFAULT '',
    access_token     TEXT DEFAULT '',
    extra_config     TEXT DEFAULT '{}',
    is_active        INTEGER DEFAULT 1,
    created_at       TEXT DEFAULT NOW(),
    updated_at       TEXT DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dev_accounts_platform
    ON mini_app_builder.dev_accounts(platform);

-- ── 2. schema 版本元数据 ──
CREATE TABLE IF NOT EXISTS mini_app_builder.schema_meta (
    key        TEXT PRIMARY KEY,
    value      TEXT DEFAULT '',
    updated_at TEXT DEFAULT NOW()
);

-- ── 3. 小程序项目（原 mini_app_projects）──
CREATE TABLE IF NOT EXISTS mini_app_builder.mini_app_projects (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    description     TEXT DEFAULT '',
    created_by      BIGINT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ── 4. 小程序版本（原 mini_app_versions，列名与 Python 端 models.py 对齐）──
CREATE TABLE IF NOT EXISTS mini_app_builder.mini_app_versions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES mini_app_builder.mini_app_projects(id) ON DELETE CASCADE,
    version_no      BIGINT NOT NULL,
    platforms_json  TEXT DEFAULT '[]',
    options_json    TEXT DEFAULT '{}',
    result_json     TEXT DEFAULT '{}',
    output_path     TEXT DEFAULT '',
    status          TEXT DEFAULT 'completed',
    prompt          TEXT DEFAULT '',
    prompt_template TEXT DEFAULT '',
    ai_plan_json    TEXT DEFAULT '{}',
    widgets_json    TEXT DEFAULT '[]',
    created_at      TEXT DEFAULT (NOW())
);
CREATE INDEX IF NOT EXISTS idx_miniapp_versions_project
    ON mini_app_builder.mini_app_versions(project_id);

-- ── 5. 平台用户映射（联邦身份：平台身份 → 主库 user_id）──
CREATE TABLE IF NOT EXISTS platform_users.platform_user_mappings (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform         TEXT NOT NULL,
    platform_user_id TEXT NOT NULL,
    user_id          BIGINT NOT NULL,
    username         TEXT DEFAULT '',
    display_name     TEXT DEFAULT '',
    avatar           TEXT DEFAULT '',
    created_at       TIMESTAMP DEFAULT NOW(),
    last_login       TIMESTAMP DEFAULT NOW(),
    UNIQUE (platform, platform_user_id)
);
CREATE INDEX IF NOT EXISTS idx_platform_mapping_user
    ON platform_users.platform_user_mappings(user_id);

-- ── 6. 小程序聊天会话（独立存储，替代主库 chatbot_sessions）──
CREATE TABLE IF NOT EXISTS mini_app_builder.mini_app_sessions (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id  TEXT NOT NULL,
    user_id     BIGINT DEFAULT 0,
    platform    TEXT DEFAULT '',
    query_text  TEXT DEFAULT '',
    reply_text  TEXT DEFAULT '',
    intent      TEXT DEFAULT '',
    sentiment   TEXT DEFAULT '',
    created_at  TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_miniapp_sessions_user
    ON mini_app_builder.mini_app_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_miniapp_sessions_session
    ON mini_app_builder.mini_app_sessions(session_id);
