# 统一域名模块（Domain & TLS Manager）设计文档

> **版本**：v2.0（对齐国际主流 SaaS 实践）
> **状态**：设计阶段（待立项）
> **更新**：2026-07-11

## 一、概述

将「子域名管理」与「HTTPS/反向代理」合并为一个统一模块，目标：**用户在后台添加子域名/绑定插件时只填一个名字，证书与路由全自动**——达到 Vercel / Netlify 级"零运维"体验。

## 二、国际主流平台怎么做（调研结论）

| 平台 | TLS 技术 | 用户操作量 |
|------|---------|-----------|
| **Vercel** | 自建 ACME：非通配用 HTTP-01，通配用 DNS-01 | 仅配 DNS |
| **Netlify** | Let's Encrypt 自动签发/续签；Netlify DNS 下自动通配证书 | 仅配 DNS |
| **Cloudflare** | 边缘托管证书 + Cloudflare for SaaS（自定义主机名） | 面板点几下 |
| **现代自建 SaaS** | **Caddy On-Demand TLS** | 仅配 DNS |

**共识**：用户唯一手动动作 = 配 DNS 解析。证书**自动申请、自动续签、自动装配**，无 certbot 脚本、无 cron、无手动改配置。

**黄金方案 = Caddy On-Demand TLS**：TLS 握手瞬间，Caddy 调用平台的校验 API（`ask`）确认域名合法后，即时向 Let's Encrypt 申请证书并缓存，**无需预配置、无需 reload、无需 DNS API**（HTTP-01 验证）。这是"让用户最省心"的业界天花板做法，被大量 SaaS 用于支撑数千自定义域名。

**参考来源见文末。**

## 三、选型决策：Caddy 作为 TLS 边缘层（替代 Nginx+certbot 手动模式）

### 现状 vs 目标

| 维度 | 现状（Nginx + certbot 手动） | 目标（Caddy On-Demand TLS） |
|------|------------------------------|------------------------------|
| 新增子域名 | 改配置文件 + `nginx -t` + reload | **零操作**，请求进来自动生效 |
| 证书申请 | 手动 certbot | **自动**（握手时签发） |
| 证书续签 | cron 定时 | **自动**（到期前自动续） |
| 通配证书 | 需 DNS-01 + DNS API | 免（On-Demand 用 HTTP-01 逐域签） |
| 用户后台操作 | 复制 Nginx 配置手动贴 | **填个子域名名字即可** |

### 目标架构

```
用户在域名商配 *.easykai.cn 泛解析（一次性，唯一手动步骤）
        │
        ▼
Caddy（:80 + :443，公网入口，On-Demand TLS）
   ├─ ask → 平台校验 API：GET /internal/caddy/check?domain=xxx
   │         查 site_domains 表，合法返回 200，否则拒绝（防滥用）
   ├─ 自动签发/续签 Let's Encrypt 证书（HTTP-01），本地缓存
   └─ 按 Host 反向代理到后端
        │
        ▼
后端服务（loopback）：platform 8081 / auth 8083 / admin 8084 / 插件端口
```

Caddy 独占 80/443；后端服务改监听 `127.0.0.1`（仅回环，不对公网暴露）。

## 四、核心前提（用户唯一手动步骤）

域名商配置**泛解析**：
```
*.easykai.cn  A  服务器IP
```
一次性操作，任何服务商（阿里云/GoDaddy/Cloudflare/境外）均支持。之后所有子域名自动解析到服务器，Caddy 负责签证书 + 路由。

## 五、Caddy 最小配置

```caddy
{
    # On-Demand TLS：握手时向校验 API 询问是否放行
    on_demand_tls {
        ask http://127.0.0.1:8084/internal/caddy/check
        interval 2m
        burst 5
    }
    email admin@easykai.cn
}

# 主域名 + 已知固定子域名（显式声明，最稳）
platform.easykai.cn {
    reverse_proxy 127.0.0.1:8081
}
agent.easykai.cn {
    reverse_proxy 127.0.0.1:8084
}

# 通配 catch-all：任意子域名，按需签证书 + 动态路由
*.easykai.cn {
    tls {
        on_demand
    }
    # 动态反代：由平台返回目标端口，或在此按 Host 映射
    reverse_proxy 127.0.0.1:8081
}
```

## 六、校验 API（防滥用的关键）

Caddy 每次为新域名签证书前会调用此接口。**必须实现**，否则攻击者可用随机域名耗尽 Let's Encrypt 速率限制。

```
GET /internal/caddy/check?domain=shop.easykai.cn
  → 查 site_domains WHERE full_domain=? AND is_published=1
  → 命中返回 200（放行签发）
  → 未命中返回 403（拒绝）
```

