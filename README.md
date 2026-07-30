# VeroRun

**Multi-Agent AI Operating System** — A full-stack SaaS website builder and business management platform powered by a 7-role Agent collaboration matrix.

VeroRun integrates multi-vendor AI engines, e-commerce operations, CMS content management, AI customer service, automation workflows, cloud provisioning, analytics, health monitoring, and a plugin-based extension system.

> **Version:** 0.37.6
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
| 8081 | Main domain `/auth/oauth/` `/user/` | Main site backend |
| 8083 | `platform.*` `/auth/` `/subscribe` | Auth & subscription |
| 8084 | `admin.*` `/admin/` | Admin panel |

### Tech Stack

- **Backend:** Python 3.12, Flask, Gunicorn
- **Database:** SQLite (primary), PostgreSQL (optional)
- **Process:** PM2, systemd
- **Reverse Proxy:** Nginx + Let's Encrypt
- **Cache:** Redis
- **AI:** Openai-compatible APIs (DeepSeek, DashScope, OpenAI)
- **Frontend:** Jinja2 templates, vanilla JavaScript

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

### Local Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # configure your keys
python app.py
```

---

## Key Features

- **7-Role Agent Matrix** — Multi-agent collaboration for site building, content, shop, and operations
- **Plugin System** — Extensible plugin architecture with 20+ built-in plugins
- **Workflow Automation** — Visual drag-and-drop workflow editor with DAG execution
- **AI Site Builder** — Generate complete websites from natural language prompts
- **Mini Program Generation** — Auto-generate WeChat/Douyin mini programs
- **E-Commerce** — Full shopping cart, orders, payments (Stripe/Alipay/WeChat)
- **CMS** — Multi-language content management with AI-assisted writing
- **Analytics** — Built-in visitor tracking, geo-IP, and traffic dashboards
- **Health Monitoring** — Automated health checks with alerting and auto-rollback
- **JWT SSO** — Single sign-on across all subdomains

---

## Directory Structure

```
VeroRunSystem/
├── admin/              # Admin panel (port 8084)
├── auth-center/        # Authentication & user services
├── main_site/          # Main site backend (port 8081)
├── agent_matrix/       # Multi-agent orchestration engine
├── orchestrator/       # Workflow automation engine
├── plugins/            # Plugin system (20+ plugins)
├── plugin_manager/     # Plugin lifecycle management
├── site_builder/       # AI-powered site generation
├── i18n/               # Internationalization (en, zh-CN)
├── deploy/             # Deployment scripts & configs
├── prompts/            # AI prompt templates
├── shared/             # Shared utilities
└── docs/               # Documentation
```

---

## License

Copyright (c) 2026 Fan Jumin. See [LICENSE](LICENSE) for details.

---

## Documentation

Full documentation is available at [docs.verorun.com](https://docs.verorun.com).
