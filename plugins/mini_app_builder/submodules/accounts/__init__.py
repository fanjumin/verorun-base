#!/usr/bin/env python3
"""Developer Credentials submodule (merged from plugins/dev_accounts).

The legacy standalone `dev_accounts` plugin (v1.1.0) was merged into
`mini_app_builder` v2.0.0.  This submodule keeps the same data access layer
so existing encrypted credentials remain readable.

Schema mode (§12.10):  `dev_accounts` / `schema_meta` tables now live in the
dedicated `mini_app_builder` schema (migrated via ALTER TABLE SET SCHEMA),
with backward-compatible public views.  Connections go through
plugins/_base/db.py (see models.py get_db()).
"""
