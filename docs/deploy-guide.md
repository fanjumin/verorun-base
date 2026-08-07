# VeroRun — Deployment & Uninstall Guide

## Prerequisites

- **OS**: Ubuntu 20.04 / 22.04 / 24.04 (amd64)
- **Python**: 3.8 or later
- **Ports**: 80 (HTTP) open in firewall / security group
- **Access**: root or sudo-capable user
- **Domain**: A domain name pointed to your server IP (optional at install time)

---

## One-Command Install

Run this on a fresh Ubuntu server:

```bash
curl -sSL https://raw.githubusercontent.com/fanjumin/VeroRunSystem/master/deploy/deploy.sh | sudo bash
```

During install you will be prompted for your domain name. You can skip it and configure later.

### What the install script does

| Step | Action |
|------|--------|
| System deps | Installs python3, pip, venv, nginx, git, build-essential, libpq-dev |
| PostgreSQL | Installs and starts PostgreSQL, creates `verorun` role and database |
| User | Creates `verorun` system user |
| Code | Clones the repository to `/home/verorun/verorun-workspace` |
| Python venv | Creates virtual environment, installs all Python dependencies |
| .env | Generates production config with random secrets |
| systemd | Creates and enables 3 services: `verorun-main`, `verorun-auth`, `verorun-admin` |
| Nginx | Configures reverse proxy, removes default site |

---

## Post-Install: Configure Domain

If you skipped the domain prompt during install, set it now:

```bash
sudo bash /home/verorun/verorun-workspace/deploy/deploy.sh configure-domain your-domain.com
```

This updates `.env`, rewrites systemd services and Nginx config, then starts everything.

---

## Seed Initial Data

Populate the database with default admin account, plans, and products:

```bash
sudo bash /home/verorun/verorun-workspace/deploy/deploy.sh seed
```

---

## Update (Deploy New Code)

Pull latest code, install new dependencies, restart services:

```bash
sudo bash /home/verorun/verorun-workspace/deploy/deploy.sh update
```

This mode does **not** overwrite systemd or Nginx configuration — only code and Python dependencies are updated.

---

## Health Check

```bash
sudo bash /home/verorun/verorun-workspace/deploy/deploy.sh health
```

Checks all three service ports (8081, 8083, 8084) and prints recent migration logs.

---

## Rollback

Revert to the previous git commit:

```bash
sudo bash /home/verorun/verorun-workspace/deploy/deploy.sh rollback
```

---

## Restart Services

```bash
sudo bash /home/verorun/verorun-workspace/deploy/deploy.sh restart
```

---

## Service Architecture

| Service | Port | systemd Unit | Module |
|---------|------|-------------|--------|
| Main Site | 8081 | `verorun-main` | `main_site` |
| Auth / Platform | 8083 | `verorun-auth` | `auth_server` |
| Admin | 8084 | `verorun-admin` | `admin` |

### Nginx Routing

| URL Path | Backend Port |
|----------|-------------|
| `your-domain.com/` | 8081 (Main) |
| `your-domain.com/admin/` | 8084 (Admin) |
| `your-domain.com/auth/` | 8083 (Auth) |
| `your-domain.com/subscribe` | 8083 (Auth) |
| `platform.your-domain.com` | 8083 (Auth) |
| `agent.your-domain.com` | 8084 (Admin) |

---

## Service Management

```bash
# View service status
systemctl status verorun-main
systemctl status verorun-auth
systemctl status verorun-admin

# Restart a single service
systemctl restart verorun-admin

# View live logs
journalctl -u verorun-admin -f

# View recent logs
journalctl -u verorun-main -n 50
```

---

## Log Locations

| Service | Log Path |
|---------|----------|
| Main Site | `/var/log/verorun/verorun-main.log` |
| Auth | `/var/log/verorun/verorun-auth.log` |
| Admin | `/var/log/verorun/verorun-admin.log` |

---

## File Locations

| Item | Path |
|------|------|
| Application root | `/home/verorun/verorun-workspace` |
| Python venv | `/home/verorun/verorun-workspace/venv` |
| Environment config | `/home/verorun/verorun-workspace/.env` |
| SQLite database | `/home/verorun/verorun-workspace/data/verorun.db` |
| Nginx config | `/etc/nginx/sites-available/verorun.conf` |
| systemd units | `/etc/systemd/system/verorun-*.service` |

---

## Complete Uninstall

To remove VeroRun entirely from the server:

