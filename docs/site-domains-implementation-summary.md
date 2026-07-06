# Site Domains 子域名管理系统 — 实施状态总结

> 生成日期：2026-07-06
> 会话目的：实现 site_domains 与 cluster_services 合并，增加服务发现和 Nginx 配置生成

---

## 一、已完成功能

### 1. site_domains 管理（浏览器操作）
- **入口**：`https://agent.easykai.cn/admin` → **System → Site Domains**
- **操作**：创建/编辑/删除子域名
- **新增"类型"选项**：
  - **内容站点**（`service_port=NULL`）→ 走 site app(8081)，无需 Nginx 配置
  - **独立服务**（`service_port=整型`）→ 生成 Nginx 配置，需要手动同步到服务器
- **配额指示器**：当前用量/上限
- **Config 按钮**：独立服务可查看 Nginx 配置文本并复制

### 2. 数据库变更
- `site_domains` 表新增 `service_port INTEGER DEFAULT NULL` 列
- `cluster_services` 表已删除（种子数据迁移到 site_domains）
- 3 个默认种子数据：www(官网), agent(管理后台), platform(用户中心)

### 3. 中间件
- `site_domain_middleware.py` 的 `g.current_site` 注入：
  - `service_type`: `'independent'` 或 `'content'`
  - `service_port`: 端口号或 `None`

### 4. Nginx 配置生成（本地）
- 文件路径：`F:\Sites\VeroRun\nginx-domains\sites-enabled/{full_domain}.conf`
- 创建/更新/删除子域名时自动生成或删除
- API 端点 `GET /admin/api/domains/<id>/nginx-config` 返回配置文本

### 5. 服务端 Nginx 配置
- 已创建目录：`/etc/nginx/snippets/easykai-domains/`
- 已在 `easykai.conf` 添加：`include /etc/nginx/snippets/easykai-domains/*.conf;`
- 原始配置已备份到：`/etc/nginx/sites-enabled/easykai.conf.bak`

---

## 二、涉及文件

| 文件 | 改动说明 |
|------|---------|
| `auth-center/models/database.py` | `site_domains` 表加 `service_port` 列 + migration |
| `auth-center/middleware/site_domain_middleware.py` | 注入 `service_type` / `service_port` |
| `auth-center/routes/admin.py` | Nginx 配置生成函数 + CRUD 更新（3 个端点）+ GET nginx-config |
| `admin/templates/partials/site_domains.html` | 类型选择器 + 端口列 + Config 按钮 + 配置查看弹窗 |
| `admin/templates/admin.html` | 移除 cluster_services 的 include |
| `admin/templates/partials/icons.html` | 移除 cluster_services 导航项 |
| `admin/templates/partials/cluster_services.html` | **已删除** |

---

## 三、未完成/待解决的问题

### 3.1 Nginx 配置自动同步（最高优先级）
当前问题：`nginx-domains/sites-enabled/` 的文件生成在**本地电脑**，但需要手动 `rsync` 到服务器。

**建议方案**：在 `admin.py` 中的 CRUD 端点里增加 Paramiko SSH 调用，创建/更新/删除子域名时直接：
1. 生成文件到本地
2. SCP 上传到 `/etc/nginx/snippets/easykai-domains/`
3. SSH 执行 `sudo nginx -s reload`

**下一步会话应该做这个。**

### 3.2 Site App 多站点渲染
当前子域名中间件能识别 `g.current_site`，但 `site/app.py` 的所有路由**不根据子域名切换内容**。`job.easykai.cn` 和 `www.easykai.cn` 渲染完全相同。

**建议方案**：改造 `site/app.py` 的路由，根据 `g.current_site['template']` 选择不同模板。

### 3.3 Wildcard SSL 证书
当前没有 `*.easykai.cn` 通配符证书，新子域名无法 HTTPS 访问。如果不需要 HTTPS 可以跳过。

---

## 四、技术细节

### API 端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/admin/api/domains` | GET | 列表+配额 |
| `/admin/api/domains` | POST | 创建（接受 `service_port`） |
| `/admin/api/domains/<id>` | PUT | 更新（接受 `service_port`） |
| `/admin/api/domains/<id>` | DELETE | 删除 |
| `/admin/api/domains/quota` | GET | 配额 |
| `/admin/api/domains/<id>/nginx-config` | GET | 返回 Nginx 配置文本 |

### Nginx 配置模板路径
- **本地生成**：`F:\Sites\VeroRun\nginx-domains\sites-enabled/{full_domain}.conf`
- **服务器目标**：`/etc/nginx/snippets/easykai-domains/{full_domain}.conf`

### 服务器信息
- IP：`***REMOVED***`
- 用户：`easykai` / 密码：`***REMOVED***`
- 网站目录：`/home/easykai/easykai-workspace/easykai.cn/`
- 服务名（之前用了错误的 `easykai`，正确是 `auth-center.service`）：
  - `auth-center.service` → 8081（主站）
  - `admin.service` → 8084（管理后台）
  - `platform.service` → 8083（用户面板）
