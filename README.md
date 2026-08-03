# VeroRun

**Multi-Agent AI Operating System** — A full-stack SaaS website builder and business management platform powered by a 9-role Agent collaboration matrix with unified LLM gateway, workflow automation, plugin ecosystem with store and license management, dual-region compliance routing, and unified guardian daemon for health monitoring and copyright protection.

VeroRun integrates multi-vendor AI engines (8 providers), e-commerce operations, CMS content management, AI customer service, automation workflows, cloud provisioning, analytics, health monitoring, site builder, mini-program generation, and a plugin-based extension system with full lifecycle management, store, payment, license activation, and subscription support.

> **Version:** 0.45.0
> **Repository:** https://github.com/fanjumin/VeroRunSystem

[![CI](https://github.com/fanjumin/VeroRunSystem/actions/workflows/ci.yml/badge.svg)](https://github.com/fanjumin/VeroRunSystem/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.45.0-blue)](https://github.com/fanjumin/VeroRunSystem/releases)
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
| 8084 | `admin.*` `/admin/` | Admin panel | Plugin management, plugin store, agent matrix, automation, CMS, shop |
| 8085 | — | Health Service (v2.0) | Independent Flask service: liveness/readiness probes + guardian status API, monitored by VeroGuard |
| 8090 | — | Captcha service | Independent puzzle captcha service with behavioral analysis |
| — | — | VeroGuard Guardian | Unified daemon: health watchdog + integrity verification + heartbeat reporting |

**systemd service names:** `verorun-main` (8081), `verorun-auth` (8083), `verorun-admin` (8084), `verorun-health` (8085), `verorun-guardian` (VeroGuard)

### Tech Stack

- **Backend:** Python 3.11+, Flask, Gunicorn
- **Database:** PostgreSQL (production), SQLite (development/fallback)
- **Process:** systemd, Supervisor (Docker)
- **Reverse Proxy:** Nginx + Let's Encrypt
- **Cache:** Redis
- **AI Engine:** OpenAI-compatible APIs — DashScope, OpenAI, DeepSeek, OpenRouter, SiliconFlow, Google Gemini, xAI Grok, Zhipu GLM (8 providers) with UnifiedLLM gateway
- **AI Infrastructure:** Token budget gate (daily quota + rate limiting), LLM quota management, encrypted API key storage
- **Frontend:** Jinja2 templates, vanilla JavaScript, React Flow (workflow editor), Chart.js, ECharts, Quill.js (rich text)
- **JS Tooling:** Node.js (DiceBear avatars, esbuild)
- **Container:** Docker, Docker Compose (single-container with Nginx + Supervisor)
- **Guardian Compilation:** Nuitka (standalone binary for anti-tampering)
- **Image Generation:** FLUX.1-pro (SiliconFlow), Tongyi Wanxiang

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

#### Region Selection

For deployments in China, use the `--region` flag to route API calls to domestic endpoints:

```bash
sudo bash deploy/install.sh install your-domain.com --region=cn
```

Supported values: `cn` (China mainland, routes to `api.verorun.cn`) or `global` (default, routes to `api.verorun.com`).

The install script provisions PostgreSQL, creates the `verorun` system user, sets up a Python virtual environment, generates `.env` with auto-generated secrets (including `PLUGIN_LICENSE_SECRET`, `CAPTCHA_SECRET_KEY`, `DEV_ACCOUNTS_ENCRYPTION_KEY`, `LICENSE_SERVER_SECRET`, `PROBE_SECRET`), creates systemd services, configures Nginx, and optionally seeds initial data.

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
- **9-Role Agent Matrix** — Multi-agent collaboration: Athena (coordinator), Content, Business, Builder, Finance, Ops, Service, plus Vision (image analysis), Creative (image generation), Supply Chain, Chatbot, Automation, Health Check, CMS, and User agents
- **Agent Discussion v2.0** — 4-stage collaborative discussion protocol: Planner generates execution plan, Reviewer critiques, Planner revises, Decider approves or rejects
- **UnifiedLLM Gateway** — Single entry point for all LLM calls across 8 AI providers with client caching and TTL
- **AI Budget Gate** — Daily token budget cap + per-minute rate limiting with fail-open design
- **LLM Quotas** — Fine-grained quota management: user-level, model-level, module-level, global-level
- **Provider API Key Management** — Encrypted storage of API keys with multi-provider support
- **Token Monitoring** — Real-time token usage tracking, daily aggregation, and cost analytics

### Site Building & Content
- **AI Site Builder** — Generate complete websites from natural language prompts with industry-specific templates (tech company, restaurant, education, law firm, etc.)
- **Mini Program Generation** — Auto-generate WeChat, Douyin, Telegram, LINE, WhatsApp mini programs with preview and packaging
- **Token-Based Site Settings** — Dynamic site configuration via tokenized rendering engine
- **Theme System** — Jinja2 ChoiceLoader-based theme override system with zero-downtime switching
- **CMS** — Multi-language content management with AI-assisted writing (zh-CN, en)
- **Content Factory** — RSS aggregation, AI content processing, skill pushing, review pipeline

### Workflow & Automation
- **Workflow Automation** — Visual drag-and-drop workflow editor with DAG execution (React Flow), 12 node types (AI agent, data collect, AI process, condition, approval, publish, notify, wait, sub-workflow, market check, HTTP request, script)
- **Workflow Templates** — Pre-built workflow templates for common automation scenarios (daily content collection, etc.)
- **Cron Scheduler** — Built-in cron job engine with pause/resume/toggle
- **Worker Pool** — Multi-level worker pool: dedicated (4 threads) + shared (8 threads), priority-based execution (CRITICAL/HIGH/NORMAL/LOW)
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
- **Social Push** — Multi-platform content push (Twitter, LinkedIn, Reddit, Telegram Channel, Toutiao, Weibo)
- **Email Service** — Email integration with template support
- **SMS Service** — Aliyun and Twilio SMS providers, auto-routing by market (CN to Aliyun, INTL to Twilio)
- **Chatbot** — AI customer service chatbot with multi-channel support

### Plugin Store & License System
- **Plugin Store** — Browse, search, and install plugins from the remote store with local cache fallback
- **Plugin Downloader** — Secure download with SHA256 integrity verification, Zip Slip protection, 200MB size limit, 120s timeout. Supports `.zip`, `.tar.gz`, `.tgz`
- **Version Compatibility** — Semver-based minimum app version check before install, preventing incompatible plugin deployments
- **License Engine** — Online validation + offline token dual-channel verification. RSA-2048 signed offline tokens with 72-hour grace period. Free plugins bypass license checks
- **License Activation** — Remote API activation with automatic offline fallback (7-day local token). Site ID binding via MAC + hostname hash
- **Payment Integration** — Alipay face-to-face QR payment for plugin purchases. Unified payment router with per-channel provider dispatch
- **Subscription Management** — Monthly/yearly plugin subscriptions with auto-renewal, cancellation, and expiration handling
- **Coupon System** — Percentage and fixed-amount discounts, per-plugin applicability, expiration support
- **Review & Rating** — Purchase-verified review system with 5-star ratings, admin reply, and aggregated store scores
- **Store Admin** — Full CRUD for store plugin listings, toggle enable/disable, manage reviews

### Dual-Region Compliance Routing
- **Region Router** (`region.py`) — Unified regional routing module. All remote service URLs are dynamically resolved based on `VERORUN_REGION` environment variable (`cn` or `global`)
- **API Endpoints** — `cn` routes to `api.verorun.cn`, `global` routes to `api.verorun.com`. Individual URL overrides available via environment variables
- **VeroGuard Heartbeat** — Region-aware heartbeat reporting endpoint, with Nuitka-compilation-safe fallback
- **License Service Heartbeat** — Subscription heartbeat API dynamically routed per region, with standalone deployment fallback
- **Install Script** — `--region=cn|global` flag sets `VERORUN_REGION` in `.env` during deployment
- **Backward Compatible** — All region-aware components support `REMOTE_LICENSE_URL` / `GUARDIAN_REMOTE_URL` / `APP_HEARTBEAT_URL` environment variable overrides

### VeroGuard — Unified Guardian
- **Health Watchdog** — 30-second service health checks with tiered recovery (restart, GitHub rollback), cooldown mechanism, and webhook alerts
- **Code Integrity Verification** — SHA256 hash comparison against encrypted manifest, detects unauthorized file modifications and deletions
- **Device Fingerprinting** — Multi-dimensional environment fingerprinting (MAC address, CPU serial, disk serial, machine ID)
- **Runtime Protection** — Debugger/ptrace detection, suspicious module detection (frida/pdb/pydevd/debugpy/mock), environment variable tampering detection (LD_PRELOAD/PYTHONPATH)
- **Heartbeat Reporting** — Periodic status reports to official server with AES-256-GCM encryption, HMAC-SHA256 signing, TLS 1.3, and Nonce+Timestamp anti-replay (5-minute window)
- **Remote Command Execution** — 6 command types: `warn` (display warning), `lock_ai` (disable AI), `lock_full` (maintenance mode 503), `shutdown` (stop all services), `self_destruct` (remove guardian files), `update_config` (update runtime parameters)
- **Self-Protection** — Dual-process daemon: guardian monitors business services, self_protect monitors guardian itself. Pipe/pidfile heartbeat monitoring, parent death triggers auto-restart
- **Nuitka Compilation** — Probe compiled to standalone binary for anti-reverse-engineering protection
- **License Integration** — Probe survival check integrated into license validation for multi-layered protection

### Captcha Service
- **Independent Service** — Dedicated captcha service on port 8090, proxied via main site (8081) for unified entry
- **Puzzle Captcha** — Dynamic puzzle-style CAPTCHA with random background images and shapes (circle, triangle, square, diamond, ellipse)
- **Behavioral Analysis** — Trajectory analysis: duration, velocity curve, acceleration changes. Outputs human_score (0 to 1) and risk_level (low/medium/high)
- **HMAC-SHA256 Tokens** — Signed challenge tokens with coordinates, image ID, puzzle dimensions, and expiration
- **Redis Storage** — Challenge state storage with in-memory dictionary fallback when Redis is unavailable
- **Rate Limiting** — IP-based: 5 failures per 5-minute window, risk threshold 0.7

### Analytics & Monitoring
- **Analytics** — Built-in visitor tracking, geo-IP (IP2Region), UA parsing, traffic dashboards with China/world map
- **Health Monitoring** — Automated health checks with tiered recovery (restart, rollback), webhook alerts, AI auto-fix, and daily snapshots (via health_check plugin)
- **System Logs** — Centralized logging with filtering and search

### Security & Access Control
- **JWT SSO** — Single sign-on across all subdomains with HttpOnly cookies
- **Admin Domain Whitelist** — Configurable allowed domains for admin panel access
- **Admin Login Protection** — IP-based rate limiting with automatic ban, multi-client support (browser/desktop/mobile)
- **Puzzle Captcha** — Independent captcha service with behavioral analysis, rate limiting, and risk scoring
- **CSP Headers** — Content Security Policy, X-Frame-Options, X-XSS-Protection
- **Password Policy** — PBKDF2-SHA256 hashing, minimum 10-character password, 4-of-4 character classes required, first-login forced change
- **Enterprise Verification** — Identity verification workflow
- **Sensitive Word Filtering** — Multi-category content moderation (political, violence, adult, spam, abuse, financial fraud)
- **Name Validation** — Username and display name validation per Chinese internet regulations
- **AI Comment Review** — Local sensitive word filter + Qwen semantic analysis for auto-approve/pending/reject

### Platform & Infrastructure
- **Plugin System** — Extensible plugin architecture with 6-state lifecycle (Unknown, Installed, Enabled, Active, Disabled, Uninstalled), dependency resolution (topological sort with Kahn's algorithm), circular dependency detection, event bus (30+ system events), hook registry (Action + Filter, WordPress-style), config validation (JSON Schema Draft-07), independent per-plugin logging (rotation: 5MB x 3 backups)
- **Subscription Management** — Tiered plans, billing, renewal reminders (7/3/1 days), upgrade funnel (14-day trial, 80% usage alerts), automated invoice generation (PDF)
- **License System** — Client-mode subscription expiry lock with renewal page redirect, enhanced with VeroGuard probe survival verification
- **Feature Gates** — Three-tier feature gating (free/paid/premium), daily call limits, plugin quantity limits, watermark control
- **Module Policy Engine** — Per-module trial/paid policies with automated trial expiration and refund window scanning
- **Multi-Language (i18n)** — YAML-based internationalization with database seeding (zh-CN, en)
- **Brand System** — Unified brand settings (name, logo, favicon, social links) shared across all 4 services
- **Knowledge Base (RAG)** — Knowledge management with role-based permission control and scheduled maintenance
- **TTS Service** — Text-to-speech via Azure TTS (400+ neural voices, 140+ languages) and Edge TTS (free, no API key)
- **Feature Flags** — Feature gate service for gradual rollout
- **Invoice Service** — Automated PDF invoice generation with Chinese/Western font support
- **One-Click Update** — Admin panel version check and update via git pull + pip install + service restart
- **Static Site Generation** — `staticgen.py` for exporting sites as static HTML
- **Deployment Config** — Centralized environment variable management for domains, email, brand, market, language, currency
- **Notification Service** — Unified notification dispatch with template variable substitution, 10/minute rate limit

### SDKs & Developer Tools
- **Multi-Platform SDKs** — JavaScript SDKs for WeChat, Douyin, Telegram, LINE + common auth/chat/RAG
- **Docker Support** — Single-container deployment with Nginx + Supervisor
- **Deployment Scripts** — Automated install, update, restart, rollback, health check, seed, and domain configuration

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
|  | - restart     |  | - SHA256       |  | - AES-256-GCM  | |
|  | - rollback    |  | - manifest     |  | - HMAC-SHA256  | |
|  | - webhook     |  | - violations   |  | - TLS 1.3      | |
|  +---------------+  +----------------+  | - anti-replay  | |
|                                         +----------------+ |
|  +---------------+  +----------------+  +----------------+ |
|  | fingerprint   |  | runtime.py     |  | executor.py    | |
|  | .py           |  | - debugger     |  | - warn         | |
|  | - MAC addr    |  | - ptrace       |  | - lock_ai      | |
|  | - CPU serial  |  | - suspicious   |  | - lock_full    | |
|  | - disk serial |  |   modules      |  | - shutdown     | |
|  +---------------+  | - env tamper   |  | - self_destruct| |
|                     +----------------+  | - update_config| |
|                                         +----------------+ |
|  +-------------------------------------------------------+ |
|  | self_protect.py — Dual-process daemon, anti-deletion  | |
|  |   guardian monitors services | self_protect monitors  | |
|  |   guardian | pipe/pidfile heartbeat | auto-restart    | |
|  +-------------------------------------------------------+ |
+-----------------------------------------------------------+
```

### Modules

| Module | File | Purpose |
|--------|------|---------|
| Main Entry | `guardian.py` | Multi-channel scheduling loop, CLI modes (snapshot/rollback) |
| Config | `config.py` | All parameters via env vars with sensible defaults, region-aware remote URL |
| Health Watchdog | `modules/health.py` | Service health checks, tiered recovery (restart, rollback), webhook alerts |
| Integrity | `modules/integrity.py` | SHA256 file verification against AES-GCM encrypted manifest |
| Fingerprint | `modules/fingerprint.py` | Multi-dimensional device fingerprinting (MAC, CPU serial, disk serial) |
| Runtime | `modules/runtime.py` | Debugger/ptrace/suspicious module detection, environment variable tampering |
| Communicator | `modules/communicator.py` | AES-256-GCM encrypted, HMAC-SHA256 signed heartbeat with TLS 1.3 + anti-replay |
| Executor | `modules/executor.py` | Remote command execution (6 actions: warn, lock_ai, lock_full, shutdown, self_destruct, update_config) |
| Self-Protect | `modules/self_protect.py` | Dual-process anti-deletion: guardian and self_protect mutual monitoring |

### Remote Commands

| Command | Description |
|---------|-------------|
| `warn` | Display warning message to user |
| `lock_ai` | Disable all AI features |
| `lock_full` | Put entire site into maintenance mode (503) |
| `shutdown` | Terminate all services gracefully |
| `self_destruct` | Remove guardian daemon files |
| `update_config` | Update runtime configuration parameters |

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

## Health Service (v2.0)

The Health Service is an independent Flask service on port 8085, decoupled from the admin panel (8084) to ensure health checks survive admin failures. It is monitored by VeroGuard's health watchdog.

- **Liveness Probe** — `GET /health` returns service status
- **Readiness Probe** — `GET /ready` checks database connectivity and returns 503 if unavailable
- **Guardian Status API** — `GET /api/guardian/status` exposes VeroGuard daemon running state

See `health_service/app.py` for the implementation and `health_service/runner.py` for the standalone Waitress WSGI runner.

---

## AI Infrastructure

### UnifiedLLM Gateway

The `UnifiedLLM` class in `agent_matrix/engine.py` provides a single entry point for all LLM interactions across the system. It supports:

- **8 AI Providers:** DashScope, OpenAI, DeepSeek, OpenRouter, SiliconFlow, Google Gemini, xAI Grok, Zhipu GLM
- **Dual Resolution:** By `provider_model_id` (recommended) or legacy `provider + model`
- **Client Caching:** 5-minute TTL cached OpenAI client instances, thread-safe
- **API Key Resolution:** Priority chain — `provider_api_keys` table (encrypted), environment variable, `system_config` table
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

## 9-Role Agent Matrix

| Role | Slug | Type | Description |
|------|------|------|-------------|
| Athena | `athena` | Master | Task decomposition, orchestration, reporting, system admin |
| Content | `content` | Sub | Content writing, SEO, social media, translation |
| Business | `business` | Sub | Product management, pricing, inventory, orders, supply chain |
| Builder | `builder` | Sub | Site generation, theme design, page building |
| Finance | `finance` | Sub | Finance, subscriptions, billing, analytics, plans |
| Ops | `ops` | Sub | Deployment, health checks, cloud provisioning |
| Service | `service` | Sub | Customer service, FAQ, tickets, notifications, IM |
| Vision | `vision` | Sub | Image analysis, OCR, chart interpretation, visual QA (GLM-4V-Plus) |
| Creative | `creative` | Sub | Text-to-image generation, creative visual design, illustration (FLUX.1-pro) |

**Extended Agents** (auto-registered): Supply Chain (1688 sourcing), Chatbot, Automation, Health Check, CMS, Cleaner

### Agent Discussion v2.0

Four-stage collaborative discussion protocol for complex tasks:
- **Planner** — Generates initial execution plan with task decomposition
- **Reviewer** — Critiques the plan for completeness and correctness
- **Planner (Revise)** — Revises the plan based on review feedback
- **Decider** — Final approval or rejection with reasoning

### Agent Execution

- **Parallel dispatch:** Sub-tasks execute via `ThreadPoolExecutor` with 300s timeout fuse
- **Deep mode:** Enhanced reasoning with multi-step chain-of-thought
- **Image mode:** Automatic image processing pipeline injection
- **Self-critique:** Agents self-score output quality; retry up to 3 times if confidence < 0.7
- **Cross-check:** Optional peer review by another sub-agent
- **Intent routing:** Keyword template + chat/tool intent classification
- **LLM Response Cache:** Session summary caching with automatic TTL and capacity limits

See [agent_matrix/ARCHITECTURE.md](agent_matrix/ARCHITECTURE.md) for detailed design and [agent_matrix/README.md](agent_matrix/README.md) for tools reference.

---

## Plugin Manager

### Lifecycle Management

The Plugin Manager (`plugin_manager/manager.py`) orchestrates the full 6-state plugin lifecycle:

```
UNKNOWN -> INSTALLED -> ENABLED -> ACTIVE -> DISABLED -> UNINSTALLED
```

- **Discovery:** Auto-scan `plugins/` directory, parse `plugin.json` metadata
- **Dependency Resolution:** Topological sort with Kahn's algorithm, global circular dependency detection
- **Event Bus:** 30+ predefined system events (APP_READY, USER_REGISTERED, ORDER_CREATED, PLUGIN_INSTALLED, etc.), thread-pool async dispatch
- **Hook System:** WordPress-style Action + Filter hooks with priority support (default 10)
- **Config Validation:** JSON Schema Draft-07 validation with automatic type coercion fallback
- **Per-Plugin Logging:** Independent log files with rotation (5MB x 3 backups, date-based)

### Plugin Store

| Feature | Description |
|---------|-------------|
| Browse & Search | Remote store API with local cache fallback, category filtering, sorting (downloads/rating/newest/price) |
| Install | One-click download + extract + install with SHA256 integrity check and Zip Slip protection |
| Version Check | Semver minimum app version validation before install, dedicated compatibility endpoint |
| Purchase | Integrated payment flow: Alipay QR code, order tracking, webhook callback, auto license activation |
| Coupons | Percentage and fixed-amount discounts applied at checkout |
| Reviews | 5-star rating system, purchase-verified reviews, admin reply, aggregated store scores |
| Subscriptions | Monthly/yearly auto-renewal, cancel (immediate or end-of-period), manual renewal |
| Admin CRUD | Full store plugin listing management, toggle enable/disable |

### License System

| Feature | Description |
|---------|-------------|
| Online Validation | Remote License Service API call with HMAC-signed requests |
| Offline Token | RSA-2048 signed local token with 72-hour grace period, site ID binding |
| Site ID | MD5(MAC + hostname) unique per deployment |
| Free Plugin Bypass | Free plugins skip license checks entirely |
| Activation | Remote API activation with automatic 7-day offline fallback |
| Deactivation | Local record removal + remote notification |
| Backward Compatible | `REMOTE_LICENSE_URL` env var override for custom license servers |

---

## Plugins

25 built-in plugins with full lifecycle management (6-state: Unknown, Installed, Enabled, Active, Disabled, Uninstalled) via the Plugin Manager:

| Plugin | Category | Description |
|--------|----------|-------------|
| `ads` | Marketing | Ad placement and management with AI tools |
| `ali_api` | E-Commerce | Alibaba/1688 product sourcing, image search, AI review |
| `analytics` | Analytics | Visitor tracking, geo-IP, traffic dashboards, China/world map, workflow nodes |
| `captcha_embedded` | Security | Embedded captcha configuration |
| `chatbot` | AI | AI customer service chatbot with multi-channel support and stats |
| `content_factory` | Content | RSS aggregation, AI content processing, skill pushing |
| `coupons` | Marketing | Coupon engine with AI recommendations and scene engine |
| `currency_converter` | Utility | Real-time currency conversion with scheduled rate updates |
| `dev_accounts` | Dev | Developer account management with encrypted credentials |
| `email` | Communication | Email service integration with template support |
| `enterprise_verify` | Security | Enterprise identity verification workflow with admin and user routes |
| `health_check` | Monitoring | Automated health checks, alerts, AI auto-fix, metrics, scheduled snapshots |
| `im_gateway` | Communication | Unified IM (Feishu, DingTalk, WeCom, Telegram, LINE, QQ) with adapter architecture |
| `logistics` | E-Commerce | Shipping and logistics management |
| `oauth_config` | Auth | Multi-platform OAuth (WeChat, Alipay, Douyin, Google, GitHub, Facebook, Telegram) |
| `order_notify` | E-Commerce | Order notification dispatch |
| `payment` | E-Commerce | Payment gateway configuration (Stripe, PayPal, Alipay, WeChat) |
| `reviews` | E-Commerce | Product review system |
| `site_domains` | Site | Custom domain management |
| `sms` | Communication | SMS service (Aliyun, Twilio) with country code support |
| `social_push` | Marketing | Social media push (Twitter, LinkedIn, Reddit, Telegram Channel) |
| `subscription` | Billing | Subscription plans, billing, scheduling, integrated payment gateways |
| `vault` | Utility | Data backup and upload service |
| `verification` | Security | Identity verification service |
| `wishlist` | E-Commerce | User wishlist |

**Plugin Manager features:** 6-state lifecycle, dependency resolution (Kahn's algorithm), event bus (30+ events), Action + Filter hook system, JSON Schema config validation, license management, store client with download/install/purchase flow, payment integration, coupon system, review system, per-plugin logging, runtime enable/disable without restart (gatekeeper-based routing).

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

> **Codebase:** ~197,000 lines across 905 files (Python, HTML, JS, YAML, Shell, CSS, TypeScript). See [GUIDE.md](GUIDE.md) for installation and user guide.

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
│   └── services/           # 30+ services: JWT, email, SMS, payment, TTS, crypto, license, brand, notification, invoice, feature gate, upgrade funnel, pricing, module policy, verification, name validation, password validation, sensitive words, comment review, KB permission, deployment config, social push, AI content, agent engine, avatar, unified auth, unified subscription, renewal reminder, completion
├── main_site/              # Main site backend (port 8081)
│   ├── routes/             # API v1, mini programs, shop public, site routes
│   ├── static/             # CSS, JS, captcha backgrounds, products, favicons
│   └── templates/          # Public site templates (shop, CMS, docs, legal, home, subscribe...)
├── agent_matrix/           # Multi-agent orchestration engine
│   ├── roles/              # 9 agent role YAML definitions (Athena, Content, Business, Builder, Finance, Ops, Service, Vision, Creative)
│   ├── prompts/            # 14 agent system prompt templates (7 core + 7 extended + 3 discussion)
│   ├── engine.py           # UnifiedLLM gateway + AI budget gate + quota management
│   ├── orchestrator.py     # Task decomposition, parallel dispatch, result aggregation
│   ├── agent_runner.py     # Agent execution with self-critique and retry
│   ├── intent.py           # Intent classification and routing
│   ├── tools.py            # Agent tool definitions
│   ├── audio.py            # Audio processing
│   ├── cache_utils.py      # LLM response cache + session summary cache
│   ├── models.py           # Agent matrix, tasks, logs, conversations, token tracking
│   └── routes.py           # Flask Blueprint: /admin/agent-matrix/*
├── orchestrator/           # Workflow automation engine (DAG execution)
│   ├── scheduler.py        # Cron-based job scheduler (APScheduler)
│   ├── worker.py           # Multi-level worker pool (dedicated + shared, priority queue)
│   ├── workflow_engine.py  # DAG workflow execution engine
│   ├── workflow_templates.py # Pre-built workflow templates (daily content collection, etc.)
│   ├── nodes.py            # 12 node type handlers (ai_agent, data_collect, ai_process, condition, approval, publish, notify, wait, sub_workflow, market_check, http_request, script)
│   ├── trigger_dispatch.py # Event trigger dispatch
│   ├── safe_eval.py        # Sandboxed expression evaluation
│   ├── models.py           # Cron jobs, workflows, instances, logs
│   └── routes.py           # Flask Blueprint: /admin/automation/*
├── site_builder/           # AI-powered site generation
│   ├── generators/         # Brand, navigation, pages, theme generators
│   ├── mini_app/           # Mini program generators + templates + deployer + packager + preview renderer
│   │   ├── generators/     # WeChat, Douyin, Telegram, LINE, WhatsApp
│   │   └── templates/      # Platform-specific boilerplate
│   ├── prompts/            # Industry-specific site templates (8 types)
│   └── site_settings/      # Token-based site configuration engine
├── plugin_manager/         # Plugin lifecycle, discovery, store, license, payment, region routing
│   ├── manager.py          # Core PluginManager class (6-state lifecycle)
│   ├── discovery.py        # Plugin auto-discovery with semver dependency resolution
│   ├── deps.py             # Dependency resolver (Kahn topological sort, cycle detection)
│   ├── event_bus.py        # Publish-subscribe event bus (30+ system events)
│   ├── hooks.py            # Action + Filter hook registry (WordPress-style, priority support)
│   ├── injectors.py        # System-critical path hook injection points
│   ├── license.py          # License engine (online + offline dual-channel, 72h grace)
│   ├── store.py            # Plugin store API client with local cache
│   ├── downloader.py       # Secure plugin downloader (SHA256, Zip Slip protection)
│   ├── payment.py          # Payment router + Alipay face-to-face provider
│   ├── subscription.py     # Plugin subscription management (monthly/yearly)
│   ├── coupons.py          # Coupon engine (percentage + fixed-amount)
│   ├── routes.py           # 40+ REST endpoints: plugins, store, license, payment, coupons, reviews, subscriptions
│   ├── region.py           # Dual-region routing (cn/global API endpoint resolution)
│   ├── models.py           # Plugin registry data models (PG)
│   ├── models_store.py     # License + store data models (plugin_licenses, store_plugins, plugin_reviews, coupon_codes, plugin_subscriptions)
│   ├── config_validator.py # JSON Schema Draft-07 config validation
│   ├── exceptions.py       # Custom exception hierarchy (8 exception types)
│   ├── logger.py           # Per-plugin independent logging (rotation: 5MB x 3)
│   └── base.py             # Plugin system base classes
├── plugins/                # 25 built-in plugins (each with models, routes, templates, i18n, plugin.json)
├── veroguard/              # VeroGuard unified guardian daemon
│   ├── guardian.py         # Main entry point - multi-channel scheduling loop
│   ├── config.py           # All parameters via environment variables, region-aware remote URL
│   ├── modules/            # 7 core modules
│   │   ├── health.py       # Health watchdog with tiered recovery
│   │   ├── integrity.py    # SHA256 code integrity verification (AES-GCM manifest)
│   │   ├── fingerprint.py  # Device fingerprinting (MAC, CPU, disk)
│   │   ├── runtime.py      # Debugger/ptrace/suspicious module/env tamper detection
│   │   ├── communicator.py # AES-256-GCM + HMAC-SHA256 encrypted heartbeat, TLS 1.3, anti-replay
│   │   ├── executor.py     # Remote command execution (6 commands)
│   │   └── self_protect.py # Dual-process anti-deletion mutual monitoring
│   ├── systemd/            # systemd service and timer units
│   ├── compile/            # Nuitka build script for binary compilation
│   ├── tools/              # Database migration + manifest builder for official server
│   └── data/               # Encrypted manifest storage
├── health_service/         # Health Service v2.0 (port 8085)
│   ├── app.py              # Flask app: /health (liveness), /ready (readiness), /api/guardian/status
│   ├── runner.py           # Standalone runner (Waitress WSGI)
│   └── requirements.txt    # Dependencies (Flask, Waitress, psycopg2)
├── captcha-service/        # Independent puzzle captcha service (port 8090, proxied via 8081)
│   └── captcha/            # Behavior analysis, generator, security (HMAC tokens), store (Redis)
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
- **Online Docs:** [docs.verorun.com](https://docs.verorun.com)

---

## License

Copyright (c) 2026 Fan Jumin. See [LICENSE](LICENSE) for details.