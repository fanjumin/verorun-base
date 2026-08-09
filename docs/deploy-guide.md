# VeroRun — Deployment & Uninstall Guide

## Prerequisites

- **OS**: Ubuntu 20.04 / 22.04 / 24.04 (amd64)
- **Python**: 3.8 or later
- **Ports**: 80 (HTTP) open in firewall / security group
- **Access**: root or sudo-capable user
- **Domain**: A domain name pointed to your server IP (optional at install time)

---

## No-Domain / LAN Deployment

Deploy VeroRun **without a public domain**, accessible via `localhost` or a LAN IP
(e.g. `http://192.168.x.x/`). No DNS, no SSL, no subdomains required.

**One-command:**
```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install-local.sh | sudo bash
```

```bash
sudo bash deploy/install-local.sh
```

Access paths after install:

| Path | Backend | Purpose |
|------|---------|---------|
| `http://localhost/` | 8081 | Main site |
| `http://localhost/admin/` | 8084 | Admin panel |
| `http://localhost/auth/` | 8083 | User console / subscriptions |
| `http://localhost/subscribe` | 8083 | Subscription |

The same paths work via `http://<LAN-IP>/` from other machines on the network.

### Other No-Domain Scripts

Besides `install-local.sh`, two more no-domain deploy scripts are shipped:

**One-command:**
```bash
curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install-code.sh | sudo bash
```

**`install-code.sh` (team intranet deployment)** — clones the private `verorun-code` over SSH with full sparse-checkout **including all plugins**:
```bash
sudo bash deploy/install-code.sh install
```

**One-command:**
```bash
curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install-dev.sh | sudo bash
```

**`install-dev.sh` (developer workstation)** — clones the private `verorun-code` over SSH (adds the deploy key on first run) with sparse-checkout that **excludes `plugins/`** (clone ~50% smaller) while keeping `plugin_manager/` so plugins can still be installed later from the admin panel:
```bash
sudo bash deploy/install-dev.sh install
```

### No-Domain Script Comparison

| Script | Code Source | Plugins | Use Case |
|--------|-------------|---------|----------|
| `install-local.sh` | git clone `verorun-base` (HTTPS) | N/A (base repo) | Full intranet / LAN deployment (public base) |
| `install-code.sh` | git clone `verorun-code` (SSH) | included | Team intranet deployment (full source + plugins) |
| `install-dev.sh` | git clone `verorun-code` (SSH) | excluded (clone ~50% smaller) | Developer workstation |

### Differences vs `install.sh`

| Dimension | install.sh (domain mode) | install-local.sh |
|-----------|--------------------------|----------------------|
| Domain | Required, else services not started | Not required, `DEPLOY_DOMAIN` empty |
| Protocol | `DEPLOY_PROTOCOL=https` | `DEPLOY_PROTOCOL=http` |
| Nginx | Subdomain `server_name` routing | Path routing only, `listen 80 default_server` |
| SSL | Manual certbot | Skipped (HTTP) |
| Backend binding | `127.0.0.1` | `127.0.0.1` (unchanged) |

### Limitations (architecture-bound)

Online payment, OAuth third-party login, and SMS notifications require public
callback URLs and are **unavailable** in no-domain mode. Multi-tenant subdomains
and SSL are also unavailable. This mode targets **development / testing / intranet**
deployment, not public production.

### Security Notes

- Transmission is plain HTTP — restrict port 80 access to trusted IPs via `ufw`/security groups
- Application-layer protections (JWT signing, password hashing, CSRF `samesite=Lax`,
  `httponly` cookies) remain fully active

### Switching to Domain Mode Later

```bash
sudo bash deploy/install.sh configure-domain your-domain.com
```

The code changes are conditional branches — once `DEPLOY_DOMAIN` is set and
`DEPLOY_PROTOCOL` defaults to `https`, the system automatically returns to
domain-mode behavior. No code rollback needed.

---

## China Network Auto-Adaptation (CN Network)

All four deploy scripts (`install.sh` / `install-local.sh` / `install-dev.sh` /
`install-code.sh`) source a shared common function library
`deploy/lib/common.sh` at startup, which provides the China-network
auto-adaptation module, logging helpers (`step` / `done_step` / `fail_step`),
git auth, systemd service writing, sudoers, health check, seed and rollback.
Each script keeps only its own domain-mode logic (`generate_env`,
`write_nginx_config`, `print_summary`, `do_install`, `do_update`).
Overseas environments (default mirrors reachable) are fully unaffected — no
manual configuration required:

