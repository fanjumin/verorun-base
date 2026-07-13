# Social Media Mini-Program — Deployment Guide

> Version: v1.0 | Date: 2026-07-13  
> System: VeroRun / easykai.cn

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Telegram Mini App](#2-telegram-mini-app)
3. [LINE MINI App](#3-line-mini-app)
4. [Douyin / Toutiao Mini-Program](#4-douyin--toutiao-mini-program)
5. [WeChat Mini Program](#5-wechat-mini-program)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Prerequisites

### 1.1 System Requirements

| Component | Detail |
|-----------|--------|
| Server | Linux with Nginx, Gunicorn |
| Domain | easykai.cn (or your custom domain) |
| SSL | HTTPS required for all platforms |
| Python | 3.10+ |
| Database | SQLite (existing `easykai.db`) |

### 1.2 Platform Accounts

| Platform | Account Required | Registration URL |
|----------|-----------------|------------------|
| Douyin | Enterprise mini-program | https://developer.open-douyin.com/ |
| Toutiao | Same as Douyin (ByteDance ecosystem) | Same as above |
| WeChat | Enterprise mini-program | https://mp.weixin.qq.com/ |
| Telegram | Bot token from @BotFather | https://t.me/BotFather |
| LINE | LINE Developers account | https://developers.line.biz/ |

### 1.3 Dev Accounts Configuration

Add platform credentials via the Admin Panel:

```
Admin → Developer Accounts → Add Account
```

Or via API:

```bash
curl -X POST https://easykai.cn/admin/dev-accounts/ \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "telegram",
    "account_name": "My Telegram Bot",
    "bot_token": "123456:ABC-DEF1234ghikl",
    "is_active": 1
  }'
```

---

## 2. Telegram Mini App

### 2.1 Create Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Save the bot token (e.g., `123456:ABC-DEF1234ghikl`)
4. Send `/setmenubutton` to configure the mini-app button

### 2.2 Generate Mini-App

1. In Admin Panel, go to **Site Builder** → **Mini Apps**
2. Select **Telegram** platform
3. Click **Generate**
4. Wait for generation to complete
5. Download the `.zip` file

### 2.3 Deploy Static Files

Upload the generated files to your server:

```bash
# On your local machine
scp telegram-mini-app-*.zip easykai@***REMOVED***:/tmp/

# On the server
ssh easykai@***REMOVED***
cd /home/easykai/easykai-workspace/easykai.cn/static/
mkdir -p mini-apps/telegram
cd mini-apps/telegram
unzip /tmp/telegram-mini-app-*.zip
```

### 2.4 Configure Nginx

Add location block to serve the mini-app:

```nginx
# /etc/nginx/sites-enabled/easykai.conf

location /mini-apps/telegram/ {
    alias /home/easykai/easykai-workspace/easykai.cn/static/mini-apps/telegram/;
    index index.html;
    try_files $uri $uri/ /mini-apps/telegram/index.html;
}
```

Reload Nginx:

```bash
nginx -t && systemctl reload nginx
```

### 2.5 Set Menu Button

Via Admin Panel API:

```bash
curl -X POST https://easykai.cn/admin/site-builder/mini-app/deploy/telegram \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<task_id>",
    "deploy_url": "https://platform.easykai.cn/mini-apps/telegram/"
  }'
```

Or manually via Bot API:

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setChatMenuButton" \
  -H "Content-Type: application/json" \
  -d '{
    "menu_button": {
      "type": "web_app",
      "text": "AI Advisor",
      "web_app": {
        "url": "https://platform.easykai.cn/mini-apps/telegram/"
      }
    }
  }'
```

### 2.6 Verify

1. Open Telegram
2. Find your bot
3. Click the menu button (bottom-left)
4. The mini-app should open with the AI Advisor chat interface
5. Try sending a message — the AI should respond

---

## 3. LINE MINI App

### 3.1 Create LINE Channel

1. Go to [LINE Developers Console](https://developers.line.biz/console/)
2. Create a new **Provider** (if you don't have one)
3. Create a new **LINE Login** channel
4. Note the **Channel ID** and **Channel Secret**

### 3.2 Create LIFF App

1. In your LINE Login channel, go to **LIFF** tab
2. Click **Add**
3. Configure:
   - **Size**: Full
   - **Endpoint URL**: `https://platform.easykai.cn/mini-apps/line/`
   - **Scopes**: `profile`, `openid`
4. Note the **LIFF ID**

### 3.3 Generate and Deploy

Same as Telegram steps 2.2-2.4, but for LINE platform:

```bash
# On server
cd /home/easykai/easykai-workspace/easykai.cn/static/
mkdir -p mini-apps/line
cd mini-apps/line
unzip /tmp/line-mini-app-*.zip
```

### 3.4 Nginx Configuration

```nginx
location /mini-apps/line/ {
    alias /home/easykai/easykai-workspace/easykai.cn/static/mini-apps/line/;
    index index.html;
    try_files $uri $uri/ /mini-apps/line/index.html;
}
```

### 3.5 Update LIFF Endpoint

Via Admin Panel API:

```bash
curl -X POST https://easykai.cn/admin/site-builder/mini-app/deploy/line \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<task_id>",
    "deploy_url": "https://platform.easykai.cn/mini-apps/line/"
  }'
```

### 3.6 Add to LINE Official Account

1. Go to LINE Developers Console → your channel
2. Go to **Channel settings** → **Messaging API**
3. Enable **Webhook** and set the webhook URL
4. Link the LIFF app to your LINE Official Account

### 3.7 Verify

1. Open LINE app
2. Find your LINE Official Account
3. Open the chat and tap the menu
4. The LIFF mini-app should open with the AI Advisor
5. Test chat functionality

---

## 4. Douyin / Toutiao Mini-Program

### 4.1 Register Developer Account

1. Go to [Douyin Open Platform](https://developer.open-douyin.com/)
2. Register as an enterprise developer
3. Create a mini-program application
4. Note the **App ID** and **App Secret**

### 4.2 Generate Mini-Program

1. In Admin Panel, go to **Site Builder** → **Mini Apps**
2. Select **Douyin** platform
3. Enter your App ID in the platform configuration
4. Click **Generate**
5. Download the `.zip` file

### 4.3 Import to Douyin Developer Tools

1. Download [Douyin Developer Tools](https://developer.open-douyin.com/docs/resource/tools)
2. Open the tool and create a new project
3. Import the generated `.zip` or directory
4. The tool will recognize the project structure automatically

### 4.4 Configure Domain Whitelist

In the Douyin Developer Console:

1. Go to **Development** → **Development Settings**
2. Add `https://platform.easykai.cn` to the **request domain** whitelist
3. Add `wss://platform.easykai.cn` to the **WebSocket domain** whitelist

### 4.5 Test and Submit

1. Use the **Preview** feature in DevTools to test on your phone
2. Test login, chat, and page navigation
3. Once verified, click **Upload** to submit for review
4. Douyin review typically takes 1-3 business days

### 4.6 Toutiao Compatibility

Toutiao uses the same ByteDance ecosystem. The generated Douyin code is compatible with Toutiao. Simply:
1. Import the same project into Toutiao DevTools
2. Configure the Toutiao-specific App ID
3. Upload and submit for review

---

## 5. WeChat Mini Program

### 5.1 Register Developer Account

1. Go to [WeChat Official Accounts Platform](https://mp.weixin.qq.com/)
2. Register as an enterprise mini-program developer
3. Complete business verification
4. Note the **App ID** and **App Secret**

### 5.2 Generate Mini-Program

1. In Admin Panel, go to **Site Builder** → **Mini Apps**
2. Select **WeChat** platform
3. Enter your App ID in the platform configuration
4. Click **Generate**
5. Download the `.zip` file

### 5.3 Import to WeChat Developer Tools

1. Download [WeChat DevTools](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. Open the tool and create a new project
3. Enter your App ID
4. Import the generated project

### 5.4 Configure Domain Whitelist

In the WeChat Mini Program Admin Console:

1. Go to **Development** → **Development Settings**
2. Add `https://platform.easykai.cn` to the **request domain** whitelist
3. Add `wss://platform.easykai.cn` to the **socket domain** whitelist

### 5.5 Test and Submit

1. Use the **Preview** feature to test on your phone
2. Test login, chat, and page navigation
3. Click **Upload** to submit for review
4. WeChat review typically takes 1-7 business days

---

## 6. Troubleshooting

### 6.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Mini-app fails to load | Nginx not configured | Check `/etc/nginx/sites-enabled/easykai.conf` |
| Chat returns 401 | JWT not sent | Verify Authorization header is set |
| CORS errors | Wrong domain | Ensure Nginx CSP allows the platform domain |
| AI not responding | API key not configured | Check `mp_ai_api_key` in system_config |
| Login fails | Platform credentials invalid | Verify dev_accounts configuration |
| File not found (404) | Static files not deployed | Check `rsync` path and permissions |

### 6.2 Debug Commands

```bash
# Check Nginx configuration
nginx -t

# Check service status
systemctl status admin.service
systemctl status auth-center.service

# Test API endpoints
curl -X POST https://platform.easykai.cn/api/v1/mini-program/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","platform":"test"}'

# Check static files
ls -la /home/easykai/easykai-workspace/easykai.cn/static/mini-apps/

# View logs
journalctl -u admin.service -f
journalctl -u auth-center.service -f
```

### 6.3 Rollback

If deployment fails:

```bash
# Restore from backup
git checkout <previous_commit>
rsync -av --delete --exclude=data/ \
  /home/easykai/easykai-workspace/easykai.cn/ \
  /path/to/backup/
systemctl restart admin.service auth-center.service
```