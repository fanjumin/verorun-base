# Identity Verification (verification)

## Overview

Identity Verification is VeroRun's user identity authentication plugin, providing real-name verification based on the Alipay identity verification service. The plugin uses a dedicated PostgreSQL schema `verification` to store authentication request records, while delegating the core authentication logic to auth-center's `verification_service`.

The plugin follows a "data isolation, logic reuse" design principle: authentication routes remain in auth-center, the plugin only provides the management UI and isolated storage for authentication request records; authentication initiation and callback handling are delegated to the existing auth-center service layer.

## Features

- **Alipay real-name verification**: integrates the Alipay identity verification service for reliable real-name authentication
- **Authentication request management**: isolated storage of authentication request records with status tracking (pending/completed)
- **Request history query**: indexed lookup of authentication history by user ID and request ID
- **Logic reuse**: core authentication logic is delegated to auth-center's `verification_service`, avoiding duplication
- **Dedicated database**: PostgreSQL schema `verification` with the `verification_requests` table
- **Data migration**: idempotently migrates existing authentication request records from the main database on first startup
- **Management UI**: admin dashboard for viewing authentication request status

## Architecture

```
+--------------------------------------------------------------+
|            Frontend (User Submission + Admin View)            |
+--------------------------------------------------------------+
         |                              |
         v                              v
+------------------------+    +---------------------------+
|  auth-center Routes    |    |  Plugin Management UI     |
|  (initiate + callback) |    |  (templates/)            |
|                        |    |  Request status view      |
+------------------------+    +---------------------------+
         |                              |
         v                              v
+--------------------------------------------------------------+
|                    Service Layer (services.py)                |
|  +-- initiate_verification()                                  |
|  |   delegated to auth-center.services.verification_service  |
|  +-- verify_callback()                                       |
|       delegated to auth-center.services.verification_service |
+--------------------------------------------------------------+
         |
         v
+--------------------------------------------------------------+
|                    Data Layer (models.py)                     |
|  PG Schema: verification                                     |
|  +-- verification_requests   authentication request table    |
|      (user_id, request_id, provider, return_url, status,     |
|       created_at, completed_at)                               |
+--------------------------------------------------------------+
         |
         v
+--------------------------------------------------------------+
|                    auth-center Service Layer                  |
|  +-- services/verification_service.py                        |
|      +-- initiate_verification()  Alipay auth initiation     |
|      +-- verify_callback()        Alipay callback handling   |
+--------------------------------------------------------------+
```

**Design principles**:

- **Data isolation**: authentication request records live in the plugin's dedicated schema, never polluting the main database
- **Logic reuse**: core authentication logic (initiation, callback handling) is delegated to auth-center's existing `verification_service`
- **Route retention**: authentication callback routes stay in auth-center; the plugin only adds a management UI
- **Legacy interface compatibility**: the service layer lazily imports auth-center's `verification_service` (the admin process already has auth-center on sys.path — no sys.path modification required)

## Directory Structure

```
verification/
+-- README.md                    # Plugin documentation
+-- plugin.json                  # Plugin metadata configuration
+-- __init__.py                  # Plugin entry point, registers blueprints and hooks
+-- models.py                    # Data models (schema connection, table creation, indexes, main-DB migration)
+-- services.py                  # Core services (delegated to auth-center verification_service)
+-- i18n/
|   +-- en.yml                   # English i18n
|   +-- zh-CN.yml                # Chinese i18n
+-- templates/
    +-- admin_verification.html  # Admin panel page template
```

## Installation & Activation

### Prerequisites

- VeroRun platform version >= 0.10.0
- Alipay Open Platform application (real-name verification product enabled)
- auth-center's `verification_service` correctly configured with Alipay credentials
- PostgreSQL database

### Installation Steps

1. Place the `verification` directory under `plugins/`
2. Ensure `enabled` is `true` in `plugin.json`
3. Restart the application; the plugin will automatically:
   - Create the PostgreSQL schema `verification`
   - Initialize the `verification_requests` table
   - Idempotently migrate existing authentication request records from the main database
4. View authentication requests in the admin panel under "Security & Compliance" > "ID Verification"

### Notes

- Authentication initiation and callback routes remain in auth-center and are unaffected by this plugin
- The plugin only provides a management UI and isolated data storage; it does not alter the authentication flow
- Ensure auth-center's Alipay configuration is correct (app_id, private key, public key, etc.)

## Configuration

This plugin has no additional configuration items; it relies on auth-center's Alipay configuration. The authentication flow is fully controlled by auth-center's `verification_service`.

## API Endpoints

Authentication-related API routes remain in auth-center; the plugin does not expose standalone API endpoints. It provides the following capabilities:

### Hooks Provided

| Hook identifier | Description |
|-----------------|-------------|
| `verification/initiate` | Initiates the real-name verification flow (delegated to auth-center) |
| `verification/verify_callback` | Handles the Alipay authentication callback (delegated to auth-center) |

## Database Schema

### verification_requests

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT (PK) | Auto-increment primary key |
| `user_id` | BIGINT | Authenticating user ID |
| `request_id` | TEXT (UNIQUE) | Unique authentication request identifier |
| `provider` | TEXT | Authentication provider (e.g. alipay) |
| `return_url` | TEXT | Callback URL after authentication completes |
| `status` | TEXT | Authentication status: pending / completed |
| `created_at` | TEXT | Request creation time |
| `completed_at` | TEXT | Authentication completion time |

## Dependencies

### Internal Dependencies

| Dependency | Purpose |
|------------|---------|
| `plugins._base.db` | Plugin base database connection module |
| main DB schema `public.verification_requests` | Migration source (same PG instance, read via `public.` qualification) |
| `auth-center.services.verification_service` | Core authentication logic (`initiate_verification`, `verify_callback`) |

### External Dependencies

| Dependency | Purpose |
|------------|---------|
| Alipay Open Platform API | Real-name verification service |

## Menu Group

- **Security & Compliance** - ID Verification

## License

This plugin is part of the VeroRun platform and follows the platform's unified license agreement.
