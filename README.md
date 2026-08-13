# VeroRun — Multi-Agent AI Engine Operating System

[![Version](https://img.shields.io/badge/version-0.56.5-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![Plugins](https://img.shields.io/badge/plugins-30-orange.svg)]()

**VeroRun is a Multi-Agent AI engine operating system deployed on a customer-owned server — a general-purpose intelligent execution engine designed for enterprise on-premises deployment.**

The engine core provides five universal intelligent execution primitives — **agent collaboration, knowledge retrieval, process orchestration, model access, and asset protection** — via six core kernel components. Knowledge-base customer service, content production, business operations, and any other business form run as plugins on top of the kernel, as application instances carried by the base. The same base supports multiple intelligent front-ends (WWW websites, mini programs, IM bots, internal business portals, data dashboards, and more).

---

## Key Features

- **Orchestrable Multi-Role Agent Matrix**: Athena (master) + 8 sub-roles, a multi-specialist agent team with role division and task-decomposition orchestration, plus auto-registration of extended agents.
- **Four-Stage Discussion Protocol (Agent Discussion v2.0)**: Planner → Reviewer → Revise → Decider, separating generation from review so that errors are intercepted before they happen.
- **Dynamic Prompt System**: a database-driven `PromptResolver` with four-layer assembly, scenario differentiation, and multi-version management.
- **Knowledge Base & Memory Engine (CogEvolution)**: vector retrieval (RAG), layered memory, Reflexion learning, and Prompt Evolution, forming a "memory → reflection → optimization → behavioral evolution" loop.
- **Visual Workflow Engine**: DAG node orchestration, Cron scheduling, and tiered worker pools — a general execution carrier for any process.
- **Multi-Provider LLM Gateway (UnifiedLLM)**: a provider-agnostic unified API, 7 native + 2 dynamically resolved providers, transparent model substitution, automatic failover, model addressing, key management, budget gate, and 4-level quota.
- **VeroGuard Guard Layer**: health monitoring + integrity verification + encrypted heartbeat, dual-process mutual protection, and client-side asset protection.
- **Plugin Ecosystem**: 30 built-in plugins carry any business form, with full lifecycle management, plugin marketplace, and licensing engine.

The kernel's design principle is **business semantics never invade the kernel**: business rules are declared entirely by plugins, and adding a business capability is equivalent to assembling a plugin — never touching kernel code.

---

## Architecture

### Engine Base vs. Application Layer

> **The engine base defines "how it runs"; application plugins define "what runs".**

```text
┌──────────────────────────────────────────────────────────────┐
│ Application Layer  Plugin apps: knowledge · content · commerce│
│                   · communications · ops …                    │
│                   30 built-in plugins; any business via plugins│
├──────────────────────────────────────────────────────────────┤
│ Engine Base       Multi-role AI Agent Matrix + Discussion     │
│                   Knowledge memory (vector) · Workflow · PromptResolver │
├──────────────────────────────────────────────────────────────┤
│ Runtime Layer     UnifiedLLM gateway · Plugin manager · Themes │
├──────────────────────────────────────────────────────────────┤
│ Guard Layer       VeroGuard unified daemon (health/integrity/ │
│                   heartbeat)                                  │
└──────────────────────────────────────────────────────────────┘
```

### Service Topology

| Port | Domain | systemd Unit | App | Responsibility |
|---|---|---|---|---|
| 8081 | main domain | `verorun-main` | `auth_server` | Main site, login, captcha proxy |
| 8083 | `platform.*` | `verorun-auth` | `main_site` (Platform Console) | User console, subscription |
| 8084 | `admin.*` | `verorun-admin` | `admin.app` | Admin panel, Agent matrix, automation, CMS |
| 8085 | — | `verorun-health` | `health_service.app` | Internal health check endpoint |
| 8090 | — | standalone | `captcha-service` | Puzzle captcha + behavior analysis |
| — | — | `verorun-guardian` | `veroguard.guardian` | Unified daemon (health + integrity + heartbeat) |

> Note: `auth-center/` is a **shared code library** (models / services / routes) imported by each service, not a standalone service on 8083; port 8083 actually runs the `main_site` app.

### Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask, Gunicorn |
| Database | PostgreSQL (production, with pgvector) / SQLite (dev fallback) |
| Cache | Redis |
| Reverse proxy | Nginx + Let's Encrypt |
| Workflow editor | React 18.3.1 + React Flow |
| Visualization | Chart.js, ECharts, Quill.js |
| Daemon build | Nuitka (standalone binary) |
| Image generation | FLUX.1-pro (SiliconFlow), Tongyi Wanxiang |

---

## Quick Start

### One-command Deployment (Ubuntu 22.04 / 24.04)

```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-pro/master/deploy/install.sh \
  | sudo bash -s -- install your-domain.com
```

Region selection:

```bash
sudo bash deploy/install.sh install your-domain.com --region=cn       # Mainland China
sudo bash deploy/install.sh install your-domain.com --region=global    # International (default)
```

After install, run `deploy/install.sh seed` to initialize data, `deploy/install.sh configure-domain` to configure the domain; certbot issues SSL automatically.

### Docker

```bash
docker compose up -d
```

### Local Development

```bash
pip install -r requirements.txt
cp .env.example .env
python scripts/dev_start.py
```

---

## Engine Base

### AI Engine — Multi-Role Agent Matrix (9 Roles)

Unlike a single large-model application, VeroRun does not push a complex task onto one conversation; it hands it to a group of specialized, reviewable Agent roles: the master decomposes tasks, sub-roles each do their part, the reviewer challenges the plan, and the decider signs off on the conclusion.

| Role | Slug | Type | Model | Responsibility |
|---|---|---|---|---|
| Athena | `athena` | master | — | Task decomposition, orchestration, reporting, system management |
| Content | `content` | sub | siliconflow/DeepSeek-V3 | Content creation, SEO, social media, translation |
| Builder | `builder` | sub | siliconflow/DeepSeek-V3 | Site building, themes, domains, page design |
| Finance | `finance` | sub | gemini/gemini-2.5-flash | Plans, subscriptions, billing, invoices, rewards |
| Ops | `ops` | sub | deepseek/deepseek-v4-flash | Deployment, health checks, alerts, cloud provisioning |
| Service | `service` | sub | moonshot/moonshot-v1-32k | Customer service, FAQ, tickets, notifications, IM |
| Vision | `vision` | sub | zhipu/glm-4v-plus | Image analysis, OCR, chart interpretation |
| Creative | `creative` | sub | siliconflow/FLUX.1-pro | Text-to-image, creative visual design |
| Business | `business` | sub | deepseek/deepseek-v4-flash | Business analysis, planning, supply chain |

**Extended Agents** (auto-registered via `sub_*_prompt.md`): Supply Chain, Chatbot, Automation, Health Check, User, CMS, Cleaner.

**Execution Mechanism**: sub-tasks are dispatched in parallel via ThreadPoolExecutor (≤5 workers) with a 300s per-task timeout; agents self-evaluate (rule-based pre-check + LLM structural review) with a confidence threshold of 0.7 and retry (default 2 attempts) below threshold; LLM response caching is enabled at temperature=0 with a 3600s TTL.

### Four-Stage Discussion Protocol (Agent Discussion v2.0)

The collaboration protocol is composed of three roles — Planner, Reviewer, Decider — and executes in 4 rounds:

1. **Planner** produces an initial execution plan (plan_v1).
2. **Reviewer** reviews it, outputting issues and revised_steps.
3. **Planner** revises into plan_v2 based on the review.
4. **Decider** makes the final approve / reject decision with reasoning.

Separating generation from review transplants the discipline of "plan review + sign-off" from engineering organizations into the LLM workflow, trading structure for quality and traceability.

### Dynamic Prompt System

VeroRun has upgraded from static `.md` text prompts to a **database-driven, tag-matching, chained-assembly dynamic prompt system**. At runtime, `PromptResolver` assembles the System Prompt in real time from the task context. `agent_matrix/prompts/*.md` files serve only as initialization seeds (migrated to the `agent_prompts` table by `seed_prompts.py`).

**Four-Layer Assembly**:

1. **Role base**: the role's base prompt from the default binding in `agent_prompt_bindings`.
2. **Global safety rules**: rules with `prompt_type='rule'` and `domain='general'`.
3. **Scenario templates**: scenario prompts whose `task_triggers` exactly match the `task_type`.
4. **Mode enhancements**: tool or scenario prompts matched by `mode` tag / mode binding.

**Data Model**: `agent_prompts` (version, is_active, priority, tags, task_triggers) + `agent_prompt_bindings`; the `prompts_db.html` admin page offers visual management, and multiple versions of the same slug are supported with switch and rollback.

**Toggle & Fallback**: controlled by `system_config.prompt_resolver_enabled`, which takes effect only when the key exists and holds a truthy value; a missing key or a read error returns a safe fallback. Fallback spans three layers: toggle off → read `agent_matrix.system_prompt` (file path or inline text, with path-traversal protection); any assembly exception → likewise falls back to legacy; no matching entry after four-layer lookup → falls back to the original `system_prompt` logic. This follows the "availability-first" principle — the default failure direction is degraded-but-available, not business outage.

**Integration with Cognitive Evolution**: dynamic prompts are injected with memory through the kernel `before_prompt_resolve` filter chain, and support Prompt Evolution's per-version metric aggregation and one-click application of new versions.

### Knowledge Base & Memory Engine (CogEvolution)

Since v0.56.4, `memory_engine` has been upgraded into a cognitive evolution engine forming a "memory → reflection → optimization → behavioral evolution" loop:

- **Vector retrieval (RAG)**: retrieves context from a document knowledge base; AI Q&A includes source citations.
- **Reflexion**: triggered on task failure or low confidence; extracts failure context → root-cause analysis → generates structured reflection → persists to long-term memory, auto-retrieved for later similar tasks to avoid repeating mistakes.
- **Prompt Evolution**: aggregates execution metrics per prompt version and generates optimization suggestions when statistically significant; admins apply a new version in one click. **Note: disabled by default** (`prompt_evolution_enabled: false`); must be explicitly enabled.
- **Evolution-loop visualization**: a pure-SVG interactive component rendering decision paths, reflection trigger points, and prompt-version switches in a ring topology, with replay and drill-down.
- **Layered memory**: working memory (in-process) + long-term vector memory (pgvector); supports user / global / agent scopes; privacy-first (user-level opt-in, PII auto-filtering, isolated schema); falls back to keyword retrieval when pgvector is unavailable.

### Project Workspace (Knowledge Retrieval in Practice)

The engine's "knowledge retrieval" primitive is realized as a project-level knowledge base by the `project_workspace` plugin:

- **Schema isolation**: each project gets an independent PostgreSQL schema with enforced `WHERE project_id=?` queries.
- **Document RAG**: supports PDF / DOCX / TXT / MD / PPTX / XLSX / CSV upload with an async pipeline (extract → chunk → embed → store).
- **Semantic retrieval**: pgvector with keyword fallback; AI Q&A includes source citations and feedback scoring.
- **Workspace assistant**: document summarization, comparison, source-traced Q&A, and content analysis.
- **RBAC**: Viewer (retrieve / ask) / Editor (upload / edit) / Owner (manage project and members).

### Visual Workflow Engine

Any task drivable by agent collaboration and process orchestration can be arranged on a visual DAG:

- **DAG orchestration**: 12 registered node types — `ai_agent`, `data_collect`, `ai_process`, `condition`, `approval`, `publish`, `notify`, `wait`, `sub_workflow`, `market_check`, `http_request`, `script`.
- **Implementation caveat**: `approval`, `sub_workflow`, and `script` currently only have placeholder handlers with no real logic — confirm before use.
- **Cron scheduling**: APScheduler-based, supporting Cron / Interval / Date triggers, pause / resume, priorities (critical / high / normal / low), exponential-backoff retry, and natural-language cron parsing.
- **Tiered worker pools**: `dedicated_pool` (4 threads) + `shared_pool` (8 threads); priorities ≤ HIGH go to dedicated, otherwise to shared.

### Multi-Provider LLM Gateway (UnifiedLLM)

`UnifiedLLM` is the unified entry point for all LLM interactions:

| Capability | Description |
|---|---|
| Provider access | 7 native providers: DashScope / OpenAI / DeepSeek / OpenRouter / SiliconFlow / Gemini / Grok; GLM and Moonshot are resolved dynamically via the `provider_models` table |
| Dual addressing | via `provider_model_id` (recommended) or legacy `provider + model` |
| Client cache | 5-minute TTL, thread-safe |
| Key resolution priority | `provider_api_keys` table (encrypted) → environment vars → `system_config` table |
| Streaming | `chat_stream()` with automatic token usage tracking |
| Tool calling | `chat_with_tools()` for function-calling agents |
| Budget gate | daily token cap (default 2M) + per-minute rate limit (default 30 calls / 60s), fail-open |
| 4-level quota | priority User > Model > Module > Global |

**Orchestration**: UnifiedLLM shields provider differences from upper layers — applications all talk the same API shape while the gateway handles interface translation, model routing, and automatic failover behind the scenes. Models are addressed dynamically by capability and cost, enabling transparent substitution and automatic degradation while avoiding vendor lock-in; onboarding a new provider or switching models requires no changes to business code.

---

### VeroGuard Guard Layer

Unifies health monitoring, code-integrity verification, and encrypted heartbeat into a single process across 7 core modules (health / integrity / fingerprint / runtime / communicator / executor / self_protect):

| Channel | Interval | Mechanism |
|---|---|---|
| Health watchdog | 30s | Service health checks, tiered recovery (restart → rollback), webhook alerts |
| Integrity verification | 300s | Per-file SHA256 comparison against an encrypted manifest (AES-GCM) |
| Heartbeat report | 300s | AES-256-GCM + HMAC-SHA256 signing + TLS 1.3, 5-minute anti-replay window |

- **Self-protection**: dual-process (`guardian` monitors business services, `self_protect` monitors the guardian) with pipe / pidfile heartbeat and automatic restart on parent death.
- **Remote commands** (6): `warn`, `lock_ai`, `lock_full`, `shutdown`, `self_destruct`, `update_config`.

---

## Plugin Ecosystem ("What Runs")

Full lifecycle management (6 states: `UNKNOWN → INSTALLED → ENABLED → ACTIVE → DISABLED → UNINSTALLED`) plus an `ERROR` state. Plugins cover six directions by domain:

| Domain | Plugins |
|---|---|
| Business operations | `shop`, `payment`, `logistics`, `order_notify`, `reviews`, `wishlist`, `ali_api`, `subscription` |
| Content publishing | `content_factory`, `site_builder`, `mini_app_builder`, `ads`, `coupons`, `social_push` |
| Knowledge management | `memory_engine`, `chatbot`, `project_workspace` |
| Communications | `im_gateway`, `email`, `sms`, `oauth_config` |
| Ops & security | `health_check`, `vault`, `verification`, `captcha_embedded`, `enterprise_verify` |
| Data & utilities | `currency_converter`, `site_domains`, `visitor_profile`, `analytics` |

**Plugin Manager Mechanics**: auto-scans `plugins/` and parses `plugin.json`; dependency resolution via Kahn topological sort with cycle detection; an event bus with 31 system events (thread-pool async dispatch); WordPress-style Action / Filter hooks with priority; JSON Schema Draft-07 config validation (with type-coercion fallback); per-plugin isolated logs (rotating 5MB × 3).

**Plugin Marketplace**: browse / search (remote API + local cache), one-click install (SHA256 integrity + Zip Slip protection), Alipay QR payment, subscriptions (monthly / yearly) and coupons. Licensing: online validation (HMAC-signed requests) + offline token (**HMAC-SHA256**, 72h grace + 7-day validity, bound to Site ID) + free plugins skip validation.

---

## Content Generation

Content generation is one of the general capabilities carried by the engine, covering the batch production and distribution of diverse content forms such as articles, images, and marketing assets. Leveraging the same engine, content can also be delivered directly to front-ends such as websites and mini programs:

- **Content production** (`content_factory`): batch generation and distribution of articles, images, and marketing assets.
- **AI site building** (`site_builder`): generates websites, themes, and pages, presenting content in site form.
- **Mini programs** (`mini_app_builder`): extends content capabilities to the mini-program front-end.

Content generation is independent of the knowledge retrieval, process orchestration, model access, and asset protection primitives — all of which can be combined on demand by business plugins to form complete applications.

---

## Business Model & Regional Routing

**Three-stage funnel**: open-source core for lead generation (the public `verorun-base` repository) → plugin purchases, subscriptions, and commercial licenses for recurring revenue → VeroGuard protects code assets and licensing rights on the customer side. **Data-flywheel vision**: centered on domain knowledge assets, knowledge bases self-evolve through business usage, powering domain-model fine-tuning and intelligent-device training.

**Regional routing**: `VERORUN_REGION=cn` → `api.verorun.cn`; `=global` → `api.verorun.com`. All remote services (licensing / heartbeat / daemon) resolve dynamically by region, with single-URL environment-variable override.

---

## SDKs

| Package | Platform | Description |
|---|---|---|
| `@verorun/sdk-common` | Cross-platform | Auth, Chat, RAG |
| `@verorun/sdk-wechat` | WeChat | WeChat Mini Program wrapper |
| `@verorun/sdk-douyin` | Douyin | Douyin / Toutiao Mini Program wrapper |
| `@verorun/sdk-telegram` | Telegram | Bot API + WebApp |
| `@verorun/sdk-line` | LINE | LIFF + Messaging API |

---

## Directory Structure

```text
verorun-pro/
├── admin/                  # Admin panel (8084)
├── auth-center/            # Shared auth/model/services/routes (not a standalone service)
├── main_site/              # Main site backend (8081)
├── agent_matrix/           # AI Engine: multi-agent orchestration
│   ├── roles/              # 9 role YAML definitions
│   ├── prompts/            # Dynamic prompt seeds (15 .md; runtime loads from agent_prompts table)
│   ├── prompt_resolver.py  # Dynamic prompt dispatching engine
│   ├── engine.py           # UnifiedLLM gateway + budget + quota
│   ├── orchestrator.py     # Task decomposition, parallel dispatch
│   └── agent_runner.py     # Self-evaluating executor
├── orchestrator/           # Visual workflow engine (DAG)
├── plugins/                # 30 built-in plugins (business form assembly)
├── plugin_manager/         # Plugin lifecycle / marketplace / licensing / regional routing
├── veroguard/              # VeroGuard guard layer (7 modules)
├── providers/              # Pluggable provider abstraction
├── sdks/                   # JavaScript SDKs (5 packages)
├── captcha-service/        # Standalone puzzle captcha service (8090)
├── health_service/         # Health check service (8085)
├── i18n/                   # Internationalization (en, zh-CN)
├── deploy/                 # Deployment scripts, Nginx config
├── themes/                 # Theme system
├── tests/                  # Test suite
├── GUIDE.md / CHANGELOG.md / VERSION
├── Dockerfile / docker-compose.yml
└── LICENSE
```

> Note: business directories such as `site_builder/` are concrete realizations of content-generation capability — they belong to the application layer carried by the engine, not the engine itself.

---

## Documentation

- `GUIDE.md` — installation and usage guide
- `CHANGELOG.md` — version changelog
- `agent_matrix/ARCHITECTURE.md` — Agent matrix design
- `sdks/README.md` — SDK usage
- `deploy/README.md` — deployment notes
- `plugins/memory_engine/README.md` — cognitive evolution engine

---

## Known Production Constraints

- The Admin service limits Gunicorn workers to 2 to avoid OOM on low-spec servers.
- SQLite mode disables `--preload` to avoid cross-process connection conflicts.
- systemd `TimeoutStartSec` must exceed `health_check.sh`'s `MAX_WAIT=180`.
- Plugin connection wrapper classes must implement commit / rollback / close to avoid idle-in-transaction pool poisoning.
- The deployment script must exclude `data/` to prevent overwriting the production database.

---

## License

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Copyright (c) 2026 Fan Jumin. See [LICENSE](LICENSE) for details.