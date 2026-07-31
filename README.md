# VeroRun

**Multi-Agent AI Operating System** — A full-stack SaaS website builder and business management platform powered by a 7-role Agent collaboration matrix.

VeroRun integrates multi-vendor AI engines, e-commerce operations, CMS content management, AI customer service, automation workflows, cloud provisioning, analytics, health monitoring, and a plugin-based extension system.

> **Version:** 0.39.0
> **Repository:** https://github.com/fanjumin/VeroRunSystem

---

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Site     │    │  Platform   │    │   Admin     │
│   :8081     │    │   :8083     │    │   :8084     │
│ Main Backend│    │ User Console│    │ Admin Panel │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                   ┌──────┴──────┐
                   │   Nginx     │
                   │  Reverse    │
                   │   Proxy     │
                   └──────┬──────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
         yourdomain   platform.*   admin.*
```

### Service Topology

| Port | Domain | Service |
|------|--------|---------|
| 8081 | Main domain `/auth/` `/oauth/` `/user/` `/api/captcha/` | Main site backend + Auth center + Captcha proxy |
| 8083 | `platform.*` `/auth/` `/subscribe` | User console & subscription |
| 8084 | `admin.*` `/admin/` | Admin panel |

Supporting services:

| Port | Service | Notes |
|------|---------|-------|
| 8090 | Captcha Service | Puzzle captcha generation & verification (proxied via 8081) |
| 8085 | Health Guardian | Independent watchdog with tiered recovery & webhook alerts |

### Tech Stack

- **Backend:** Python 3.11+, Flask, Gunicorn
- **Database:** SQLite (primary), PostgreSQL (optional)
- **Process:** PM2, systemd, Supervisor (Docker)
- **Reverse Proxy:** Nginx + Let's Encrypt
- **Cache:** Redis
- **AI:** OpenAI-compatible APIs (DeepSeek, DashScope, OpenAI, SiliconFlow, OpenRouter)
- **Frontend:** Jinja2 templates, vanilla JavaScript, React (workflow editor)
- **JS Tooling:** Node.js (dicebear, esbuild)
- **Container:** Docker, Docker Compose

---

## Quick Start

### One-Click Deploy (Ubuntu 22.04/24.04)

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/install.sh)" -- install your-domain.com
```

Or via git clone:

```bash
git clone https://github.com/fanjumin/VeroRunSystem.git
cd VeroRunSystem
sudo bash deploy/install.sh install your-domain.com
```

For detailed instructions, see [deploy/README.md](deploy/README.md).

### Docker Deploy

```bash
docker compose up -d
```

The Docker image bundles all services (Nginx, app, Supervisor) into a single container exposing port 80. Volumes mount `data/` and `static/` directories for persistence. See [Dockerfile](Dockerfile) and [docker-compose.yml](docker-compose.yml) for details.

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

`scripts/dev_start.py` launches all 4 services (captcha, site, platform, admin) with one command, runs health checks, and prints local URLs and test credentials.

---

## Key Features

