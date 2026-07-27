# VeroRun — Installation & User Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [One-Click Deployment](#one-click-deployment)
3. [Manual Installation](#manual-installation)
4. [Configuration](#configuration)
5. [Service Management](#service-management)
6. [SSL Certificate](#ssl-certificate)
7. [Upgrading](#upgrading)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

| Requirement | Minimum |
|-------------|---------|
| OS | Ubuntu 22.04 / 24.04 (x86_64) |
| CPU | 2 cores |
| RAM | 2 GB |
| Disk | 10 GB free |
| Python | 3.10+ |
| Ports | 80, 443 (open in firewall/security group) |

---

## One-Click Deployment

The bootstrap script installs everything from scratch on a fresh Ubuntu VPS.

```bash
# Clone the repository
git clone https://github.com/fanjumin/VeroRunSystem.git /tmp/verorun
cd /tmp/verorun

# Run the deployment script
sudo bash deploy/bootstrap.sh your-domain.com
```

### What the script does

1. Installs system dependencies (Python, Nginx, Redis, Certbot, Node.js, PM2)
2. Creates a `www-data` system user and application directory at `/var/www/verorun`
3. Clones the repository and installs Python dependencies
4. Generates a `.env` configuration file with random JWT/Flask secret keys
5. Configures Nginx with proper reverse proxy rules for all subdomains
6. Requests SSL certificates via Let's Encrypt (requires DNS to be configured)
7. Starts all services via PM2 with systemd auto-restart

### Custom Installation Path

```bash
sudo bash deploy/bootstrap.sh your-domain.com /opt/my-app
```

---

## Manual Installation

### 1. Install System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev \
    nginx redis-server certbot python3-certbot-nginx git curl
```

### 2. Install Node.js & PM2

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

### 3. Clone & Setup

```bash
git clone https://github.com/fanjumin/VeroRunSystem.git /var/www/verorun
cd /var/www/verorun
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings:
#   JWT_SECRET       — generate a random 64-char hex string
#   FLASK_SECRET_KEY — generate a random 64-char hex string
#   DEPLOY_DOMAIN    — your domain name
#   API keys         — fill in your AI provider keys
```

### 5. Configure Nginx

Copy the configuration from `deploy/nginx/easykai.conf` to `/etc/nginx/sites-available/`,
replace `__DOMAIN__` and `__APP_ROOT__` placeholders, then enable:

```bash
sudo ln -s /etc/nginx/sites-available/easykai.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Start Services

```bash
pm2 start ecosystem.config.js
pm2 save
sudo env PATH=$PATH pm2 startup systemd -u www-data --hp /home/www-data
```

---

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DEPLOY_MARKET` | Yes | Market code (`cn` for China) |
| `DEPLOY_DOMAIN` | Yes | Primary domain name |
| `DB_PATH` | Yes | SQLite database path |
| `JWT_SECRET` | Yes | JWT signing secret (64-char random hex) |
| `FLASK_SECRET_KEY` | Yes | Flask session secret (64-char random hex) |
| `EASYKAI_MODE` | Yes | Operation mode (`main`) |
| `PG_HOST` | No | PostgreSQL host (optional) |
| `PG_PORT` | No | PostgreSQL port |
| `PG_DB` | No | PostgreSQL database name |
| `PG_USER` | No | PostgreSQL username |
| `PG_PASSWORD` | No | PostgreSQL password |
| `DASHSCOPE_TEXT_KEY` | No | DashScope API key |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key |

---

## Service Management

All services are managed via PM2:

```bash
pm2 status          # View all processes
pm2 logs            # View logs (all)
pm2 logs easykai-admin  # View specific service logs
pm2 restart all     # Restart all services
pm2 stop all        # Stop all services
pm2 start all       # Start all services
```

### Running Services

| PM2 Name | Port | Description |
|----------|------|-------------|
| `easykai-main` | 8081 | Main site backend |
| `easykai-platform` | 8083 | Platform & auth |
| `easykai-admin` | 8084 | Admin panel |
| `easykai-health` | — | Health guardian (watchdog) |

---

## SSL Certificate

### Initial Setup

The bootstrap script automatically requests SSL certificates. For manual setup:

```bash
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

To upgrade to the latest version:

```bash
cd /var/www/verorun
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
pm2 restart all
```

---

## Troubleshooting

### Service not starting

```bash
pm2 logs easykai-main --lines 50
```

Common causes:
- `.env` file missing or misconfigured
- Port already in use: `sudo lsof -i :8081`
- Python dependency missing: `pip install -r requirements.txt`

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

SQLite databases are stored in `data/`. If you encounter corruption:

```bash
sqlite3 data/easykai.db "PRAGMA integrity_check;"
```

---

For additional help, visit [docs.verorun.com](https://docs.verorun.com).
