-- Developer Accounts Plugin — v1.0.0 initial migration
-- =====================================================
-- 说明：dev_accounts 表保留在主库 public schema（逻辑解耦，见 __init__.py）。
--       幂等：与 models.init_db() 保持一致，重复执行不报错。

CREATE TABLE IF NOT EXISTS dev_accounts (
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
    ON dev_accounts(platform);
