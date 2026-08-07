-- mini_app_builder v2.0.0 rollback
-- =================================
-- Reverts the v2.0.0 schema migration: moves tables back from the
-- mini_app_builder schema into public and drops the compat views.
--
-- WARNING: only run when you are certain no new writes were made through the
-- public views after the upgrade, otherwise the tables in mini_app_builder
-- are the authoritative copy and this rollback would discard newer data
-- written via the views is NOT lost (views are read-only shims created with
-- CREATE OR REPLACE VIEW; writes via them fail).  Moving tables back is safe.
--
-- Run as:  psql -d verorun -f migrations/v2.0.0_rollback.sql

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['dev_accounts', 'schema_meta', 'mini_app_projects', 'mini_app_versions']
    LOOP
        -- Drop compat view first
        IF EXISTS (
            SELECT 1 FROM information_schema.views
            WHERE table_schema = 'public' AND table_name = t
        ) THEN
            EXECUTE format('DROP VIEW public.%I', t);
        END IF;
        -- Move table back to public
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'mini_app_builder' AND table_name = t
        ) THEN
            EXECUTE format('ALTER TABLE mini_app_builder.%I SET SCHEMA public', t);
        END IF;
    END LOOP;
END $$;