| Item | Behavior |
|------|----------|
| **apt mirror** | If the default source is unreachable within 3s, switches to Aliyun (backup at `sources.list.bak.$(date +%s)`, idempotent via marker file) |
| **pip mirror** | Multi-source speed test (Aliyun → Tsinghua → official), picks the fastest, detected once |
| **git clone** | `timeout 60` + `--depth 1` shallow clone; on failure prints proxy / manual-clone workarounds |

---

## One-Command Install

| 脚本 | 场景 | 一键命令 |
|------|------|---------|
| `install.sh` | 公网生产部署（需域名） | `curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install.sh \| sudo bash -s -- install your-domain.com` |
| `install-local.sh` | 局域网 / 单机无域名 | `curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install-local.sh \| sudo bash` |
| `install-dev.sh` | 开发工作站（私有库 SSH） | `curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install-dev.sh \| sudo bash` |
| `install-code.sh` | 团队内网服务器（私有库 SSH + 全量 plugins） | `curl -sSL https://raw.githubusercontent.com/fanjumin/verorun-base/master/deploy/install-code.sh \| sudo bash` |

公开库（`install.sh` / `install-local.sh`）无需认证，单行命令直接可用。私有库（`install-dev.sh` / `install-code.sh`）需先配置 SSH deploy key：服务器生成密钥后，将公钥加入 GitHub `verorun-code` 仓库的 Deploy Keys，再重跑同一条命令即可。

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

## 手动部署（Manual Deployment）

一键命令（`curl | sudo bash`）等价于手动执行以下步骤，适合需要先审阅代码或网络受限的场景：

```bash
# 1. 克隆仓库
git clone https://github.com/fanjumin/verorun-base.git
cd verorun-base

# 2. 有域名部署
sudo bash deploy/install.sh install your-domain.com

# 3. 无域名部署（局域网/单机，后续可用 configure-domain 补配）
sudo bash deploy/install-local.sh
```

私有库（`verorun-code`）将第 1 步替换为 SSH 克隆并改用 `install-dev.sh` / `install-code.sh`：

```bash
git clone git@github.com:fanjumin/verorun-code.git
cd verorun-code
sudo bash deploy/install.sh install your-domain.com
```

`install` 模式会自动执行数据库迁移 + 播种，装完即用，无需再手动执行 `seed`。

## Post-Install: Configure Domain

If you skipped the domain prompt during install, set it now:

```bash
sudo bash /home/verorun/verorun-workspace/deploy/deploy.sh configure-domain your-domain.com
```

This updates `.env`, rewrites systemd services and Nginx config, then starts everything.

---

## Seed Initial Data

`install` 模式已自动执行数据库迁移与播种（管理员账号、订阅计划、产品在安装时即已创建），装完即用。
仅在 `update` 后或需要重置初始数据时手动执行：

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
| Health Service | 8085 | `verorun-health` | `health_service` |
| VeroGuard Guardian | — | `verorun-guardian` | `veroguard` |

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

The `mini_app_builder` plugin (mini-program generation + developer
accounts) uses an independent database `mini_app` (same PG instance,
database-level physical isolation from the main `verorun` database).

### New environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MINI_APP_DB_URL` | Full URL to the independent DB (overrides the `MINI_APP_PG_*` group) | (empty) |
| `MINI_APP_PG_HOST` | Independent DB host | falls back to `PG_HOST` |
| `MINI_APP_PG_PORT` | Independent DB port | falls back to `PG_PORT` |
| `MINI_APP_PG_DB` | Independent DB name | `mini_app` |
| `MINI_APP_PG_USER` | Independent DB user | falls back to `PG_USER` |
| `MINI_APP_PG_PASSWORD` | Independent DB password | falls back to `PG_PASSWORD` |
| `INTERNAL_SERVICE_TOKEN` | Token for `/api/internal/*` (main_site → plugin) | auto-generated by install.sh |
| `MAIN_SITE_INTERNAL_URL` | Base URL of main_site internal API | `http://127.0.0.1:8081` |

`install.sh` automatically creates `mini_app` and writes
`MINI_APP_PG_DB` / `INTERNAL_SERVICE_TOKEN` into `.env`.

### Fresh install

1. Pull the code and update dependencies.
2. `install.sh` creates the independent DB automatically (or manually):
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE mini_app OWNER verorun"
   ```
3. The plugin creates its schemas/tables on first start (idempotent).
4. Restart all services:
   ```bash
   systemctl restart verorun-main verorun-auth verorun-admin
   ```

### Uninstall note

When removing VeroRun, also drop the independent DB:

```bash
sudo -u postgres psql -c "DROP DATABASE IF EXISTS mini_app"
```