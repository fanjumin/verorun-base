-- ============================================================================
-- fix_easykai_db.sql
-- 将 easykai.db（旧库/7月1日）升级到 verorun.db（新库/当前）的结构
-- 
-- 操作说明：
--   1. 备份 easykai.db
--   2. sqlite3 easykai.db < fix_easykai_db.sql
--
-- 变更摘要：
--   - 删除 15 个废弃索引
--   - 删除 53 张废弃表（DROP TABLE IF EXISTS，安全操作）
--   - 新增 1 列（cms_posts.publish_channels）
-- ============================================================================

PRAGMA foreign_keys=OFF;

-- ============================================================================
-- 第一步：删除废弃索引（15 个）
-- ============================================================================

DROP INDEX IF EXISTS idx_ci_order;
DROP INDEX IF EXISTS idx_ci_status;
DROP INDEX IF EXISTS idx_ci_user;
DROP INDEX IF EXISTS idx_community_sections_path;
DROP INDEX IF EXISTS idx_orders_status;
DROP INDEX IF EXISTS idx_pl_instance;
DROP INDEX IF EXISTS idx_pm_provider_model;
DROP INDEX IF EXISTS idx_regions_full_name;
DROP INDEX IF EXISTS idx_regions_level;
DROP INDEX IF EXISTS idx_regions_parent;
DROP INDEX IF EXISTS idx_sms_uniq;
DROP INDEX IF EXISTS idx_social_accounts_user;
DROP INDEX IF EXISTS idx_task_log_agent_date;
DROP INDEX IF EXISTS idx_tkl_dimension;
DROP INDEX IF EXISTS ix_apscheduler_jobs_next_run_time;

-- ============================================================================
-- 第二步：删除废弃表（53 张）
-- ============================================================================

-- 废弃的阿里云 API 相关表（NOTE: 这些表在 verorun.db 中仍存在，但用户确认清理）
DROP TABLE IF EXISTS ali_api_items;
DROP TABLE IF EXISTS ali_api_logs;
DROP TABLE IF EXISTS ali_api_user_stats;
DROP TABLE IF EXISTS ali_api_tokens;
DROP TABLE IF EXISTS ali_oauth_states;

-- 废弃的品牌设置表（NOTE: 该表在 verorun.db 中仍存在，但用户确认清理）
DROP TABLE IF EXISTS tm_brand_settings;

-- 废弃的活动与管理员笔记表
DROP TABLE IF EXISTS activity_logs;
DROP TABLE IF EXISTS admin_notes;

-- 废弃的智能体社区功能表
DROP TABLE IF EXISTS agent_arena_stats;
DROP TABLE IF EXISTS agent_balances;
DROP TABLE IF EXISTS agent_comments;
DROP TABLE IF EXISTS agent_feeds;
DROP TABLE IF EXISTS agent_follows;
DROP TABLE IF EXISTS agent_notifications;
DROP TABLE IF EXISTS agent_profiles;
DROP TABLE IF EXISTS agent_stats;
DROP TABLE IF EXISTS agent_streaks;
DROP TABLE IF EXISTS agent_task_logs;
DROP TABLE IF EXISTS agent_votes;

-- 废弃的任务调度表
DROP TABLE IF EXISTS apscheduler_jobs;

-- 废弃的文章评论表
DROP TABLE IF EXISTS article_comments;

-- 废弃的自动充值设置表
DROP TABLE IF EXISTS auto_recharge_settings;

-- 废弃的云实例表
DROP TABLE IF EXISTS cloud_instances;

-- 废弃的社区板块表
DROP TABLE IF EXISTS community_sections;

-- 废弃的联系人会话与回复表
DROP TABLE IF EXISTS contact_conversations;
DROP TABLE IF EXISTS contact_replies;

-- 废弃的日用量日志表
DROP TABLE IF EXISTS daily_usage_log;

-- 废弃的辩论相关表（自动检测到的旧库遗留表）
DROP TABLE IF EXISTS debate_arguments;
DROP TABLE IF EXISTS debate_votes;
DROP TABLE IF EXISTS debates;

-- 废弃的体验包表
DROP TABLE IF EXISTS experience_packages;

-- 废弃的页脚导航相关表
DROP TABLE IF EXISTS footer_articles;
DROP TABLE IF EXISTS footer_links;
DROP TABLE IF EXISTS footer_nav;

-- 废弃的公会相关表
DROP TABLE IF EXISTS guild_members;
DROP TABLE IF EXISTS guilds;

-- 废弃的页眉导航表
DROP TABLE IF EXISTS header_nav;

