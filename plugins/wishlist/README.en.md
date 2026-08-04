# wishlist (Favorites/Wishlist)

## Overview

The **wishlist** plugin provides product favorites and wishlist management for the VeroRun platform. It allows users to save products they are interested in for later purchase, and supports synchronization with price changes. The plugin is lightweight, with routes defined inline within the `__init__.py` module as a Blueprint.

The plugin manages its own independent SQLite database (`wishlist.db`) while performing cross-reads from the main VeroRun database for product information.

| Property    | Value                |
|-------------|----------------------|
| Identifier  | `wishlist`           |
| Version     | 1.0.0                |
| Database    | `wishlist.db`        |
| Menu Group  | None (no admin menu) |

---

## Features

- **Product Favorites** -- Users can add products to their wishlist with a single toggle action.
- **Wishlist Management** -- View, add, and remove items from the wishlist via simple API endpoints.
- **Toggle Functionality** -- The `POST /api/toggle` endpoint adds or removes a product in one call.
- **Bulk Check** -- The `POST /api/check` endpoint allows checking wishlist status for multiple products at once.
- **Item Count** -- The `GET /api/count` endpoint returns the total number of wishlist items for the current user.
- **Price Change Sync** -- Listens to the `product/price_change` event to notify users or update wishlist metadata.
- **Cross-Database Reads** -- Reads product information from the main VeroRun database while storing wishlist data in `wishlist.db`.

---

## Architecture

The plugin defines all routes inline within the `__init__.py` module as a Blueprint:

```
wishlist/
  __init__.py    -- Plugin entry point, Blueprint definition, and all routes
  models.py      -- Data layer (ORM models, wishlist table)
```

**Data Flow:**
1. User browses a product and toggles it into their wishlist.
2. The wishlist entry is stored in `wishlist.db`.
3. Product details are cross-read from the main VeroRun database.
4. When a product price changes, the `product/price_change` hook triggers.
5. The `wishlist/sync` hook allows other plugins to synchronize wishlist data.
6. Users can view their wishlist and remove items at any time.

---

## Directory Structure

```
plugins/wishlist/
  __init__.py
  models.py
  README.en.md
```

---

## Installation & Activation

1. Ensure the `wishlist/` directory is present under `plugins/`.
2. The plugin is auto-discovered by the VeroRun plugin loader.
3. Verify activation in the admin panel under **Plugins**.
4. The database `wishlist.db` is automatically initialized on first load.

No additional dependencies are required beyond the core VeroRun platform.

---

## Configuration

This plugin does not have explicit configuration keys. All settings are managed through the VeroRun admin panel's general wishlist settings.

---

## API Endpoints & Hooks

### Hooks Provided

| Hook              | Description                                              |
|-------------------|----------------------------------------------------------|
| `wishlist/sync`   | Synchronize wishlist data (used by other plugins)        |

### Hooks Listened

| Hook                   | Description                                              |
|------------------------|----------------------------------------------------------|
| `product/price_change` | Triggered when a product price changes                   |

### API Endpoints (Public)

| Method | Endpoint          | Description                                              |
|--------|-------------------|----------------------------------------------------------|
| GET    | `/api/list`       | List all wishlist items for the current user             |
| POST   | `/api/toggle`     | Toggle (add/remove) a product in the wishlist            |
| POST   | `/api/check`      | Check wishlist status for one or more products           |
| GET    | `/api/count`      | Get the total count of wishlist items for the current user|

### Admin Routes

This plugin does not register any admin routes.

---

## Dependencies

This plugin has no external third-party dependencies. It relies on:

- VeroRun core (hook system, plugin loader, template engine)
- SQLite (via VeroRun's database abstraction layer)
- Main VeroRun database (cross-reads for product information)

---

## Permissions

| Permission            | Description                              |
|-----------------------|------------------------------------------|
| `shop.product.read`   | Read product information for wishlist    |
| `user.read`           | Read user information for wishlist owner |

---

## License

This plugin is part of the VeroRun platform and is distributed under the same license as the core platform.