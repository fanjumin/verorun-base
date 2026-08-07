-- mini_app_builder v2.0.0 migration
-- =================================
-- Moves legacy tables (dev_accounts, schema_meta, mini_app_projects,
-- mini_app_versions) from the public schema into the dedicated
-- `mini_app_builder` schema.  Preserves all data, indexes and sequences
-- (ALTER TABLE ... SET SCHEMA).  Backward-compatible public views are created
-- so any external SQL readers keep working.
--
-- Idempotent: safe to run multiple times.  The same logic is executed at
-- plugin setup by plugins/mini_app_builder/migrate.py; this SQL is archived
-- for standalone execution.
--
-- Run as:  psql -d verorun -f migrations/v2.0.0.sql

CREATE SCHEMA IF NOT EXISTS mini_app_builder;

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['dev_accounts', 'schema_meta', 'mini_app_projects', 'mini_app_versions']
    LOOP
        -- Move from public to mini_app_builder if it still lives in public
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = t
        ) THEN
            EXECUTE format('ALTER TABLE public.%I SET SCHEMA mini_app_builder', t);
        END IF;
        -- Backward-compatible public view
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'mini_app_builder' AND table_name = t
        ) THEN
            EXECUTE format('CREATE OR REPLACE VIEW public.%I AS SELECT * FROM mini_app_builder.%I', t, t);
        END IF;
    END LOOP;
END $$;