```bash
# 1. Stop and disable all services
systemctl stop verorun-main verorun-auth verorun-admin
systemctl disable verorun-main verorun-auth verorun-admin
rm -f /etc/systemd/system/verorun-*.service
systemctl daemon-reload

# 2. Remove Nginx config
rm -f /etc/nginx/sites-enabled/verorun.conf
rm -f /etc/nginx/sites-available/verorun.conf
systemctl restart nginx

# 3. Remove application user and files
userdel -r verorun

# 4. Remove logs
rm -rf /var/log/verorun

# 5. Remove PostgreSQL database and role (optional — only if VeroRun is the sole user)
sudo -u postgres psql -c "DROP DATABASE IF EXISTS verorun"
sudo -u postgres psql -c "DROP ROLE IF EXISTS verorun"
```

> **Warning**: Steps 5 removes the PostgreSQL database permanently. Skip this if you share the PostgreSQL instance with other applications.

---

## Environment Variables

The `.env` file is auto-generated during install. Manual edits may be needed for production:

| Variable | Purpose | Default |
|----------|---------|---------|
| `DEPLOY_DOMAIN` | Your domain name | (set during install) |
| `DEPLOY_MARKET` | Market region (`cn` / `intl`) | `cn` |
| `PG_HOST` | PostgreSQL host | `localhost` |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_DB` | PostgreSQL database name | `verorun` |
| `PG_USER` | PostgreSQL user | `verorun` |
| `PG_PASSWORD` | PostgreSQL password | **change this** |
| `JWT_SECRET` | JWT signing key | auto-generated |
| `FLASK_SECRET_KEY` | Flask session secret | auto-generated |
| `DASHSCOPE_TEXT_KEY` | DashScope API key | (set your own) |
| `OPENAI_API_KEY` | OpenAI API key | (set your own) |
| `DEEPSEEK_API_KEY` | DeepSeek API key | (set your own) |

After editing `.env`, restart all services:

```bash
systemctl restart verorun-main verorun-auth verorun-admin
```

---

## Troubleshooting

### Service fails to start

```bash
journalctl -u verorun-admin -n 30 --no-pager
```

### Port already in use

```bash
ss -tlnp | grep -E '8081|8083|8084'
```

### Nginx config test fails

```bash
nginx -t
```

### Database connection issues

```bash
sudo -u verorun /home/verorun/verorun-workspace/venv/bin/python -c "
import psycopg2
conn = psycopg2.connect(host='localhost', dbname='verorun', user='verorun', password='your-password')
print('OK')
"
```

---

## Independent Database for mini_app_builder (v2.1.0)

Since **v2.1.0** the `mini_app_builder` plugin (mini-program generation + developer
accounts) no longer shares the main `verorun` database. It uses an independent
database `verorun_miniapp` (same PG instance, database-level physical isolation).

### New environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MINI_APP_DB_URL` | Full URL to the independent DB (overrides the `MINI_APP_PG_*` group) | (empty) |
| `MINI_APP_PG_HOST` | Independent DB host | falls back to `PG_HOST` |
| `MINI_APP_PG_PORT` | Independent DB port | falls back to `PG_PORT` |
| `MINI_APP_PG_DB` | Independent DB name | `verorun_miniapp` |
| `MINI_APP_PG_USER` | Independent DB user | falls back to `PG_USER` |
| `MINI_APP_PG_PASSWORD` | Independent DB password | falls back to `PG_PASSWORD` |
| `INTERNAL_SERVICE_TOKEN` | Token for `/api/internal/*` (main_site → plugin) | auto-generated by install.sh |
| `MAIN_SITE_INTERNAL_URL` | Base URL of main_site internal API | `http://127.0.0.1:8081` |

`install.sh` automatically creates `verorun_miniapp` and writes
`MINI_APP_PG_DB` / `INTERNAL_SERVICE_TOKEN` into `.env`.

### Upgrading an existing deployment

1. Pull the new code and update dependencies.
2. Create the independent DB (install.sh does this automatically on reinstall):
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE verorun_miniapp OWNER verorun"
   ```
3. The plugin creates its schemas/tables on first start (idempotent).
4. Migrate existing data **only if you already used mini-apps before v2.1.0** — see
   `plugins/mini_app_builder/migrations/v2.1.0_migrate_to_independent.sql` for the
   pg_dump procedure, row-count verification and rollback steps.
5. Restart all services:
   ```bash
   systemctl restart verorun-main verorun-auth verorun-admin
   ```

### Uninstall note

When removing VeroRun, also drop the independent DB:

```bash
sudo -u postgres psql -c "DROP DATABASE IF EXISTS verorun_miniapp"
```