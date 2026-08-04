# subscription (Unified Subscription Management)

## Overview

The **subscription** plugin provides a unified subscription management system for the VeroRun platform. It implements a pay-as-you-go feature marketplace with per-SKU billing, enabling merchants to monetize premium features. The plugin supports dual-environment payment routing: Alipay/WeChat Pay for the Chinese (CN) market and Stripe/PayPal for international (INTL) customers.

The plugin includes scheduled jobs for subscription expiry checks and auto-renewal, and uses dedicated gateway modules for each supported payment provider.

| Property    | Value                |
|-------------|----------------------|
| Identifier  | `subscription`       |
| Version     | 1.0.0                |
| Database    | (internal)           |
| Menu Group  | (managed via admin)  |

---

## Features

- **Feature Marketplace** -- Define and sell premium features as subscription SKUs with per-SKU billing.
- **Pay-as-You-Go** -- Flexible billing model where customers pay only for the features they need.
- **Dual-Environment Routing** -- Automatic payment routing: CN users get Alipay/WeChat Pay; INTL users get Stripe/PayPal.
- **Multi-Gateway Support** -- Dedicated gateway modules for Alipay, WeChat Pay, Stripe, and PayPal.
- **Subscription Lifecycle** -- Full lifecycle management: subscribe, cancel, renew, and check subscription status.
- **Scheduled Jobs** -- Automated expiry checks via `register_jobs()` and configurable auto-renewal.
- **Trial & Grace Periods** -- Configurable trial days and grace periods for subscription management.
- **User Registration Hook** -- Automatically initialize subscription state when a new user registers.

---

## Architecture

The plugin follows a gateway-based architecture with a scheduler:

```
subscription/
  __init__.py     -- Plugin entry point (SubscriptionPlugin)
  models.py       -- Data layer (ORM models, subscription tables)
  routes.py       -- Web layer (sub_bp Blueprint)
  services.py     -- Subscription business logic
  scheduler.py    -- Scheduled jobs for expiry and auto-renewal
  gateways/
    alipay.py     -- Alipay payment gateway
    paypal.py     -- PayPal payment gateway
    stripe.py     -- Stripe payment gateway
    wechat.py     -- WeChat Pay payment gateway
```

**Data Flow:**
1. Admin defines subscription SKUs and features in the marketplace.
2. Users browse and subscribe to features.
3. `services.py` routes the payment to the appropriate gateway based on environment (CN/INTL).
4. The gateway module processes the payment and returns confirmation.
5. `scheduler.py` runs periodic jobs to check for expiring subscriptions.
6. Auto-renewal is triggered if enabled and payment succeeds.
7. The `subscription/has` hook lets other plugins check feature access.

---

## Directory Structure

```
plugins/subscription/
  __init__.py
  models.py
  routes.py
  services.py
  scheduler.py
  gateways/
    alipay.py
    paypal.py
    stripe.py
    wechat.py
  README.en.md
```

---

## Installation & Activation

1. Ensure the `subscription/` directory is present under `plugins/`.
2. The plugin is auto-discovered by the VeroRun plugin loader.
3. Verify activation in the admin panel under **Plugins**.
4. The database is automatically initialized on first load.
5. Configure payment gateway credentials for each supported provider.
6. The `register_jobs()` method registers scheduled jobs for expiry checks and auto-renewal.

---

## Configuration

| Key                  | Type    | Default | Description                                      |
|----------------------|---------|---------|--------------------------------------------------|
| `trial_days`         | integer | 0       | Number of free trial days for new subscriptions  |
| `grace_days`         | integer | 3       | Grace period after expiry before access is revoked|
| `auto_renew_default` | boolean | true    | Default auto-renewal setting for new subscriptions|

Each payment gateway also requires its own provider-specific credentials (API keys, secrets, merchant IDs).

---

## API Endpoints & Hooks

### Hooks Provided

| Hook                    | Description                                              |
|-------------------------|----------------------------------------------------------|
| `subscription/has`      | Check if a user has an active subscription to a feature  |
| `subscription/list`     | List all subscriptions for a user                        |
| `subscription/subscribe`| Subscribe a user to a feature                            |
| `subscription/cancel`   | Cancel an active subscription                            |
| `subscription/renew`    | Renew an expiring or expired subscription                |

### Hooks Listened

| Hook               | Description                                              |
|--------------------|----------------------------------------------------------|
| `user/registered`  | Initialize subscription state for new users              |

### Admin Routes

- `GET  /admin/subscription/` -- Subscription management dashboard
- `POST /admin/subscription/sku` -- Create or update a subscription SKU
- `GET  /admin/subscription/users` -- View user subscriptions

### Public Routes

- `GET  /api/subscription/plans` -- List available subscription plans
- `GET  /api/subscription/my` -- Get current user's subscriptions
- `POST /api/subscription/subscribe` -- Subscribe to a plan
- `POST /api/subscription/cancel` -- Cancel a subscription

### Scheduled Jobs

The `register_jobs()` method registers two periodic jobs:
1. **Expiry Check** -- Runs daily to identify and process expired subscriptions.
2. **Auto-Renewal** -- Runs daily to process auto-renewals for subscriptions nearing expiry.

---

## Dependencies

This plugin has no external third-party Python dependencies. It relies on:

- VeroRun core (hook system, plugin loader, template engine, job scheduler)
- SQLite (via VeroRun's database abstraction layer)
- External payment gateway APIs (Alipay, WeChat Pay, Stripe, PayPal)

---

## Permissions

| Permission             | Description                              |
|------------------------|------------------------------------------|
| `subscription.read`    | View subscription plans and status       |
| `subscription.write`   | Subscribe, cancel, and renew             |
| `subscription.admin`   | Manage subscription SKUs and all users   |

---

## License

This plugin is part of the VeroRun platform and is distributed under the same license as the core platform.