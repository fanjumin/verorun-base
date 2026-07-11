# 统一域名模块（Domain & Nginx Manager）设计文档

> **版本**：v1.0  
> **状态**：设计阶段（待立项）  
> **更新**：2026-07-11

## 一、概述

将「子域名管理」与「Nginx 配置生成/应用」合并为一个统一模块，实现：用户在域名商配置 `*.easykai.cn`（泛解析）后，服务器端完全自主控制子域名的创建、绑定端口、HTTPS 证书，不再依赖域名商管理面板。

## 二、核心前提

用户在域名商配置 **泛解析（wildcard DNS）**：
```
*.easykai.cn  A  服务器IP
```
这是一次性操作。之后所有子域名自动解析到服务器，无需再逐个加 DNS 记录。任何域名服务商（阿里云/GoDaddy/Cloudflare/境外等）均支持。

**此前提消除 DNS API 依赖**，模块只需关注服务器端（Nginx + 证书）。

## 三、模块能力分层

```
Domain & Nginx Manager
├── 前提     → 用户在域名商配 *.easykai.cn 泛解析（一次性，手动）
├── Nginx 层 → 生成/校验/应用/reload server 块
├── 证书层   → 泛域名证书 *.easykai.cn（一张证书覆盖所有子域名）
├── 端口分配 → 插件声明端口（如 8089），模块记录 + 生成反代
├── 数据层   → site_domains 表（现有，含 subdomain/full_domain/service_port 等）
└── 编排层   → "一键添加子域名" = Nginx 生成 → 校验 → 应用 → 证书 → 入库
```

## 四、Nginx 权限方案（选定：受限 sudo 白名单）

### 推荐方案：受限 sudo 白名单

给 `easykai` 用户配置仅限特定命令的免密 sudo（`/etc/sudoers.d/easykai-nginx`）：

```
easykai ALL=(root) NOPASSWD: /usr/sbin/nginx -t
easykai ALL=(root) NOPASSWD: /usr/bin/systemctl reload nginx
easykai ALL=(root) NOPASSWD: /usr/bin/tee /etc/nginx/sites-enabled/*
easykai ALL=(root) NOPASSWD: /usr/bin/tee /etc/nginx/sites-available/*
easykai ALL=(root) NOPASSWD: /bin/cp -f /tmp/nginx_rollback_* /etc/nginx/sites-enabled/*
easykai ALL=(root) NOPASSWD: /bin/rm /etc/nginx/sites-enabled/*.disabled
```

### 为什么选这个方案

| 维度 | sudo 白名单 | 特权 Agent | 队列+人工 |
|------|-----------|-----------|----------|
| 开发成本 | 🟢 低（纯配置） | 🟡 中（需独立进程） | 🟢 低 |
| 安全风险 | 🟡 中（命令范围是关键） | 🟢 高（最小攻击面） | 🟢 高（人工确认壁垒） |
| 用户体验 | 🟢 好（实时生效） | 🟢 好 | 🟡 差（需手动确认） |
| 维护成本 | 🟢 低 | 🟡 中 | 🟢 低 |
| **结论** | **✅ 推荐**（同机、体验最佳） | 保留（异地/多机场景） | 备选 |

同机部署场景下，sudo 白名单是性价比最高的方案。命令列表经过精心限定——只允许 `nginx -t`（校验）、`reload`（热加载）、`tee` 写特定目录（通过目录限定防篡改），以及受控的回滚 `cp`/`rm`。

## 五、安全护栏（必须实现）

1. **`nginx -t` 强制校验**：应用前先测试，失败**绝不 reload**（否则全站 502）
2. **自动备份 + 回滚**：
   - 写入前 `cp /etc/nginx/sites-enabled/X /tmp/nginx_rollback_X`
   - reload 失败 → 自动还原 `/tmp/nginx_rollback_X` → 再次 reload
   - reload 成功 → 清理备份
3. **输入严格校验**：
   - 域名格式正则：`^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$`（仅允许合法二级域名）
   - 端口范围：1024-65535
   - 禁止自由编辑 server 块原文——只允许填参数（域名、端口），生成逻辑固定
4. **server 块模板固定**——不接受用户自定义 `location`/`proxy_pass`，防配置注入

## 六、插件端口绑定与子域名升级

### 插件启用时将插件路由从路径升级为子域名

**路径模式**（默认）：`easykai.cn/plugins/shop`
- 已有机制，无需 Nginx 变更

**子域名模式**（启用时选择）：`shop.easykai.cn`
- 插件声明需要端口（如 8089）
- 后台生成 Nginx server 块：`shop.easykai.cn → proxy_pass 127.0.0.1:8089`
- 写入 site_domains（service_port=8089, subdomain=shop）
- 应用 Nginx + 证书