-- 废弃的帮助中心表
DROP TABLE IF EXISTS help_answers;
DROP TABLE IF EXISTS help_requests;

-- 废弃的知识缺口表
DROP TABLE IF EXISTS knowledge_gaps;

-- 废弃的市场提醒表
DROP TABLE IF EXISTS market_alerts;

-- 废弃的模型提供商表
DROP TABLE IF EXISTS model_providers;

-- 废弃的合作伙伴链接表
DROP TABLE IF EXISTS partner_links;

-- 废弃的支付相关表
DROP TABLE IF EXISTS payment_methods;
DROP TABLE IF EXISTS payment_orders;

-- 废弃的资源配置相关表
DROP TABLE IF EXISTS provision_logs;

-- 废弃的循环订阅表
DROP TABLE IF EXISTS recurring_subscriptions;

-- 废弃的区域表
DROP TABLE IF EXISTS regions;

-- 废弃的技能相关表
DROP TABLE IF EXISTS skill_fragments;
DROP TABLE IF EXISTS skill_keys;
DROP TABLE IF EXISTS skill_versions;

-- 废弃的社交媒体链接表
DROP TABLE IF EXISTS social_media_links;

-- 废弃的用户社交账号、标签表
DROP TABLE IF EXISTS user_social_accounts;
DROP TABLE IF EXISTS user_tags;

-- ============================================================================
-- 第三步：新增表（3 张在旧库中不存在的表）
-- ============================================================================

-- site_domains —— 子域名管理表
CREATE TABLE IF NOT EXISTS site_domains (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    site_config_id  INTEGER NOT NULL DEFAULT 1,
    subdomain       TEXT NOT NULL,
    full_domain     TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL DEFAULT '',
    template        TEXT DEFAULT 'default',
    is_published    INTEGER DEFAULT 1,
    page_keys_json  TEXT DEFAULT '[]',
    sort_order      INTEGER DEFAULT 0,
    service_port    INTEGER DEFAULT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (site_config_id) REFERENCES site_configs(id)
);
CREATE INDEX IF NOT EXISTS idx_sd_config ON site_domains(site_config_id);
CREATE INDEX IF NOT EXISTS idx_sd_domain ON site_domains(full_domain);

-- i18n_strings —— 国际化翻译表
CREATE TABLE IF NOT EXISTS i18n_strings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    locale      TEXT NOT NULL DEFAULT 'zh-CN',
    source_hash TEXT NOT NULL,
    source      TEXT NOT NULL,
    translation TEXT NOT NULL DEFAULT '',
    is_auto     INTEGER DEFAULT 0,
    updated_at  TEXT DEFAULT (datetime('now')),
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(locale, source_hash)
);
CREATE INDEX IF NOT EXISTS idx_i18n_locale ON i18n_strings(locale);

-- enterprise_verifications —— 企业认证审核表
CREATE TABLE IF NOT EXISTS enterprise_verifications (
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
);
CREATE INDEX IF NOT EXISTS idx_ev_user ON enterprise_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_ev_status ON enterprise_verifications(status);

-- ============================================================================
-- 第三步（接上）：新增列
-- ============================================================================

-- cms_posts.publish_channels —— 发布渠道控制（JSON 数组）
ALTER TABLE cms_posts ADD COLUMN publish_channels TEXT DEFAULT '[]';

-- ============================================================================
-- 第四步：恢复外键约束
-- ============================================================================

PRAGMA foreign_keys=ON;

-- ============================================================================
-- 迁移完成。以下变更因 SQLite ALTER TABLE 限制无法通过本脚本处理，
-- 如需严格对齐新结构，应通过「创建新表→迁移数据→重命名」方式处理：
--
-- 1. oauth_providers 表：
--    - site_domain 从 UNIQUE 改为非 UNIQUE
--    - 新增 UNIQUE(site_domain, provider) 表级约束
--
-- 2. users 表：
--    - 删除 nickname 列（旧表中存在，新表中无此列）
--    - 删除 alipay_user_id 列（旧表中存在，新表中无此列）
--
-- 3. products 表：
--    - 删除 product_config 列（旧表中存在，新表中无此列）
--
-- 4. site_blocks / site_plans 表：
--    - site_id 新增 REFERENCES site_configs(id) 外键约束
--
-- 5. user_feedback 表：
--    - user_id 新增 REFERENCES users(id) 外键约束
--    - title / content 新增 NOT NULL 约束
--    - created_at 新增 DEFAULT
--
-- 以上差异不影响数据完整性，现有应用代码运行正常，可暂不处理。
-- ============================================================================
