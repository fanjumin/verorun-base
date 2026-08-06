# Analytics (analytics)

## Overview

Analytics is VeroRun's server-side cookie-less analytics middleware plugin, providing complete website traffic data collection, storage, aggregation, and visualization. The plugin uses a cookie-less lightweight tracking approach to deliver PV/UV statistics, visitor session identification, page-level behavior analysis, geolocation resolution, and trend analysis without relying on client-side cookies.

Version: **1.5.0**

## Features

- **Cookie-less Tracking**: Visitor identification based on server-side fingerprints (IP + User-Agent combined hash), no client cookies required, privacy-compliant
- **PV/UV Statistics**: Accurate page view (PV) and unique visitor (UV) tracking
- **Visitor Session Management**: Automatic session identification and merging based on time windows
- **Page-level Statistics**: Fine-grained analysis by page path, referrer, device type, etc.
- **Geolocation**: ip2region-based IP geolocation (country/province/city)
- **User-Agent Parsing**: Built-in UA parser for browser, OS, and device type detection
- **Trend Analysis**: Hourly/daily/weekly/monthly access trends
- **Real-time Dashboard**: Embedded analytics dashboard in the admin panel
- **Background Aggregation**: Dedicated aggregation thread every 60 seconds
- **Workflow Integration**: `workflow_nodes` module for calling analytics data in workflows

## Architecture

### Database Strategy

The plugin uses a **dedicated database**, storing data in the PostgreSQL `analytics` schema.

### Module Structure

```
┌─────────────────────────────────────────────────┐
│                  middleware.py                    │
│        (request interception & raw capture)       │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                   tracker.py                     │
│         (behavior tracking & event logging)       │
└─────────────────────┬───────────────────────────┘
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  ua_parser   │ │  geoip   │ │  models.py   │
│  (UA parsing)│ │(IP lookup)│ │ (11 tables)  │
└──────────────┘ └──────────┘ └──────┬───────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────┐
│                 processor.py                     │
│      (background aggregation / every 60s)        │
└─────────────────────┬───────────────────────────┘
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   routes     │ │   cli    │ │ workflow_    │
│ (dashboard   │ │ (command │ │ nodes        │
│  Blueprint)  │ │  line)   │ │ (workflow)   │
└──────────────┘ └──────────┘ └──────────────┘
```

### 11 Analytics Tables

The plugin maintains the following tables in the PostgreSQL `analytics` schema:

| Table | Purpose |
|------|------|
| `analytics_logs` | Raw access logs |
| `analytics_visitor_sessions` | Visitor session aggregation |
| `analytics_hourly_stats` | Hourly aggregated stats |
| `analytics_daily_stats` | Daily aggregated stats |
| `analytics_page_stats` | Page-level stats |
| `analytics_source_stats` | Referrer/source stats |
| `analytics_geo_stats` | Geolocation stats |
| `analytics_device_stats` | Device/browser/OS stats |
| `analytics_events` | Custom event records |
| `analytics_alerts` | Alert records |
| `analytics_privacy_config` | Privacy configuration |

## Directory Structure

```
analytics/
├── __init__.py              # Plugin entry, registers hooks and middleware
├── models.py                # 11 analytics table models
├── middleware.py            # Server-side cookie-less analytics middleware
├── processor.py             # Background aggregation thread (every 60s)
├── tracker.py               # Event tracker, records raw behavior data
├── geoip.py                 # IP geolocation (ip2region-based)
├── ua_parser.py             # User-Agent parser
├── routes.py                # Dashboard Blueprint routes (register_routes)
├── cli.py                   # Command-line tools
├── workflow_nodes.py        # Workflow engine integration nodes
├── migrate_analytics.py     # Database migration script
├── plugin.json              # Plugin metadata configuration
├── data/
│   └── ip2region_v4.xdb     # ip2region IP geolocation database
├── ip2region/
│   ├── __init__.py
│   ├── searcher.py          # ip2region search engine
│   └── util.py              # ip2region utilities
├── i18n/
│   ├── en.yml               # English internationalization
│   └── zh-CN.yml            # Simplified Chinese internationalization
├── migrations/
│   └── 001_initial.sql      # Database version migration (initial schema)
├── static/
│   ├── js/                  # Localized frontend dependencies (echarts/chart.js/tsparticles) and dashboard JS
│   ├── china.json           # China map data
│   └── world.json           # World map data
└── templates/
    └── analytics.html       # Admin dashboard template
```

## Installation & Activation

### Installation

The plugin is included in VeroRun's default plugin directory; no separate installation is required.

### Activation

1. Ensure the `analytics` schema exists in PostgreSQL
2. Run the database migration script:

```bash
python -m plugins.analytics.migrate_analytics
```

3. Enable the Analytics plugin in the VeroRun admin "Plugin Management" page
4. The middleware will automatically start intercepting requests and collecting data after activation

### Local Development

The plugin uses the PostgreSQL `analytics` schema; tables are created automatically on initialization (see `migrations/001_initial.sql`).

## Configuration

The following parameters are configured in `plugin.json`:

```json
{
  "name": "analytics",
  "version": "1.5.0",
  "database": {
    "type": "postgresql",
    "schema": "analytics"
  },
  "aggregation": {
    "interval_seconds": 60
  },
  "middleware": {
    "enabled": true,
    "exclude_paths": ["/admin/*", "/static/*", "/api/health"]
  },
  "ip2region": {
    "db_path": "data/ip2region_v4.xdb"
  }
}
```

| Config Key | Description | Default |
|--------|------|--------|
| `database.schema` | PostgreSQL schema name | `analytics` |
| `aggregation.interval_seconds` | Aggregation thread interval (seconds) | `60` |
| `middleware.enabled` | Whether the middleware is enabled | `true` |
| `middleware.exclude_paths` | Excluded path patterns | Admin panel and static assets |
| `ip2region.db_path` | ip2region database file path | `data/ip2region_v4.xdb` |

## API Endpoints

### Hooks Provided

| Hook Identifier | Type | Description |
|-------------|------|------|
| `analytics/track_event` | Hook | Manually record custom analytics events |
| `analytics/get_realtime` | Hook | Fetch real-time analytics (online visitors, today's PV/UV) |
| `analytics/get_trend` | Hook | Fetch analytics trends for a specified time range |

### Admin Panel

| Path | Description |
|------|------|
| `/admin/analytics/` | Analytics dashboard (embedded page) |

### Filters Registered

| Filter Identifier | Description |
|---------------|------|
| `dashboard.data` | Module-level registration; injects analytics summaries into the admin dashboard |

## Dependencies

### Internal Dependencies

- VeroRun core framework: middleware registration, hook system, event bus
- Admin panel (auth-center): dashboard embedding and menu rendering

### External Dependencies

- **ip2region**: IP geolocation library using the offline `data/ip2region_v4.xdb` database
- **PostgreSQL**: production data storage (`analytics` schema)

### Dependents

- **health_check** plugin: fetches access trends via the `analytics/get_trend` hook for health analysis
- **Workflow engine**: calls analytics data via `workflow_nodes.py`

### Menu

- **Menu group**: `Monitoring & Data`
- **Embedded URL**: `/admin/analytics/`

## License

This plugin is part of the VeroRun project and follows the overall license of the VeroRun project.
