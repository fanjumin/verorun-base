# VeroRun — Installation & User Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Selecting a Distribution](#selecting-a-distribution)
3. [One-Click Deployment](#one-click-deployment)
4. [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
6. [Service Management](#service-management)
7. [SSL Certificate](#ssl-certificate)
8. [Upgrading](#upgrading)
9. [Troubleshooting](#troubleshooting)

---

## System Requirements

| Requirement | Minimum |
|-------------|---------|
| OS | Ubuntu 22.04 / 24.04 (x86_64) |
| CPU | 1 vCPU (2 recommended) |
| RAM | 2 GB (4 GB recommended) |
| Disk | 20 GB free |
| Python | 3.10+ |
| Ports | 80, 443 (open in firewall/security group) |

---

## Selecting a Distribution

| Distribution | Repository | When to use |
|--------------|-----------|-------------|
| `verorun-base` | `https://github.com/fanjumin/verorun-base` (public) | Standard enterprise package, open download. |
| `verorun-code` | `https://github.com/fanjumin/verorun-code` (private) | Official site / enterprise customization; requires SSH access. |

`verorun-base` is generated automatically from `verorun-code` on every version tag by the `sync-to-base` CI workflow.

---

## One-Click Deployment

A single unified `deploy/install.sh` handles all deployment types. Choose interactively or
via the `INSTALL_TYPE` environment variable.

**Interactive (recommended):**

```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo bash -s -- install
```

**CI / automation — specify type:**

```bash
# Website (production, domain + HTTPS)
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo env INSTALL_TYPE=website bash -s -- install your-domain.com

# Professional (no domain, LAN access)
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo env INSTALL_TYPE=professional bash

# Development (verorun-code SSH, full plugins)
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo env INSTALL_TYPE=development bash

# Educational (edu license required)
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh | sudo env INSTALL_TYPE=educational bash
```

**Supported types:** `website` | `professional` | `development` | `educational`

For China deployments add `--region=cn`.

> `install-code.sh` is preserved as an independent shortcut for Development deployments.

### What the script does

1. Installs system dependencies (Python 3, Nginx, Git, build tools, PostgreSQL)
2. Creates the `verorun` system user and application directory at `/home/verorun/verorun`
3. Clones the repository (HTTPS for `verorun-base`, SSH deploy key for `verorun-code`) and installs Python dependencies
4. Generates a `.env` configuration file with auto-generated secrets (`JWT_SECRET`, `PLUGIN_LICENSE_SECRET`, `CAPTCHA_SECRET_KEY`, `PROBE_SECRET`, ...)
5. Configures Nginx with proper reverse proxy rules for all subdomains
6. Writes and starts 5 systemd services (main / auth / admin / health / guardian)
7. Optionally seeds initial data (`install.sh seed`)

---

## Manual Installation

### 1. Install System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev \
    nginx git curl wget build-essential libpq-dev libssl-dev postgresql postgresql-client
```

### 2. Clone & Setup

**`verorun-base` (public):**

```bash
sudo git clone -b master https://github.com/fanjumin/verorun-base.git /home/verorun/verorun
```

**`verorun-code` (private):**

```bash
sudo git clone -b master git@github.com:fanjumin/verorun-code.git /home/verorun/verorun
```

Then:

```bash
sudo chown -R verorun:verorun /home/verorun/verorun
cd /home/verorun/verorun
sudo -u verorun python3 -m venv venv
sudo -u verorun venv/bin/pip install --upgrade pip
sudo -u verorun venv/bin/pip install -r requirements.txt
```

### 3. Configure Environment

`install.sh` generates `.env` automatically. For manual setup, see the `.env` template and variable list in [deploy/README.md](deploy/README.md#manual-step-by-step-installation).

### 4. Configure Nginx

Run `sudo bash deploy/install.sh configure-domain your-domain.com` to write the Nginx configuration, or use the template in `deploy/nginx/`.

### 5. Start Services

```bash
sudo bash deploy/install.sh restart
```

---

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DEPLOY_MARKET` | Yes | Market code (`cn` for China) |
| `DEPLOY_DOMAIN` | Yes | Primary domain name |
| `APP_REGION` | Yes | API region routing (`cn` / `global`) |
| `PG_HOST` / `PG_PORT` | Yes | PostgreSQL host / port |
| `PG_DB` / `PG_USER` / `PG_PASSWORD` | Yes | PostgreSQL database / user / password |
| `JWT_SECRET` | Yes | JWT signing secret (64-char random hex) |
| `FLASK_SECRET_KEY` | Yes | Flask session secret (64-char random hex) |
| `PLUGIN_LICENSE_SECRET` | Yes | Plugin license HMAC secret |
| `CAPTCHA_SECRET_KEY` | Yes | Captcha HMAC token secret |
| `PROBE_SECRET` | Yes | VeroGuard probe secret |
| `DASHSCOPE_TEXT_KEY` | No | DashScope API key |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key |

All secrets are auto-generated by `install.sh` on first install.

---

## Service Management

All services are managed via systemd:

```bash
sudo systemctl status verorun-main   # View status of a service
sudo systemctl restart verorun-main  # Restart a single service
sudo bash deploy/install.sh restart  # Restart all services + Nginx
sudo bash deploy/install.sh health   # Check all services and show HTTP status
```

### Running Services

| systemd Name | Port | Description |
|--------------|------|-------------|
| `verorun-main` | 8081 | Main site backend / auth center (`auth_server`) |
| `verorun-auth` | 8083 | Platform user console & subscription (`main_site`) |
| `verorun-admin` | 8084 | Admin panel (`admin`) |
| `verorun-health` | 8085 | Health service (`health_service`) |
| `verorun-guardian` | — | VeroGuard unified guardian daemon |

---

## SSL Certificate

### Initial Setup

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com \
    -d www.your-domain.com \
    -d platform.your-domain.com \
    -d agent.your-domain.com
```

### Auto-Renewal

Certbot sets up a systemd timer automatically:

```bash
sudo systemctl status certbot.timer
```

---

## Upgrading

Use the install script (recommended):

```bash
sudo bash deploy/install.sh update
```

Or upgrade from the admin panel's **One-Click Update** (version check + git pull + pip install + service restart, with live progress).

---

## Troubleshooting

### Service not starting

```bash
sudo journalctl -u verorun-main -n 50 --no-pager
```

Common causes:
- `.env` file missing or misconfigured → run `install.sh update` to fill missing keys
- Port already in use: `sudo lsof -i :8081`
- Python dependency missing → `install.sh update` re-installs dependencies

### Nginx configuration error

```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### SSL certificate failed

- Ensure DNS A records point to your server IP
- Ensure ports 80 and 443 are open in your cloud firewall
- Try manually: `sudo certbot --nginx`

### Database issues

PostgreSQL is used in production (`verorun` database). Check the service is running:

```bash
systemctl status postgresql
```

---

For additional help, visit [docs.verorun.com](https://docs.verorun.com).