- 仅监听回环（127.0.0.1），不对公网暴露
- 域名必须先在后台 site_domains 表登记，才会被签发——**签发权与业务数据绑定**

## 七、模块能力分层

```
Domain & TLS Manager
├── 前提     → 用户配 *.easykai.cn 泛解析（一次性，手动）
├── 边缘层   → Caddy On-Demand TLS（自动证书 + 反代）
├── 校验 API → /internal/caddy/check（查 site_domains 决定放行）
├── 端口分配 → 插件声明端口，模块记录 + 动态路由映射
├── 数据层   → site_domains 表（现有，含 subdomain/full_domain/service_port）
└── 编排层   → "添加子域名" = 写 site_domains 表（就绪，无需碰配置文件）
```

**注意**：引入 Caddy 后，"添加子域名"简化为**仅写一行数据库记录**——无需生成/写入/reload 任何配置文件。证书与路由由 Caddy 运行时按 site_domains 表自动处理。这是相比原 Nginx 方案的最大简化。

## 八、插件端口绑定与子域名升级

| 模式 | 示例 | 实现 |
|------|------|------|
| 路径模式（默认） | `easykai.cn/plugins/shop` | 无需任何域名操作 |
| 子域名模式 | `shop.easykai.cn` | 后台 site_domains 加一条记录（subdomain=shop, service_port=8089）→ Caddy 自动签证书 + 路由到 8089 |

插件启用时让用户选择路径或独立子域名；选子域名仅需写库，其余全自动。

## 九、迁移与兼容（重要：不推翻现有 Nginx）

当前生产用 Nginx（easykai.cn / agent / platform 等已在 :8081/8083/8084）。**不建议一次性替换**，采用渐进式：

**阶段 A（现状保留）**：Nginx 继续服务现有固定域名，certbot 现有证书不动。

**阶段 B（Caddy 并行接管通配）**：
- Caddy 监听非标端口或新增泛解析专用入口，仅接管 `*.easykai.cn` 动态子域名
- 或：Caddy 置于 Nginx 之前作为 TLS 终止层，Nginx 退到 loopback

**阶段 C（可选，完全迁移）**：Caddy 统一接管 80/443，Nginx 完全退到内部。

> 决策点：是否引入 Caddy 是架构级选择。若不引入，退回 v1 的"Nginx + sudo 白名单 + certbot"手动方案（见附录 A），但用户操作量更大。

## 十、安全护栏

1. **校验 API 强制**：`ask` 未通过绝不签发，防随机域名滥用
2. **速率限制**：`interval` + `burst` 限制签发频率
3. **证书日志监控**：复用现有 health_check `ssl_cert` 检查器监控到期
4. **后端仅 loopback**：8081/8083/8084 改监听 127.0.0.1，不对公网暴露
5. **输入校验**：子域名正则 `^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$`，端口 1024-65535

## 十一、与现有系统集成

### 现有 asset 复用

| 资产 | 用途 |
|------|------|
| `site_domains` 表 | 域名登记 + 校验 API 数据源（结构已就绪，含 service_port）|
| `site_domain_middleware.py` | 运行时按 Host 解析站点主题（不变） |
| plugins/site_domains（本次已解耦）| 后台 CRUD UI，未来加"绑定子域名"入口 |
| health_check `ssl_cert` | 证书到期监控（Caddy 自动续签后可保留作双保险）|

### 已存在的 Nginx L2 能力（勿重写）

`auth-center/routes/admin.py` 已实现一套 Nginx 配置生成/写入/reload：
- `_generate_domain_nginx_config()`：写 server 块
- `_reload_nginx()`：`sudo /usr/sbin/nginx -s reload`（受 `NGINX_SNIPPETS_DIR` 开关）

若最终不引入 Caddy 而走 Nginx 方案，直接复用这套，不要重写。

## 十二、分阶段实施计划

| 阶段 | 内容 | 依赖 |
|------|------|------|
| P1 ✅ | site_domains 后台 CRUD 插件化 | 已完成 |
| P1.5 ✅ | Caddy 校验 API（/internal/caddy/check）+ Caddyfile（测试/生产）| 已完成 |
| P1.6 ✅ | **On-Demand TLS 机制生产验证（非标 8443，不碰 443）** | 已完成，见 §十四 |
| P2 | 决策：引入 Caddy（推荐）or 沿用 Nginx | 架构决策 |
| P3a（Caddy 路线）| Caddy 接管公网 443 + Let's Encrypt 真实签发 + 后端退 loopback | P2，需停机窗口 |
| P3b（Nginx 路线）| sudo 白名单 + 复用 admin.py 的 L2 + certbot 通配证书 | P2 |
| P4 | 插件"绑定子域名"入口（写 site_domains 即生效）| P3 |
| P5 | 部署脚本集成：装边缘层 + 生成默认三子域名 | P3 |

