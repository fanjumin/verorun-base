# VeroRun Deployment Guide

> Automated one-command deployment script for VeroRun multi-service system on Ubuntu 22.04+.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Install (One Command)](#quick-install-one-command)
- [What the Script Does](#what-the-script-does)
- [Available Commands](#available-commands)
- [Architecture Overview](#architecture-overview)
- [Post-Install Configuration](#post-install-configuration)
- [Troubleshooting](#troubleshooting)
- [Manual Step-by-Step Installation](#manual-step-by-step-installation)

---

## Prerequisites

- **OS:** Ubuntu 22.04 or 24.04 LTS (clean installation recommended)
- **User:** `root` access via `sudo` (the script must run as root)
- **Network:** Outbound internet access to GitHub (for cloning the repository)
- **Domain (recommended):** A domain name pointed to your server's public IP
- **Minimum specs:**
  - 2 GB RAM (4 GB recommended)
  - 20 GB disk
  - 1 vCPU (2 vCPU recommended)

---

## Quick Install (One Command)

### With a domain

```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/install.sh | sudo bash -s -- install your-domain.com
```

Replace `your-domain.com` with your actual domain name.

### Without a domain (configure later)

```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/install.sh | sudo bash -s -- install
```

You will be prompted to enter a domain or skip. If skipped, you can configure it later:

```bash
sudo bash deploy/install.sh configure-domain your-domain.com
```

### Via git clone

```bash
git clone https://github.com/fanjumin/VeroRunSystem.git
cd VeroRunSystem
sudo bash deploy/install.sh install your-domain.com
```

---

## What the Script Does

On a fresh install (`install` mode), the script:

1. **System dependencies** — Installs Python 3, Nginx, Git, build tools, PostgreSQL
2. **PostgreSQL** — Installs and starts PostgreSQL, creates the `verorun` database role and database
3. **User & directories** — Creates the `verorun` system user, workspace directory, and log directory
4. **Pull code** — Clones the latest code from GitHub into `/home/verorun/verorun-workspace/`
5. **Python virtual environment** — Creates a venv and installs all Python dependencies
6. **Environment file** — Generates `.env` with auto-generated secrets (JWT, encryption keys, etc.)
7. **systemd services** — Writes 3 service files:
   - `verorun-main` (port 8081) — Main site backend
   - `verorun-auth` (port 8083) — Auth & subscription
   - `verorun-admin` (port 8084) — Admin panel
8. **Nginx** — Configures reverse proxy for main domain + subdomains
9. **Start services** — Starts all systemd services and Nginx

If no domain is provided, steps 7-9 are skipped and can be run later with `configure-domain`.

---

## Available Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `install` | `install.sh install [domain]` | Fresh installation (default if no `.env` exists) |
| `update` | `install.sh update` | Pull latest code, update deps, restart services |
| `restart` | `install.sh restart` | Restart all systemd services and Nginx |
| `health` | `install.sh health` | Check all services and show HTTP status |
| `rollback` | `install.sh rollback` | Revert to previous git commit and restart |
| `seed` | `install.sh seed` | Inject initial data (admin account, plans, products) |
| `configure-domain` | `install.sh configure-domain <domain>` | Set/replace domain, re-configure Nginx and services |

### Example: Update to latest code

```bash
sudo bash deploy/install.sh update
```

### Example: Health check

```bash
sudo bash deploy/install.sh health
```

### Example: Seed initial data (after install)

```bash
sudo bash deploy/install.sh seed
```

---

## Clean Uninstall

Remove everything (services, database, code, logs) for a complete fresh start:

```bash
# 1. Stop and disable all services
sudo systemctl stop verorun-main verorun-auth verorun-admin verorun-health 2>/dev/null
sudo systemctl disable verorun-main verorun-auth verorun-admin verorun-health 2>/dev/null

# 2. Remove systemd service files
sudo rm -f /etc/systemd/system/verorun-*.service
sudo systemctl daemon-reload

# 3. Remove Nginx config
sudo rm -f /etc/nginx/sites-enabled/verorun.conf /etc/nginx/sites-available/verorun.conf
sudo systemctl restart nginx

# 4. Drop database and role
sudo -u postgres dropdb verorun
sudo -u postgres dropuser verorun

# 5. Remove code, venv, and logs
sudo rm -rf ~/verorun-workspace /var/log/verorun
```

After this, you can run the install command again for a clean install.

---

## Architecture Overview

### Service Layout

```
Internet
    │
    ▼
  Nginx (port 80/443)
    │
    ├── /admin/* ──────────────► verorun-admin (:8084)
    ├── /auth/*, /subscribe ──► verorun-auth (:8083)
    └── /* ──────────────────► verorun-main (:8081)
```

### Subdomain Routing

| Subdomain | Port | Service | Purpose |
|-----------|------|---------|---------|
| `yourdomain.com` | 8081 | `main_site:app` | Main site, user-facing pages |
| `platform.yourdomain.com` | 8083 | `auth_center:app` | Auth, subscriptions, user console |
| `agent.yourdomain.com` | 8084 | `admin:app` | Admin panel, plugin management |

### File Locations

| Path | Purpose |
|------|---------|
| `/home/verorun/verorun-workspace/` | Application code |
| `/home/verorun/verorun-workspace/venv/` | Python virtual environment |
| `/home/verorun/verorun-workspace/.env` | Environment configuration |
| `/home/verorun/verorun-workspace/data/` | SQLite database (if used) |
| `/var/log/verorun/` | Service logs |
| `/etc/systemd/system/verorun-*.service` | systemd service files |
| `/etc/nginx/sites-available/verorun.conf` | Nginx configuration |

---

## Post-Install Configuration

### 1. Seed Initial Data

After installation, inject the admin user, subscription plans, and products:

```bash
sudo bash deploy/install.sh seed
```

Default admin credentials (generated by seed script):
- Username: `guxiao`
- Password: `XSNNTg.9vmFy`

**Important:** Change the admin password after first login.

### 2. Configure Domain (if skipped during install)

```bash
sudo bash deploy/install.sh configure-domain your-domain.com
```

This writes Nginx config, generates systemd service files, and restarts everything.

### 3. Set Up SSL with Let's Encrypt (Recommended)

After the domain is configured and DNS is pointing to your server:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com -d platform.your-domain.com -d agent.your-domain.com
```

### 4. Configure API Keys

Edit `/home/verorun/verorun-workspace/.env` and replace placeholder API keys:

- `DASHSCOPE_TEXT_KEY` — DashScope (Alibaba AI) API key
- `OPENAI_API_KEY` — OpenAI API key
- `DEEPSEEK_API_KEY` — DeepSeek API key

After updating, restart services:

```bash
sudo bash deploy/install.sh restart
```

---

## Troubleshooting

### All services fail to start (exit code 1)

Check the common error:

```bash
journalctl -u verorun-main -n 50 --no-pager
```

**Most common cause:** The `platform/` directory name conflicts with Python's standard library `platform` module. This has been fixed by renaming to `main_site/`. If you are running an old version, update the code:

```bash
sudo bash deploy/install.sh update
```

### Service keeps restarting in a loop

```bash
journalctl -u verorun-auth -n 50 --no-pager | grep -A 20 "Traceback"
```

Common causes:
- Missing Python dependencies → run `install.sh update`
- Database connection failure → check PostgreSQL is running: `systemctl status postgresql`
- `.env` missing required keys → run `install.sh update` to fill missing keys

### Nginx fails to start

```bash
nginx -t
journalctl -u nginx -n 30 --no-pager
```

Ensure the domain is correctly configured in `.env`:
- `DEPLOY_DOMAIN=your-domain.com`

Then re-run configure-domain:

```bash
sudo bash deploy/install.sh configure-domain your-domain.com
```

### 502 Bad Gateway

This means Nginx is running but the backend service is not responding.

1. Check if the backend service is running:
   ```bash
   systemctl status verorun-main
   ```

2. Check the service logs:
   ```bash
   journalctl -u verorun-main -n 50 --no-pager
   ```

3. The most likely cause is the `platform/` stdlib naming conflict (see above). Run `install.sh update` to get the fix.

### Rollback to previous version

```bash
sudo bash deploy/install.sh rollback
```

This reverts the code to the previous git commit and restarts all services.

---

## Manual Step-by-Step Installation

If the automated script fails, you can follow these manual steps.

### 1. System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip python3-dev \
    nginx git curl wget build-essential libpq-dev libssl-dev postgresql postgresql-client
```

### 2. Create User

```bash
sudo useradd -m -s /bin/bash verorun
sudo mkdir -p /home/verorun/verorun-workspace /var/log/verorun /home/verorun/verorun-workspace/data
sudo chown -R verorun:verorun /home/verorun/verorun-workspace /var/log/verorun
```

### 3. Clone Code

```bash
sudo git clone -b master https://github.com/fanjumin/VeroRunSystem.git /home/verorun/verorun-workspace
sudo chown -R verorun:verorun /home/verorun/verorun-workspace
```

### 4. Python Virtual Environment

```bash
sudo -u verorun python3 -m venv /home/verorun/verorun-workspace/venv
sudo -u verorun /home/verorun/verorun-workspace/venv/bin/pip install --upgrade pip
sudo -u verorun /home/verorun/verorun-workspace/venv/bin/pip install -r /home/verorun/verorun-workspace/requirements.txt
```

### 5. PostgreSQL Setup

```bash
sudo systemctl enable --now postgresql
sudo -u postgres psql -c "CREATE ROLE verorun WITH LOGIN PASSWORD 'change-me-in-production';"
sudo -u postgres psql -c "CREATE DATABASE verorun OWNER verorun;"
```

### 6. Generate .env

```bash
sudo bash -c 'cat > /home/verorun/verorun-workspace/.env << EOF
DEPLOY_MARKET=cn
DEPLOY_DOMAIN=your-domain.com
DB_PATH=/home/verorun/verorun-workspace/data/verorun.db
PG_HOST=localhost
PG_PORT=5432
PG_DB=verorun
PG_USER=verorun
PG_PASSWORD=change-me-in-production
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
APP_MODE=main
PLUGIN_LICENSE_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
CAPTCHA_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DEV_ACCOUNTS_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
LICENSE_SERVER_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DASHSCOPE_TEXT_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here
EOF'
sudo chmod 600 /home/verorun/verorun-workspace/.env
sudo chown verorun:verorun /home/verorun/verorun-workspace/.env
```

### 7. Create systemd Services

Run the script's service generator directly:

```bash
cd /home/verorun/verorun-workspace
# Manually create /etc/systemd/system/verorun-main.service
# Manually create /etc/systemd/system/verorun-auth.service
# Manually create /etc/systemd/system/verorun-admin.service
sudo systemctl daemon-reload
sudo systemctl enable verorun-main verorun-auth verorun-admin
sudo systemctl start verorun-main verorun-auth verorun-admin
```

### 8. Configure Nginx

Create `/etc/nginx/sites-available/verorun.conf` with the reverse proxy configuration (see the `write_nginx_config` function in `install.sh` for the template), then:

```bash
sudo ln -sf /etc/nginx/sites-available/verorun.conf /etc/nginx/sites-enabled/verorun.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

---

## License

Copyright (c) 2026 Fan Jumin. All rights reserved.
