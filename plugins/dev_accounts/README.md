# Developer Accounts (dev_accounts)

## Overview

Developer Accounts is a VeroRun plugin for centrally managing developer credentials (App ID, App Secret, Bot Token, Access Token, etc.) for third-party social media platforms. All sensitive credentials are encrypted at rest.

## Features

- **Multi-platform management**: Douyin, Toutiao, WeChat, Telegram, LINE developer accounts
- **Encrypted credentials**: App Secret, Bot Token, Access Token, Channel Secret are encrypted with Fernet before storage
- **CRUD operations**: Create, read, update and delete developer accounts
- **Connection test**: Telegram / LINE verify credentials against platform APIs
- **Shared credential provider**: Unified credential access for other modules (mini-program login, site builder, etc.)

## Architecture

### Database strategy

The plugin uses **no separate database / schema** — data lives in the main database `public` schema.

**Logic-decoupling decision (standard §12.10)**: the `dev_accounts` table is shared and read by the following modules, so it stays in the main DB:

- `main_site/routes/mini_program.py`: reads `bot_token` directly via SQL for Telegram login signature verification
- `site_builder/routes.py`: reads credentials through `models` for mini-app deployment

Moving to an isolated schema would break those core paths. Data access uses the shared PostgreSQL helper `plugins/_base/db.py` (`get_raw_connection()` + `PgConnection`, `SET search_path TO public`).

### Table: dev_accounts

| Column | Type | Description |
|--------|------|-------------|
| `id` | Serial | Primary key |
| `platform` | Text | Platform (douyin / toutiao / wechat / telegram / line) |
| `account_name` | Text | Display name for this account |
| `app_id` | Text | Application ID |
| `app_secret` | Text (encrypted) | Application secret (Fernet) |
| `bot_token` | Text (encrypted) | Bot token (Fernet) |
| `channel_id` | Text | Channel ID |
| `channel_secret` | Text (encrypted) | Channel secret (Fernet) |
| `access_token` | Text (encrypted) | Access token (Fernet) |
| `extra_config` | Text | Extra config (JSON string) |
| `is_active` | Integer | Enabled flag (1 / 0) |
| `created_at` | Text | Creation time |
| `updated_at` | Text | Last update time |

### Table: schema_meta (Schema version tracking, standard §10.6)

| Column | Type | Description |
|--------|------|-------------|
| `key` | Text (PK) | Metadata key (currently only `schema_version`) |
| `value` | Text | Value (plugin version, e.g. `1.1.0`) |
| `updated_at` | Text | Last update time |

### Encryption

Sensitive fields are encrypted with `cryptography.fernet` (**AES-128-CBC + HMAC-SHA256**, not AES-256-GCM). The key is derived from the `DEV_ACCOUNTS_ENCRYPTION_KEY` environment variable via SHA-256 into the Fernet key format. The cipher is initialized lazily on the first `encrypt` / `decrypt` call.

### Module layout

```
dev_accounts/
├── __init__.py          # Plugin entry: routes, lifecycle hooks, dashboard stats
├── models.py            # Data access layer (PG connection, CRUD, connection tests)
├── routes.py            # Admin API routes (CRUD, connection tests)
├── crypto.py            # Fernet encryption utilities
├── i18n/                # Translations (zh-CN.yml / en.yml)
│   ├── zh-CN.yml
│   └── en.yml
├── migrations/          # Version migration SQL
│   └── v1.0.0.sql
└── plugin.json          # Plugin metadata
```

## Installation & Enablement

### Install

The plugin ships with the VeroRun plugin directory; no extra install step is required.

### Environment variable

Set the encryption key before first use (the plugin loads fine without it; only `encrypt` / `decrypt` calls raise an error):

```bash
export DEV_ACCOUNTS_ENCRYPTION_KEY='<Fernet key>'
# Generate one:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Enable

1. Enable Developer Accounts in the admin "Plugins" page
2. On enable the `dev_accounts` table is created in the main DB (if missing)
3. The "Developer Accounts" menu item appears at `/admin/dev-accounts`

## Configuration

The plugin has **no plugin-level config** (`config` is empty in `plugin.json`). The only external configuration is the `DEV_ACCOUNTS_ENCRYPTION_KEY` environment variable (see above).

## API Endpoints

### Admin dashboard

| Menu item | Description |
|-----------|-------------|
| `Developer Accounts` | Management page loaded by the admin SPA from `templates/admin_devaccounts.html` (menu `key` maps to the `window.l_dev_accounts` render function) |

The page provides platform filtering, account list, create/edit modal (leave sensitive credentials blank to keep them unchanged), delete, and connection test.

### Admin API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/dev-accounts/` | List accounts (optional `?platform=` filter) |
| `POST` | `/admin/dev-accounts/` | Create an account |
| `GET` | `/admin/dev-accounts/<id>` | Get account details |
| `PUT` | `/admin/dev-accounts/<id>` | Update an account |
| `DELETE` | `/admin/dev-accounts/<id>` | Delete an account |
| `POST` | `/admin/dev-accounts/<id>/test` | Test platform connection |

All endpoints require admin privileges (JWT `is_admin`).

### Internal interface

| Method | Description |
|--------|-------------|
| `models.get_all(platform)` | List accounts (sensitive fields masked) |
| `models.get_by_id(id)` | Get one account (sensitive fields masked) |
| `models.get_by_platform(platform)` | Get first account for a platform (sensitive fields masked) |
| `models.test_connection(id)` | Test platform connection |

## Dependencies

### Internal

- VeroRun plugin manager & routing
- `plugins/_base/db.py` (PostgreSQL connection helpers)
- `cryptography` (Fernet)
- Environment variable `DEV_ACCOUNTS_ENCRYPTION_KEY`

### External

- `cryptography` (Python package)

### Consumers

- **main_site** (`routes/mini_program.py`): reads `bot_token` via SQL for Telegram login
- **site_builder** (`routes.py`): reads credentials via `models.get_all/update` for mini-app deployment

## License

Part of the VeroRun project; subject to the VeroRun project license.
