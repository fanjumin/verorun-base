# VeroRun

**Multi-Agent AI Operating System** — A full-stack SaaS website builder and business management platform powered by a 7-role Agent collaboration matrix with unified LLM gateway, workflow automation, plugin ecosystem, and unified guardian daemon for health monitoring and copyright protection.

VeroRun integrates multi-vendor AI engines (7 providers), e-commerce operations, CMS content management, AI customer service, automation workflows, cloud provisioning, analytics, health monitoring, site builder, mini-program generation, and a plugin-based extension system with lifecycle management.

> **Version:** 0.42.1
> **Repository:** https://github.com/fanjumin/VeroRunSystem

[![Version](https://img.shields.io/badge/version-0.42.1-blue)](https://github.com/fanjumin/VeroRunSystem/releases)
[![Python](https://img.shields.io/badge/python-3.11+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![Database](https://img.shields.io/badge/database-PostgreSQL-336791)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/docker-supported-2496ED)](https://www.docker.com/)

---

## Architecture

### Service Topology

```
+-------------+    +-------------+    +-------------+    +--------------+
|  Main Site  |    |  Auth/User  |    |   Admin     |    |  VeroGuard   |
|   :8081     |    |   :8083     |    |   :8084     |    |   Unified    |
|             |    |             |    |             |    |   Guardian   |
| Auth Center |    |  Platform   |    | Admin Panel |    |              |
| +Captcha    |    | Console     |    | +Plugins    |    | Health +     |
+------+------+    +------+------+    +------+------+    | Integrity +  |
       |                  |                  |            | Heartbeat    |
       +------------------+------------------+            +------+-------+
                          |                                    |
                   +------+------+    +-------------+          |
                   |   Nginx     |    |   systemd   |----------+
                   |  Reverse    |    |  Services   |
                   |   Proxy     |    | verorun-*   |
                   +------+------+    +-------------+
                          |
              +-----------+-----------+
              |           |           |
         yourdomain   platform.*   admin.*
```

### Service Layout

| Port | Domain | Service | Description |
|------|--------|---------|-------------|
| 8081 | Main domain `/auth/` `/oauth/` `/user/` `/api/captcha/` | Main site backend + Auth center + Captcha proxy | Unified entry point for auth, OAuth, user APIs, and proxied captcha |
| 8083 | `platform.*` `/auth/` `/subscribe` | User console & subscription | Platform dashboard, subscription management |
| 8084 | `admin.*` `/admin/` | Admin panel | Plugin management, agent matrix, automation, CMS, shop |
| 8085 | — | Internal health endpoint | Health check endpoint monitored by VeroGuard |
| — | — | VeroGuard Guardian | Unified daemon: health watchdog + integrity verification + heartbeat reporting |

**systemd service names:** `verorun-main` (8081), `verorun-auth` (8083), `verorun-admin` (8084), `verorun-health` (8085), `verorun-guardian` (VeroGuard)

### Tech Stack

- **Backend:** Python 3.11+, Flask, Gunicorn
- **Database:** PostgreSQL (production), SQLite (development/fallback)
- **Process:** systemd, Supervisor (Docker)
- **Reverse Proxy:** Nginx + Let's Encrypt
- **Cache:** Redis
- **AI Engine:** OpenAI-compatible APIs — DashScope, OpenAI, DeepSeek, OpenRouter, SiliconFlow, Google Gemini, xAI Grok (7 providers) with UnifiedLLM gateway
- **AI Infrastructure:** Token budget gate (daily quota + rate limiting), LLM quota management, encrypted API key storage
- **Frontend:** Jinja2 templates, vanilla JavaScript, React Flow (workflow editor), Chart.js, ECharts, Quill.js (rich text)
- **JS Tooling:** Node.js (DiceBear avatars, esbuild)
- **Container:** Docker, Docker Compose (single-container with Nginx + Supervisor)
- **Guardian Compilation:** Nuitka (standalone binary for anti-tampering)

---

## Quick Start

### One-Click Deploy (Ubuntu 22.04/24.04)

```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/install.sh | sudo bash -s -- install your-domain.com
```

Or via git clone:

```bash
git clone https://github.com/fanjumin/VeroRunSystem.git
cd VeroRunSystem
sudo bash deploy/install.sh install your-domain.com
```

The install script provisions PostgreSQL, creates the `verorun` system user, sets up a Python virtual environment, generates `.env` with auto-generated secrets, creates systemd services, configures Nginx, and optionally seeds initial data.

For detailed instructions, see [deploy/README.md](deploy/README.md).

### Post-Install

```bash
# Seed initial data (admin account, plans, products)
sudo bash deploy/install.sh seed

# Configure domain (if skipped during install)
sudo bash deploy/install.sh configure-domain your-domain.com

# Set up SSL
sudo certbot --nginx -d your-domain.com -d platform.your-domain.com -d admin.your-domain.com
```

### Docker Deploy

```bash
docker compose up -d
```

The Docker image bundles all services (Nginx, app, Supervisor) into a single container exposing port 80. Volumes mount `data/`, `admin/static/`, and `main_site/static/` directories for persistence. See [Dockerfile](Dockerfile) and [docker-compose.yml](docker-compose.yml) for details.

### Local Development

**Linux/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # configure your keys
python scripts/dev_start.py
```

**Windows:**

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts\dev_start.py
```

`scripts/dev_start.py` launches all 4 services (captcha, main site, platform, admin) with one command, runs health checks, and prints local URLs and test credentials.

---

## Key Features

### AI & Agent System
- **7-Role Agent Matrix** — Multi-agent collaboration: Athena (coordinator), Content, Shop, Builder, Steward, Ops, Service, plus Supply Chain, Chatbot, Automation, Health Check, Finance, and User agents
- **UnifiedLLM Gateway** — Single entry point for all LLM calls across 7 AI providers with client caching and TTL
- **AI Budget Gate** — Daily token budget cap + per-minute rate limiting with fail-open design
- **LLM Quotas** — Fine-grained quota management: user-level, model-level, module-level, global-level
- **Provider API Key Management** — Encrypted storage of API keys with multi-provider support
- **Agent Discussion** — Multi-agent collaborative discussion and task decomposition (v2.0)
- **Token Monitoring** — Real-time token usage tracking, daily aggregation, and cost analytics

### Site Building & Content
- **AI Site Builder** — Generate complete websites from natural language prompts with industry-specific templates (tech company, restaurant, education, law firm, etc.)
- **Mini Program Generation** — Auto-generate WeChat, Douyin, Telegram, LINE, WhatsApp mini programs with preview and packaging
- **Token-Based Site Settings** — Dynamic site configuration via tokenized rendering engine
- **Theme System** — Jinja2 ChoiceLoader-based theme override system with zero-downtime switching
- **CMS** — Multi-language content management with AI-assisted writing (zh-CN, en)
- **Content Factory** — RSS aggregation, AI content processing, skill pushing, review pipeline

### Workflow & Automation
- **Workflow Automation** — Visual drag-and-drop workflow editor with DAG execution (React Flow)
- **Cron Scheduler** — Built-in cron job engine with pause/resume/toggle
- **Worker Pool** — Dedicated + shared worker pools for parallel task execution
- **Workflow Templates** — Pre-built workflow templates for common automation scenarios
- **System Agents** — Configurable automation agents for cron-triggered tasks

### E-Commerce
- **Full E-Commerce** — Shopping cart, orders, product management, categories
- **Payment Gateways** — Stripe, PayPal, Alipay, WeChat Pay with pluggable provider abstraction
- **Logistics** — Shipping management via Shippo integration
- **Coupons** — Coupon engine with AI-powered recommendations
- **Reviews** — Product review system
- **Wishlist** — User wishlist management
- **Alibaba/1688 Sourcing** — Product sourcing, image search, AI review

### Communications & Social
- **IM Gateway** — Unified messaging across Feishu, DingTalk, WeCom, Telegram, LINE, QQ
- **OAuth Multi-Platform** — WeChat, Alipay, Douyin, Google, GitHub, Facebook, Telegram login
- **Social Push** — Multi-platform content push (Twitter, LinkedIn, Reddit, Telegram Channel)
- **Email Service** — Email integration with template support
- **SMS Service** — Aliyun and Twilio SMS providers
- **Chatbot** — AI customer service chatbot with multi-channel support

### VeroGuard — Unified Guardian
- **Health Watchdog** — 30-second service health checks with tiered recovery (restart → GitHub rollback), cooldown mechanism, and webhook alerts
- **Code Integrity Verification** — SHA256 hash comparison against encrypted manifest, detects unauthorized file modifications and deletions
- **Device Fingerprinting** — Multi-dimensional environment fingerprinting (machine ID, OS, hardware, network)
- **Runtime Protection** — Debugger/ptrace detection, anti-tampering monitoring
- **Heartbeat Reporting** — Periodic status reports to official server with integrity status, fingerprint snapshots, and runtime metrics
- **Remote Command Execution** — 6 command types: warn, lock, shutdown, snapshot, rollback_now, self_destruct
- **Self-Protection** — Dual-process daemon to prevent probe deletion, HMAC-SHA256 signing, AES-256-GCM encrypted communication
- **Nuitka Compilation** — Probe compiled to standalone binary for anti-reverse-engineering protection
- **License Integration** — Probe survival check integrated into license validation for multi-layered protection

### Analytics & Monitoring
- **Analytics** — Built-in visitor tracking, geo-IP (IP2Region), UA parsing, traffic dashboards with China/world map
- **Health Monitoring** — Automated health checks with tiered recovery (restart → rollback), webhook alerts, and daily snapshots (via health_check plugin)
- **System Logs** — Centralized logging with filtering and search

### Security & Access Control
- **JWT SSO** — Single sign-on across all subdomains with HttpOnly cookies
- **Admin Domain Whitelist** — Configurable allowed domains for admin panel access
- **Admin Login Protection** — IP-based rate limiting with automatic ban, multi-client support (browser/desktop/mobile)
- **Puzzle Captcha** — Independent captcha service with behavioral analysis, rate limiting, and risk scoring
- **CSP Headers** — Content Security Policy, X-Frame-Options, X-XSS-Protection
- **Password Policy** — PBKDF2-SHA256 hashing, minimum 10-character password, first-login forced change
- **Enterprise Verification** — Identity verification workflow
- **Sensitive Word Filtering** — Content moderation

### Platform & Infrastructure
- **Plugin System** — Extensible plugin architecture with 5-state lifecycle, dependency resolution, event bus, hook registry, and license management
- **Subscription Management** — Tiered plans, billing, renewal reminders, upgrade funnel
- **License System** — Client-mode subscription expiry lock with renewal page redirect, now enhanced with VeroGuard probe survival verification
- **Multi-Language (i18n)** — YAML-based internationalization with database seeding (zh-CN, en)
- **Brand System** — Unified brand settings (name, logo, favicon, social links)
- **Knowledge Base (RAG)** — Knowledge management with permission control and scheduled maintenance
- **TTS Service** — Text-to-speech via Azure TTS and Edge TTS
- **Feature Flags** — Feature gate service for gradual rollout
- **Invoice Service** — Automated invoice generation
- **One-Click Update** — Admin panel version check and update via git pull + pip install + service restart
- **Static Site Generation** — `staticgen.py` for exporting sites as static HTML

### SDKs & Developer Tools
- **Multi-Platform SDKs** — JavaScript SDKs for WeChat, Douyin, Telegram, LINE + common auth/chat/RAG
- **Docker Support** — Single-container deployment with Nginx + Supervisor
- **Deployment Scripts** — Automated install, update, rollback, health check, seed, and domain configuration

---

## VeroGuard — Unified Guardian Daemon

VeroGuard is the unified guardian daemon that merges health monitoring, copyright protection, and remote management into a single process. It runs as an independent systemd service (`verorun-guardian`) on every deployed instance.

### Architecture

```
+-----------------------------------------------------------+
|                   VeroGuard Guardian                       |
|                   (verorun-guardian)                        |
+-----------------------------------------------------------+
|  +---------------+  +----------------+  +----------------+ |
|  | Channel 1     |  | Channel 2      |  | Channel 3      | |
|  | Health        |  | Integrity      |  | Heartbeat      | |
|  | Watchdog      |  | Verification   |  | Reporter       | |
|  | (30s)         |  | (300s)         |  | (300s)         | |
|  +-------+-------+  +-------+--------+  +-------+--------+ |
|          |                   |                    |         |
|  +-------v-------+  +-------v--------+  +-------v--------+ |
|  | health.py     |  | integrity.py   |  |communicator.py | |
|  | - restart     |  | - SHA256       |  | - HMAC-SHA256  | |
|  | - rollback    |  | - manifest     |  | - AES-256-GCM  | |
|  | - webhook     |  | - violations   |  | - heartbeat    | |
|  +---------------+  +----------------+  +----------------+ |
|                                                             |
|  +---------------+  +----------------+  +----------------+ |
|  | fingerprint   |  | runtime.py     |  | executor.py    | |
|  | .py           |  | - debugger     |  | - warn         | |
|  | - machine ID  |  | - ptrace       |  | - lock         | |
|  | - env info    |  | - sandbox      |  | - shutdown     | |
|  +---------------+  +----------------+  | - self_destruct| |
|                                         +----------------+ |
|  +-------------------------------------------------------+ |
|  | self_protect.py — Dual-process daemon, anti-deletion  | |
|  +-------------------------------------------------------+ |
+-----------------------------------------------------------+
```

### Modules

| Module | File | Purpose |
|--------|------|---------|
| Main Entry | `guardian.py` | Multi-channel scheduling loop, CLI modes (snapshot/rollback) |
| Config | `config.py` | All parameters via env vars with sensible defaults |
| Health Watchdog | `modules/health.py` | Service health checks, tiered recovery (restart → rollback), webhook alerts |
| Integrity | `modules/integrity.py` | SHA256 file verification against encrypted manifest |
| Fingerprint | `modules/fingerprint.py` | Multi-dimensional device fingerprinting |
| Runtime | `modules/runtime.py` | Debugger/ptrace/sandbox detection |
| Communicator | `modules/communicator.py` | HMAC-SHA256 signed, AES-256-GCM encrypted heartbeat |
| Executor | `modules/executor.py` | Remote command execution (6 actions) |
| Self-Protect | `modules/self_protect.py` | Dual-process anti-deletion mechanism |

### Remote Commands

| Command | Description |
|---------|-------------|
| `warn` | Display warning message to user |
| `lock` | Lock the software, redirect to license page |
| `shutdown` | Terminate all services gracefully |
| `snapshot` | Take integrity snapshot immediately |
| `rollback_now` | Force immediate rollback from GitHub |
| `self_destruct` | Remove all VeroRun code (last resort) |

### Deployment

The guardian is compiled to a standalone binary using Nuitka for production deployment:

```bash
python veroguard/compile/build_guardian.py
# Output: veroguard/dist/verorun-guardian.bin
```

Systemd service files are provided in `veroguard/systemd/`:
- `verorun-guardian.service` — Main daemon
- `verorun-guardian-snapshot.service` + `.timer` — Daily integrity snapshot

### Server-Side (Official Use Only)

The VeroGuard Server components run exclusively on VeroRun's official infrastructure:
- **Database Schema** — 5 PostgreSQL tables in `veroguard` schema: `probe_instances`, `integrity_violations`, `remote_commands`, `probe_heartbeats`, `alert_events`
- **Migration Tool** — `veroguard/tools/migrate_veroguard.py` creates the schema
- **API Endpoints** — Integrated into auth-center for heartbeat reception, command issuance, and alert management

---

## AI Infrastructure

### UnifiedLLM Gateway

The `UnifiedLLM` class in `agent_matrix/engine.py` provides a single entry point for all LLM interactions across the system. It supports:

- **7 AI Providers:** DashScope, OpenAI, DeepSeek, OpenRouter, SiliconFlow, Google Gemini, xAI Grok
- **Dual Resolution:** By `provider_model_id` (recommended) or legacy `provider + model`
- **Client Caching:** 5-minute TTL cached OpenAI client instances, thread-safe
- **API Key Resolution:** Priority chain — `provider_api_keys` table (encrypted) → environment variable → `system_config` table
- **Streaming Support:** `chat_stream()` with automatic token usage tracking
- **Tool Calling:** Native `chat_with_tools()` for function-calling agents
- **Unified Logging:** All calls write to `agent_token_logs` + `agent_token_daily`

### AI Budget Gate

Process-level rate limiting and daily token budget enforcement:

| Control | Default | Configurable |
|---------|---------|-------------|
| Daily token cap | 2,000,000 tokens | `ai_budget_daily_tokens` in `system_config` |
| Rate limit | 30 calls/60s | `ai_rate_max_calls` + `ai_rate_window_sec` |
| Fail-open | Yes | Read failures allow calls through |

### LLM Quotas

Fine-grained quota management via `llm_quotas` table with priority: user > model > module > global. Each quota supports daily limits and rate limits independently.

---

## 7-Role Agent Matrix

| Role | Slug | Type | Description |
|------|------|------|-------------|
| Athena | `athena` | Master | Task decomposition, orchestration, reporting, system admin |
| Content | `content` | Sub | Content writing, SEO, social media, translation |
| Shop | `shop` | Sub | Product management, pricing, inventory, orders |
| Builder | `builder` | Sub | Site generation, theme design, page building |
| Steward | `steward` | Sub | Finance, subscriptions, billing, analytics |
| Ops | `ops` | Sub | Deployment, health checks, cloud provisioning |
| Service | `service` | Sub | Customer service, FAQ, tickets, notifications, IM |

**Extended Agents** (auto-registered): Supply Chain (1688 sourcing), Chatbot, Automation, Health Check, Finance, User, Cleaner

### Agent Execution

- **Parallel dispatch:** Sub-tasks execute via `ThreadPoolExecutor` with 300s timeout fuse
- **Self-critique:** Agents self-score output quality; retry up to 3 times if confidence < 0.7
- **Cross-check:** Optional peer review by another sub-agent
- **Intent routing:** Keyword template + chat/tool intent classification

See [agent_matrix/ARCHITECTURE.md](agent_matrix/ARCHITECTURE.md) for detailed design and [agent_matrix/README.md](agent_matrix/README.md) for tools reference.

---

## Plugins

24 built-in plugins with full lifecycle management (5-state: Unknown → Installed → Enabled → Active → Disabled) via the Plugin Manager:

| Plugin | Category | Description |
|--------|----------|-------------|
| `ads` | Marketing | Ad placement and management |
| `ali_api` | E-Commerce | Alibaba/1688 product sourcing, image search, AI review |
| `analytics` | Analytics | Visitor tracking, geo-IP, traffic dashboards, China/world map |
| `captcha_embedded` | Security | Embedded captcha configuration |
| `chatbot` | AI | AI customer service chatbot with multi-channel support and stats |
| `content_factory` | Content | RSS aggregation, AI content processing, skill pushing |
| `coupons` | Marketing | Coupon engine with AI recommendations and scene engine |
| `currency_converter` | Utility | Real-time currency conversion with scheduled rate updates |
| `dev_accounts` | Dev | Developer account management with encrypted credentials |
| `email` | Communication | Email service integration with template support |
| `enterprise_verify` | Security | Enterprise identity verification workflow |
| `health_check` | Monitoring | Automated health checks, alerts, AI auto-fix, metrics |
| `im_gateway` | Communication | Unified IM (Feishu, DingTalk, WeCom, Telegram, LINE, QQ) |
| `logistics` | E-Commerce | Shipping and logistics management |
| `oauth_config` | Auth | Multi-platform OAuth (WeChat, Alipay, Douyin, Google, GitHub, Facebook, Telegram) |
| `order_notify` | E-Commerce | Order notification dispatch |
| `payment` | E-Commerce | Payment gateway configuration (Stripe, PayPal, Alipay, WeChat) |
| `reviews` | E-Commerce | Product review system |
| `site_domains` | Site | Custom domain management |
| `sms` | Communication | SMS service (Aliyun, Twilio) with country code support |
| `social_push` | Marketing | Social media push (Twitter, LinkedIn, Reddit, Telegram Channel) |
| `subscription` | Billing | Subscription plans, billing, and scheduling |
| `verification` | Security | Identity verification service |
| `wishlist` | E-Commerce | User wishlist |

**Plugin Manager features:** Dependency resolution, event bus, hook registry, config validation, license management, store client, runtime enable/disable without restart (gatekeeper-based routing).

---

## Provider System

Pluggable provider abstractions for key services:

| Category | Providers |
|----------|-----------|
| Payment | Stripe, PayPal, Alipay, WeChat Pay |
| SMS | Aliyun, Twilio |
| Logistics | Shippo |
| Social | Twitter, LinkedIn, Reddit, Telegram Channel |

---

## SDKs

JavaScript SDKs for social media mini-program platforms:

| Package | Platform | Description |
|---------|----------|-------------|
| `@verorun/sdk-common` | Cross-platform | Core SDK: Auth, Chat, RAG |
| `@verorun/sdk-wechat` | WeChat | WeChat Mini-Program (`wx.*`) wrapper |
| `@verorun/sdk-douyin` | Douyin | Douyin/Toutiao Mini-Program (`tt.*`) wrapper |
| `@verorun/sdk-telegram` | Telegram | Telegram Bot API + WebApp SDK |
| `@verorun/sdk-line` | LINE | LINE LIFF + Messaging API SDK |

See [sdks/README.md](sdks/README.md) for usage details.

---

> **Codebase:** ~207,000 lines across 886 files (Python, HTML, JS, YAML, Shell, CSS, TypeScript). See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed breakdown.

---

## Directory Structure

```
VeroRunSystem/
├── admin/                  # Admin panel (port 8084)
│   ├── routes/             # Admin route blueprints
│   ├── static/             # CSS, JS, editor, workflow, libs (Chart.js, ECharts, Quill, React Flow)
│   │   ├── css/            # design-system, editor, workflow_editor styles
│   │   ├── js/             # Editor (block actions, color palette, inline editor, nav editor, state manager)
│   │   └── lib/            # React Flow, Chart.js, ECharts, Quill.js, DiceBear
│   └── templates/          # Jinja2 admin templates + partials (50+ sections)
├── auth-center/            # Shared auth, models, services, routes
│   ├── middleware/          # Site domain middleware
│   ├── models/             # Database models (CMS, core)
│   ├── routes/             # Auth, admin, CMS, shop, agents, deployment, knowledge, sessions
│   │   └── subscription/   # Payment gateway integrations (Alipay, PayPal, Stripe, WeChat)
│   └── services/           # JWT, email, SMS, payment, TTS, crypto, license, brand, notification, invoice...
├── main_site/              # Main site backend (port 8081)
│   ├── routes/             # API v1, mini programs, shop public, site routes
│   ├── static/             # CSS, JS, captcha backgrounds, products, favicons
│   └── templates/          # Public site templates (shop, CMS, docs, legal, home, subscribe...)
├── agent_matrix/           # Multi-agent orchestration engine
│   ├── roles/              # 7 agent role YAML definitions
│   ├── prompts/            # 12 agent system prompt templates
│   ├── engine.py           # UnifiedLLM gateway + AI budget gate + quota management
│   ├── orchestrator.py     # Task decomposition, parallel dispatch, result aggregation
│   ├── agent_runner.py     # Agent execution with self-critique and retry
│   ├── intent.py           # Intent classification and routing
│   ├── tools.py            # Agent tool definitions
│   ├── audio.py            # Audio processing
│   ├── models.py           # Agent matrix, tasks, logs, conversations, token tracking
│   └── routes.py           # Flask Blueprint: /admin/agent-matrix/*
├── orchestrator/           # Workflow automation engine (DAG execution)
│   ├── scheduler.py        # Cron-based job scheduler (APScheduler)
│   ├── worker.py           # Worker pool (dedicated + shared)
│   ├── workflow_engine.py  # DAG workflow execution engine
│   ├── workflow_templates.py # Pre-built workflow templates
│   ├── nodes.py            # Node type handlers
│   ├── trigger_dispatch.py # Event trigger dispatch
│   ├── safe_eval.py        # Safe expression evaluation
│   ├── models.py           # Cron jobs, workflows, instances, logs
│   └── routes.py           # Flask Blueprint: /admin/automation/*
├── site_builder/           # AI-powered site generation
│   ├── generators/         # Brand, navigation, pages, theme generators
│   ├── mini_app/           # Mini program generators + templates + deployer + packager
│   │   ├── generators/     # WeChat, Douyin, Telegram, LINE, WhatsApp
│   │   └── templates/      # Platform-specific boilerplate (app.js, app.wxss, etc.)
│   ├── prompts/            # Industry-specific site templates (8 types)
│   └── site_settings/      # Token-based site configuration engine
├── plugin_manager/         # Plugin lifecycle, discovery, event bus, licensing
│   ├── manager.py          # Core PluginManager class (5-state lifecycle)
│   ├── discovery.py        # Plugin auto-discovery
│   ├── event_bus.py        # Publish-subscribe event bus
│   ├── hooks.py            # Hook registry for extensibility
│   ├── license.py          # License validation and management
│   ├── store.py            # Plugin store API client
│   └── routes.py           # Admin API: /admin/plugins/*
├── plugins/                # 24 built-in plugins (each with models, routes, templates, i18n, plugin.json)
├── veroguard/              # VeroGuard unified guardian daemon (NEW)
│   ├── guardian.py         # Main entry point - multi-channel scheduling loop
│   ├── config.py           # All parameters via environment variables
│   ├── modules/            # Core modules
│   │   ├── health.py       # Health watchdog with tiered recovery
│   │   ├── integrity.py    # SHA256 code integrity verification
│   │   ├── fingerprint.py  # Device fingerprinting
│   │   ├── runtime.py      # Debugger/ptrace detection
│   │   ├── communicator.py # Encrypted heartbeat reporting
│   │   ├── executor.py     # Remote command execution
│   │   └── self_protect.py # Dual-process anti-deletion
│   ├── systemd/            # systemd service and timer units
│   ├── compile/            # Nuitka build script for binary compilation
│   ├── tools/              # Database migration for official server
│   └── data/               # Encrypted manifest storage
├── captcha-service/        # Puzzle captcha service (proxied via 8081)
│   └── captcha/            # Behavior analysis, generator, security, store
├── health_guardian/        # systemd unit files for legacy health watchdog
├── providers/              # Pluggable provider abstractions (payment, SMS, logistics, social)
├── sdks/                   # JavaScript SDKs (common, wechat, douyin, telegram, line)
├── i18n/                   # Internationalization (en, zh-CN) with YAML seeding
├── prompts/                # AI coding rules & system prompts (12 rule files)
├── deploy/                 # Deployment scripts, Nginx config, Gunicorn config, seed data
├── nginx-domains/          # Per-domain Nginx site configs
├── scripts/                # Dev utilities (dev_start.py)
├── data/                   # SQLite databases (development)
├── images/                 # Static images (badges, icons)
├── shared/                 # Shared utilities (logging)
├── themes/                 # Theme system (Jinja2 template overrides)
├── static/                 # Shared static assets (captcha backgrounds, CSS, JS)
├── tests/                  # Test suite
├── docs/                   # Design documents and architecture specs (65 docs)
├── GUIDE.md                # Installation & user guide
├── CHANGELOG.md            # Version changelog
├── Dockerfile              # Docker image definition (multi-stage)
├── docker-compose.yml      # Docker Compose config
├── health_guardian.py      # Legacy standalone watchdog daemon (superseded by VeroGuard)
├── auth_server.py          # Main entry point (port 8081, combines auth + site + captcha proxy)
├── run_auth_wsgi.py        # WSGI entry point
├── run_gunicorn.py         # Gunicorn runner
├── package.json            # Node.js dependencies (DiceBear, esbuild, React)
├── requirements.txt        # Python dependencies
└── VERSION                 # Current version
```

---

## Documentation

- **Installation & User Guide:** [GUIDE.md](GUIDE.md)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Deployment Guide:** [deploy/README.md](deploy/README.md)
- **Agent Matrix Architecture:** [agent_matrix/ARCHITECTURE.md](agent_matrix/ARCHITECTURE.md)
- **Agent Matrix Tools:** [agent_matrix/README.md](agent_matrix/README.md)
- **SDKs:** [sdks/README.md](sdks/README.md)
- **Design Docs:** `docs/` directory (65 architecture and planning documents)
- **Online Docs:** [docs.verorun.com](https://docs.verorun.com)

---

## License

Copyright (c) 2026 Fan Jumin. See [LICENSE](LICENSE) for details.
