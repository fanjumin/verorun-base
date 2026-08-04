# ads (Ad Management)

## Overview

The **ads** plugin is the central ad management module for the VeroRun platform. It provides a complete system for creating, placing, and tracking advertisements across the site. With built-in AI-Ready APIs, the plugin enables intelligent ad placement and optimization, making it suitable for both manual and automated advertising workflows.

The plugin manages its own independent SQLite database (`ads.db`) and integrates with the platform's hook system for seamless extensibility.

| Property    | Value             |
|-------------|-------------------|
| Identifier  | `ads`             |
| Version     | 1.0.0             |
| Database    | `ads.db`          |
| Menu Group  | AI & Content      |
| Menu Key    | `ads`             |

---

## Features

- **Ad Placement Management** -- Create, update, and delete ad placements with configurable dimensions, positions, and targeting rules.
- **Impression & Click Statistics** -- Track every ad impression and click with full timestamp and referrer data for analytics.
- **AI-Ready APIs** -- Expose structured endpoints and hooks that AI agents can consume for automated ad optimization and placement decisions.
- **Template Rendering** -- Server-side rendering of ad units via Jinja2 templates (`render_ads.html`).
- **Admin Dashboard** -- A dedicated admin panel (`admin_ads.html`) for managing placements, reviewing statistics, and configuring ad parameters.
- **Client-Side Integration** -- JavaScript module (`ads.js`) for dynamic ad rendering and impression/click recording on the frontend.
- **Role-Based Access Control** -- Granular permissions (`ads.read`, `ads.write`) for controlling who can view and manage ads.

---

## Architecture

The plugin follows a layered architecture:

```
ads/
  __init__.py       -- Plugin entry point (AdsPlugin class)
  models.py         -- Data layer (init_ad_db, ORM models)
  routes.py         -- Web layer (ads_bp Blueprint, admin & public routes)
  ai_tools.py       -- AI integration layer (AI function tools)
  templates/
    admin_ads.html  -- Admin dashboard template
    render_ads.html -- Ad unit rendering template
  static/
    ads.js          -- Frontend ad rendering and tracking
```

**Data Flow:**
1. Admins create/configure placements via the admin dashboard.
2. Ad placements are stored in `ads.db`.
3. The `render_ads.html` template renders ad units on the frontend.
4. `ads.js` records impressions and clicks via hook endpoints.
5. Statistics are aggregated and displayed in the admin panel.
6. AI tools read placement data and stats for automated optimization.

---

## Directory Structure

```
plugins/ads/
  __init__.py
  models.py
  routes.py
  ai_tools.py
  templates/
    admin_ads.html
    render_ads.html
  static/
    ads.js
  README.en.md
```

---

## Installation & Activation

1. Ensure the `ads/` directory is present under `plugins/`.
2. The plugin is auto-discovered by the VeroRun plugin loader.
3. Verify activation in the admin panel under **Plugins**.
4. The database `ads.db` is automatically initialized on first load by `models.init_ad_db()`.

No additional dependencies are required beyond the core VeroRun platform.

---

## Configuration

The following configuration keys are available in the plugin's configuration:

| Key               | Type    | Default | Description                                        |
|-------------------|---------|---------|----------------------------------------------------|
| `default_width`   | integer | 320     | Default width (in pixels) for new ad placements    |
| `default_height`  | integer | 0       | Default height (in pixels). 0 means auto-height.   |
| `max_placements`  | integer | 50      | Maximum number of concurrent ad placements allowed |

Configuration can be set via the admin panel or the plugin configuration file.

---

## API Endpoints & Hooks

### Hooks Provided

The plugin registers the following hooks that other plugins and the platform can consume:

| Hook                        | Description                                      |
|-----------------------------|--------------------------------------------------|
| `ads/get_placements`        | Retrieve all active ad placements                |
| `ads/render_ad`             | Render a specific ad unit as HTML                |
| `ads/get_stats`             | Get impression and click statistics              |
| `ads/record_impression`     | Record an ad impression event                    |
| `ads/record_click`          | Record an ad click event                         |

### Hooks Listened

This plugin does not listen to any external hooks.

### Admin Routes

- `GET  /admin/ads/` -- Admin dashboard (ad placements list, statistics)
- `POST /admin/ads/` -- Create a new ad placement
- Various CRUD routes under the `ads_bp` Blueprint

### Public Routes

- `GET  /api/ads/render` -- Server-side ad rendering endpoint
- `POST /api/ads/impression` -- Record impression (called by `ads.js`)
- `POST /api/ads/click` -- Record click (called by `ads.js`)

---

## Dependencies

This plugin has no external third-party dependencies. It relies solely on:

- VeroRun core (hook system, plugin loader, template engine)
- SQLite (via VeroRun's database abstraction layer)

---

## Permissions

| Permission  | Description                          |
|-------------|--------------------------------------|
| `ads.read`  | View ad placements and statistics    |
| `ads.write` | Create, update, and delete ad placements |

---

## License

This plugin is part of the VeroRun platform and is distributed under the same license as the core platform.