- **7-Role Agent Matrix** — Multi-agent collaboration: Athena (coordinator), Content, Shop, Builder, Steward, Ops, Service
- **Plugin System** — Extensible plugin architecture with 24 built-in plugins (see [Plugins](#plugins))
- **Workflow Automation** — Visual drag-and-drop workflow editor with DAG execution (React Flow)
- **AI Site Builder** — Generate complete websites from natural language prompts
- **Mini Program Generation** — Auto-generate WeChat, Douyin, Telegram, LINE, WhatsApp mini programs
- **E-Commerce** — Full shopping cart, orders, payments (Stripe, Alipay, WeChat, PayPal)
- **CMS** — Multi-language content management with AI-assisted writing (zh-CN, en)
- **Analytics** — Built-in visitor tracking, geo-IP (IP2Region), and traffic dashboards
- **Health Monitoring** — Automated health checks with tiered recovery (restart → rollback), webhook alerts, and daily snapshots
- **JWT SSO** — Single sign-on across all subdomains
- **OAuth Multi-Platform** — WeChat, Alipay, Douyin, Google, GitHub, Facebook, Telegram login
- **IM Gateway** — Unified messaging across Feishu, DingTalk, WeCom, Telegram, LINE, QQ
- **Multi-Platform SDKs** — JavaScript SDKs for WeChat, Douyin, Telegram, LINE + common auth/chat/RAG
- **Docker Support** — Single-container deployment with Nginx + Supervisor
- **Puzzle Captcha** — Independent captcha service with behavioral analysis, rate limiting, and risk scoring

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

See [agent_matrix/ARCHITECTURE.md](agent_matrix/ARCHITECTURE.md) for detailed design.

---

## Plugins

24 built-in plugins covering e-commerce, marketing, security, and operations:

| Plugin | Category | Description |
|--------|----------|-------------|
| `ads` | Marketing | Ad placement and management |
| `ali_api` | E-Commerce | Alibaba/1688 product sourcing, image search, AI review |
| `analytics` | Analytics | Visitor tracking, geo-IP, traffic dashboards |
| `captcha_embedded` | Security | Embedded captcha configuration |
| `chatbot` | AI | AI customer service chatbot with multi-channel support |
| `content_factory` | Content | RSS aggregation, AI content processing, skill pushing |
| `coupons` | Marketing | Coupon engine with AI recommendations |
| `currency_converter` | Utility | Real-time currency conversion |
| `dev_accounts` | Dev | Developer account management |
| `email` | Communication | Email service integration |
| `enterprise_verify` | Security | Enterprise identity verification |
| `health_check` | Monitoring | Automated health checks, alerts, auto-fix |
| `im_gateway` | Communication | Unified IM (Feishu, DingTalk, WeCom, Telegram, LINE, QQ) |
| `logistics` | E-Commerce | Shipping and logistics management |
| `oauth_config` | Auth | Multi-platform OAuth (WeChat, Alipay, Douyin, Google, GitHub, Facebook, Telegram) |
| `order_notify` | E-Commerce | Order notification dispatch |
| `payment` | E-Commerce | Payment gateway configuration |
| `reviews` | E-Commerce | Product review system |
| `site_domains` | Site | Custom domain management |
| `sms` | Communication | SMS service (Aliyun, Twilio) |
| `social_push` | Marketing | Social media push (Twitter, LinkedIn, Reddit, Telegram) |
| `subscription` | Billing | Subscription plans and billing |
| `verification` | Security | Identity verification service |
| `wishlist` | E-Commerce | User wishlist |

---

## Provider System

Pluggable provider abstractions for key services:

| Category | Providers |
|----------|-----------|
| Payment | Stripe, PayPal |
| SMS | Aliyun, Twilio |
| Logistics | Shippo |
| Social | Twitter, LinkedIn |

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

## Directory Structure

```
VeroRunSystem/
├── admin/                  # Admin panel (port 8084)
│   ├── routes/             # Admin route blueprints
│   ├── static/             # CSS, JS, editor, workflow, libs
│   └── templates/          # Jinja2 admin templates
├── auth-center/            # Shared auth, models, services, routes
│   ├── middleware/          # Site domain middleware
│   ├── models/             # Database models
│   ├── routes/             # Auth, admin, CMS, shop, agents, deployment
│   └── services/           # JWT, email, SMS, payment, TTS, crypto, license…
├── main_site/              # Main site backend (port 8081)
│   ├── routes/             # API v1, mini programs, shop public, site routes
│   ├── static/             # CSS, JS, captcha, products, favicons
│   └── templates/          # Public site templates (shop, CMS, docs, legal…)
├── agent_matrix/           # Multi-agent orchestration engine
│   ├── roles/              # 7 agent role YAML definitions
│   ├── prompts/            # Agent system prompt templates
│   └── ARCHITECTURE.md     # Agent matrix design doc
├── orchestrator/           # Workflow automation engine (DAG execution)
├── plugins/                # 24 built-in plugins
├── plugin_manager/         # Plugin lifecycle, discovery, event bus, licensing
├── site_builder/           # AI-powered site generation
│   ├── generators/         # Brand, navigation, pages, theme
│   ├── mini_app/           # Mini program generators (WeChat, Douyin, Telegram, LINE, WhatsApp)
│   ├── prompts/            # Industry-specific site templates
│   └── site_settings/      # Token-based site settings
├── captcha-service/        # Puzzle captcha service (port 8090, proxied via 8081)
├── health_guardian/        # Systemd unit files for health watchdog
├── providers/              # Pluggable provider abstractions (payment, SMS, logistics, social)
├── sdks/                   # JavaScript SDKs (common, wechat, douyin, telegram, line)
├── i18n/                   # Internationalization (en, zh-CN)
├── deploy/                 # Deployment scripts, Nginx config, Gunicorn config, seed data
├── nginx-domains/          # Per-domain Nginx site configs
├── prompts/                # AI prompt templates & coding rules
├── scripts/                # Dev utilities (dev_start.py)
├── data/                   # SQLite databases
├── images/                 # Static images (badges, icons)
├── shared/                 # Shared utilities (logging)
├── GUIDE.md                # Installation & user guide
├── CHANGELOG.md            # Version changelog
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose config
├── health_guardian.py      # Standalone watchdog daemon
└── auth_server.py          # Main entry point (port 8081, combines auth + site + captcha proxy)
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