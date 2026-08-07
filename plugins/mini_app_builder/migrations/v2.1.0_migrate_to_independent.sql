-- mini_app_builder v2.1.0 — 主库 → 独立库 数据迁移指引
-- =============================================================
-- 将主库 verorun 的 mini_app_builder schema 数据迁移到独立库 verorun_miniapp。
--
-- ⚠️ 本脚本为「操作指引」（含变量），不能直接 psql -f 执行。
--    请在**服务器**上按以下步骤执行，并由运维人员核对。
--
-- 前置条件：
--   1. 已创建独立库： CREATE DATABASE verorun_miniapp OWNER verorun;
--   2. 已执行 v2.1.0.sql 完成独立库建表；
--   3. 应用已升级到 mini_app_builder v2.1.0，且插件迁移逻辑已运行
--      （旧表已在主库的 mini_app_builder schema 中）。
--
-- 步骤（服务器 bash，PG 单实例多库模式）：

-- ── Step 1: 导出主库 mini_app_builder schema（含 platform_users 若存在）──
-- pg_dump -h 127.0.0.1 -p 5432 -U verorun -d verorun \
--     --schema=mini_app_builder --data-only --column-inserts \
--     -f /tmp/miniapp_schema_data.sql

-- ── Step 2: 导入独立库（数据走 4 张自有表 + sessions）──
-- psql -h 127.0.0.1 -p 5432 -U verorun -d verorun_miniapp -f /tmp/miniapp_schema_data.sql

-- ── Step 3: 校验行数一致 ──
-- SELECT 'dev_accounts' AS tbl, COUNT(*) FROM mini_app_builder.dev_accounts
-- UNION ALL SELECT 'mini_app_projects', COUNT(*) FROM mini_app_builder.mini_app_projects
-- UNION ALL SELECT 'mini_app_versions', COUNT(*) FROM mini_app_builder.mini_app_versions;
--（分别在主库与独立库执行，逐表对比计数）

-- ── Step 4: 切换应用连接 ──
-- .env 增加： MINI_APP_PG_DB=verorun_miniapp
--（或 MINI_APP_DB_URL=postgres://verorun:xxx@127.0.0.1:5432/verorun_miniapp）
-- 重启 admin(8084) 与 main_site(8081)。

-- ── Step 5: 观察期（建议 1 周）后清理主库残留 ──
-- psql -d verorun -c "DROP SCHEMA IF EXISTS mini_app_builder CASCADE;"
-- psql -d verorun -c "DROP VIEW IF EXISTS public.dev_accounts;
--                      DROP VIEW IF EXISTS public.mini_app_projects;
--                      DROP VIEW IF EXISTS public.mini_app_versions;"
-- ⚠️ 仅在确认独立库数据完整、无回滚需求后执行。

-- ── 回滚（观察期内）──
-- psql -h 127.0.0.1 -U verorun -d verorun_miniapp -f migrations/v2.1.0_rollback.sql
-- psql -d verorun -c "CREATE SCHEMA IF NOT EXISTS mini_app_builder;"
-- pg_dump -d verorun_miniapp --schema=mini_app_builder --data-only --column-inserts | psql -d verorun
-- .env 移除 MINI_APP_PG_DB / MINI_APP_DB_URL，重启服务。