## 十三、自检清单

- [x] Caddy 校验 API 已实现且仅回环监听
- [x] `ask` 拒绝未登记域名（防滥用）
- [x] 速率限制 interval/burst 已配置
- [ ] 后端服务改监听 127.0.0.1（P3 生产切换时做）
- [x] 泛解析前提已在部署文档中说明
- [ ] 现有 Nginx/证书迁移路径明确（不中断现有域名）
- [x] 子域名输入校验正则

## 十四、On-Demand TLS 机制验证记录（2026-07-11）

在生产机（***REMOVED***）完成机制验证，**全程不碰生产 80/443**，Nginx 与核心服务无影响。

### 验证环境
- Caddy 2.6.2（apt 安装，systemd 服务已 `stop` + `disable`，防止抢占 80/443）
- 手动前台运行监听非标端口 **8080/8443**，使用 Caddy 内置 CA（`tls internal`）自签证书
- 配置：[deploy/caddy/Caddyfile.test](file:///f:/Sites/VeroRun/deploy/caddy/Caddyfile.test)
- 校验端点：admin(:8084) 的 `/internal/caddy/check`（查 site_domains 表）

### 验证结果

| 测试项 | 命令 | 结果 | 结论 |
|--------|------|------|------|
| **已登记域名** | `curl -k --resolve www.easykai.cn:8443:127.0.0.1 https://www.easykai.cn:8443/` | `HTTP=200` | ask→200→自动签证书→握手成功 ✅ |
| **未登记域名** | `curl -k --resolve nope-xyz-123.easykai.cn:8443:127.0.0.1 ...` | 握手失败 | ask→403→拒绝签发 ✅ |

### Caddy 日志证据链（已登记域名）
```
tls.on_demand  obtaining new certificate  server_name=www.easykai.cn
tls.obtain     lock acquired
tls.obtain     certificate obtained successfully  identifier=www.easykai.cn
```
未登记域名 `nope-xyz-123.easykai.cn` 无任何 obtaining 记录——被校验 API 挡在签发前。

### 结论
On-Demand TLS + ask 校验机制在生产环境验证通过：
- **新子域名首次访问即自动签发证书**（无需预配置、无需 reload）
- **未登记域名被校验 API 拒绝**（防滥用 Let's Encrypt 速率限制）
- 达到 Vercel / Netlify 级"用户只配 DNS，其余全自动"的目标

### 验证后环境状态（已清理）
- Caddy 验证进程已停，8443/8080 释放
- 生产 80/443 全程 Nginx 服务，未受影响
- Caddy 二进制保留（`apt` 装，disabled 状态），供 P3 正式切换复用
- 生产切换（P3a）仍是全站命门级操作，需专门停机窗口 + 回滚预案

## 附录 A：Nginx + certbot 手动方案（备选，若不引入 Caddy）

保留 v1 方案要点，供不引入 Caddy 时参考：

- **权限**：`easykai` 受限 sudo 白名单（`nginx -t` / `reload` / 写 sites-enabled）
- **通配证书**：`certbot certonly --dns-<provider> -d easykai.cn -d "*.easykai.cn"`（**需 DNS API**，因通配强制 DNS-01）
- **单域名证书**：泛解析下可用 HTTP-01，每子域签一张（免 DNS API）
- **安全护栏**：`nginx -t` 强制校验 + 备份回滚 + 输入校验 + 模板固定

**核心差异**：Nginx 方案每加域名需改配置 + reload + 管理证书续签；Caddy 方案写库即生效、证书全自动。**用户省心度：Caddy > Nginx。**

## 附录 B：参考来源

- [Vercel — Working with SSL Certificates](https://vercel.com/docs/domains/working-with-ssl)
- [Netlify — HTTPS (SSL)](https://docs.netlify.com/manage/domains/secure-domains-with-https/https-ssl/)
- [Caddy — On-Demand TLS](https://caddyserver.com/on-demand-tls)
- [Caddy TLS On-Demand 2026 Guide](https://fivenines.io/blog/caddy-tls-on-demand-complete-guide-to-dynamic-https-with-lets-encrypt/)
- [Multi-Tenant SaaS with Caddy + Cloudflare + Nginx](https://tallcms.com/zh-CN/docs/multi-tenant-saas-on-digitalocean-with-caddy-cloudflare-nginx-and-ploi)
- [SaaS Custom Domains on AWS: Past the 25 SSL Certificate Wall](https://techunfiltered.dev/scalable-ssl-saas-custom-domains-aws)
