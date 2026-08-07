-- mini_app_builder v2.1.0 rollback — 独立库回滚
-- =============================================================
-- 撤销 v2.1.0 独立库结构：删除新增的 sessions 表与 platform_users schema。
-- 注意：4 张自有表（dev_accounts 等）为「迁移 + 导入」得来，回滚时**保留**，
-- 因为它们已从主库转移，删除即永久丢失。
--
-- 运行方式： psql -d verorun_miniapp -f migrations/v2.1.0_rollback.sql
-- 幂等：可重复执行。

DROP TABLE IF EXISTS mini_app_builder.mini_app_sessions;

DROP SCHEMA IF EXISTS platform_users;

-- platform_user_mappings 属平台用户 schema，随之上层删除
-- 4 张自有表保留（数据在独立库，主库已无副本）