| 模式 | 适用场景 |
|------|---------|
| 路径模式 | 轻量插件，不需独立入口 |
| 子域名模式 | 需要独立品牌/独立服务的插件（电商、社区等）|

## 七、HTTPS 证书策略

**泛域名证书 `*.easykai.cn`**——一张证书覆盖所有子域名。

```bash
certbot certonly --manual --preferred-challenges dns \
  -d "easykai.cn" -d "*.easykai.cn"
```

优势：
- 新增子域名**无需重新签发证书**（已覆盖）
- 非 certbot 签发方式同样适用（手动 DNS-01 + 上传至 Nginx）

Nginx 引用：
```nginx
ssl_certificate     /etc/letsencrypt/live/easykai.cn/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/easykai.cn/privkey.pem;
```

## 八、server 块模板

每个独立子域名生成的 Nginx 配置模板：

```nginx
server {
    listen 80;
    server_name {{subdomain}}.easykai.cn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name {{subdomain}}.easykai.cn;
    client_max_body_size 50M;

    ssl_certificate     /etc/letsencrypt/live/easykai.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/easykai.cn/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:{{service_port}};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 九、部署脚本集成

### 安装时自动配置

部署脚本（ansible/paramiko）执行：
1. 写入 sudo 白名单 `/etc/sudoers.d/easykai-nginx`
2. 验证：`sudo -u easykai sudo -n nginx -t` 无报错
3. 生成三默认子域名：
   ```
   platform.easykai.cn → 8081
   agent.easykai.cn    → 8084
   admin.easykai.cn    → 8084（或独立端口）
   ```
4. 写 `/etc/nginx/sites-available/easykai-platform.conf`（以及 agent/admin）→ symlink 到 sites-enabled
5. `nginx -t && systemctl reload nginx`
6. 幂等：配置存在则跳过

### 日常运维

后台"添加子域名"按钮 → 模块编排：
```
① 校验域名格式 + 端口可用性
② 生成 server 块 → 写入 /etc/nginx/sites-available/<name>.conf
③ ln -s 到 sites-enabled
④ nginx -t（失败则回滚：①删除 → ②还原备份）
⑤ systemctl reload nginx
⑥ 写入 site_domains 表
⑦ 返回成功（含生成的 Nginx 配置预览）
```

## 十、与现有系统集成

### 现有 asset: site_domains 表

```sql
CREATE TABLE IF NOT EXISTS site_domains (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    site_config_id INTEGER NOT NULL DEFAULT 1,
    subdomain      TEXT NOT NULL,
    full_domain    TEXT NOT NULL UNIQUE,
    display_name   TEXT NOT NULL,
    template       TEXT DEFAULT 'default',
    is_published   INTEGER DEFAULT 1,
    page_keys_json TEXT DEFAULT '["home"]',
    sort_order     INTEGER DEFAULT 0,
    service_port   INTEGER,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_config_id) REFERENCES site_configs(id)
);
```

表结构完全匹配所需属性，无需变更。

### 现有 asset: site_domain_middleware.py

运行时中间件根据 Host header 查 `site_domains` JOIN `site_configs`，决定当前站点主题/端口。**模块无需改动中间件**——它只是添加记录到表，中间件自动生效。

### 现有 asset: admin/app.py get_nginx_config

已有 `GET /admin/api/domains/<id>/nginx-config` 生成 server 块文本。为 L1 能力，已实现。

## 十一、分阶段实施计划

| 阶段 | 内容 | 依赖 |
|------|------|------|
| P1 | 插件化（Phase 5）：后台 CRUD 抽离为插件 | 无，可立即做 |
| P2 | Nginx 应用能力（L2）：sudo 白名单 + 备份/回滚 | P1 完成 |
| P3 | 编排：一键添加子域名（Nginx 生成→应用→入库）| P2 完成 |
| P4 | 插件端口绑定 + 子域名升级入口 | P2 完成 |
| P5 | 泛域名证书 + 部署脚本集成 | P2 完成 |

## 十二、自检清单

- [ ] sudo 白名单命令列表已审核（无路径穿越风险）
- [ ] `nginx -t` 校验在每次 apply 前执行
- [ ] 回滚逻辑覆盖：校验失败 / reload 失败
- [ ] 输入校验正则防御配置注入
- [ ] server 块模板不可用户自定义
- [ ] 幂等性：同一域名重复添加 = 更新（非覆盖）
- [ ] 审计日志：每次 Nginx 变更记录操作人 + 时间 + diff
