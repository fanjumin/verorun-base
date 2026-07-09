# 插件系统修复 — 任务交接文档

> 生成时间：2026-07-09
> 服务器：easykai@***REMOVED***，网站根目录 `/home/easykai/easykai-workspace/easykai.cn/`
> Admin 服务：`agent.easykai.cn` → `:8084`（gunicorn，systemd 服务名 `admin`）

## 一、背景

将系统若干模块解耦为插件（analytics、health_check、ai_tools、ali_api、captcha_embedded、coupons、novasense、order_notify、reviews、wishlist），
插件位于 `plugins/<identifier>/`，各自独立数据库，通过 `PluginManager` 统一生命周期管理。
本轮会话集中修复"插件解耦后菜单与功能不可用"的一系列问题。

## 二、插件系统关键架构（现状）

- 插件发现/加载：`plugin_manager/manager.py`、`plugin_manager/discovery.py`、`plugin_manager/base.py`、`plugin_manager/models.py`
- 插件注册 API：`plugin_manager/routes.py`，蓝图挂载于 `/admin/plugins/*`
- 插件注册表 DB：主库 `data/verorun.db` 的 `plugin_registry` 表（存 identifier/status/metadata 等）
- 生命周期状态：`installed → enabled → active`（见 `models.py` PluginStatus）
- 侧边栏菜单：`admin/templates/partials/icons.html`（GROUPS + 动态插件菜单）
- 插件内容加载：`admin/templates/partials/core.html` 的 `goPlugin()`
- Admin 启动引导：`admin/app.py`（`PluginManager(app)` + `mount_active_routes()`）

### 关键设计约定
1. **插件用命名空间导入**：`importlib.import_module(f'plugins.{identifier}')`，避免插件包名遮蔽项目根同名业务模块（如 `analytics`、`health_check`）。`plugins/__init__.py` 已建，使其成为包。
2. **路由必须在启动期挂载**：Flask `register_blueprint` 只能在首个请求前调用。`admin/app.py` 初始化后调用 `pm.mount_active_routes()` 统一挂载所有 enabled/active 插件的 Blueprint。运行时 activate() 挂载路由无效。
3. **插件 metadata 以磁盘 plugin.json 为权威**：`init_app` 启动时用磁盘 plugin.json 刷新内存缓存的 metadata（menu/version），不写 DB。改 plugin.json 后重启即生效。
4. **新旧生命周期钩子桥接**：`BasePlugin.setup()` 默认桥接旧钩子 `on_install()+on_enable()`；`deactivate()` 桥接 `on_disable()`；`BasePlugin.app` property 从 `manager.app` 取 Flask app。
5. **插件页面通过真实 iframe + URL token 加载**：`goPlugin()` 用 `iframe.src=embed_url?token=T`，插件页鉴权支持从 `?token=` 读取，页面内请求需带该 token。

## 三、本轮已修复问题（按时间顺序）

### 1. 侧边栏残留菜单 + 插件菜单未注入
- 移除 icons.html 中硬编码的 analytics/health/AI Tools 残留项
- 新增 `/admin/plugins/menus` 端点（`routes.py` `plugin_menus` + `manager.py` `get_plugin_menus`）
- icons.html `renderNav()` 动态拉取插件菜单渲染

### 2. New Plugins 列表包含已安装插件
- `plugins_admin.html` 用 `.filter(p=>!p.installed)` 过滤

### 3. `get_plugin_menus` 500（AttributeError: PluginInfo 无 instance）
- `manager.py` 改用 `getattr(pinfo, 'instance', None)`

### 4. 插件激活后页面 404（路由未挂载）
- 根因：插件停在 enabled 状态，路由只在 active 挂载，且启动从不激活
- 修复：新增 `manager.py::mount_active_routes()`，`admin/app.py` 启动时调用

### 5. analytics 路由挂载失败（No module named 'analytics.dashboard'）
- 根因：`plugins/analytics` 包名遮蔽项目根 `analytics` 业务模块
- 修复：`_load_instance` 改命名空间导入 `plugins.<id>` + 新建 `plugins/__init__.py`

### 6. 插件菜单新建重复组（如 analytics 另建 "Ops Data"）
- 修复：icons.html 新增 `GROUP_KEYS` 英文标识数组，插件 menu.group 匹配现有组则合并进其 body，否则才新建组

### 7. 插件 API 500（no such table，独立库未建表）
- 根因：`BasePlugin.setup()` 默认空实现，未调用插件的 `on_enable`（旧钩子），表从未建
- 修复：`base.py` setup 桥接 on_install+on_enable，deactivate 桥接 on_disable，新增 app property
- 结果：analytics 11 张表建于 `analytics/data/analytics.db`

### 8. AI Tools 菜单重复两级 → 移入 Content 组
- `plugins/ai_tools/plugin.json` menu.group 从 "AI Tools" 改为 "Content"
- 配合修复：`manager.py init_app` 启动时从磁盘 plugin.json 刷新 metadata（否则 DB 缓存旧 group 不更新）

### 9. ali_api（1688）500 的三个根因
- A. `admin.py:index` 用 `render_template`(str) 直接 `.set_cookie` → 改 `make_response()` 包装 + 导入 make_response
- B. `on_enable` 未建表 → 补 `from .models import init_tables; init_tables()`
- C. `models.py` 有**两个同名 `class AliApiItem`**（L54 与 L419），后者遮蔽前者导致 `create_table` 丢失 → 合并两类为一，删除重复定义
- 结果：ali_api.db 建成 7 张表（ali_api_items 等）

### 10. 1688 页面功能问题（本轮最后修复）
- 问题2（AI服务状态检测中）+ 问题3（顶部导航打不开）
- 根因：`goPlugin` 用 iframe srcdoc + XHR，导致外部脚本/JWT 鉴权失效
- 修复（用户选定"真实iframe+URL传token"）：
  - `core.html goPlugin` 改真实 `iframe.src=embedUrl?token=T`
  - `ali_api/routes/admin.py _require_admin` 支持 `request.args.get('token')`
  - `ali_api/static/ali_console.js` axios 拦截器从 URL 读 token 注入 `Authorization: Bearer`

## 四、待验证 / 待办

1. **浏览器实测（Ctrl+F5）**：1688 顶部导航是否可切换、AI 状态是否显示"可用/不可用"
2. **改动 goPlugin 影响所有插件**（现均走真实 iframe + URL token）：
   - analytics：`dashboard.py check_auth` 已支持 `?token=`，但页面 JS 是否带 token 请求需确认
   - ai_tools：embed 页面是 `routes.py` 内联 HTML，其 fetch 请求需确认带 token
   - 需逐个点开验证，受影响的插件按 ali_console.js 同款方式修复（axios/fetch 从 URL 读 token）
3. **风格统一（问题1，用户已同意暂缓）**：ali_api 的 `templates/ali_admin/index.html` 用 Bootstrap 浅色主题，与系统深色科技风不一致，需单独排期重写为深色主题
4. **health_check / captcha_embedded 仍是 installed 未启用**：需在插件管理页启用后才会挂载路由（现启用流程已能正确建表）
5. **清理临时脚本**：`scripts/_verify_deploy.py`（本地临时验证脚本）、服务器 `/tmp/_*.py`

## 五、部署与验证流程（重要）

### 部署（本地 → 服务器）
```powershell
$env:PYTHONIOENCODING="utf-8"; python scripts/deploy_sftp.py
```
- 基于 git diff 增量部署（依赖已 commit）；自动重启受影响服务
- 服务器输出中文乱码是 PowerShell 显示问题，不影响实际部署
- 涉及 admin/plugins/plugin_manager 改动会自动重启 admin 服务

### 服务器验证（用 paramiko，SSH 交互密码问题用脚本绕过）
- 密码：`***REMOVED***`
- 验证插件菜单：`curl -s http://localhost:8084/admin/plugins/menus`
- 验证插件路由状态：`curl -s -o /dev/null -w "%{http_code}" http://localhost:8084/admin/<plugin>/`（401=已挂载待鉴权，404=未挂载，200=可访问，500=有异常）
- 查错误日志：`admin/service.log`（grep Traceback / ERROR / 表名）
- 查插件状态：读 `data/verorun.db` 的 `plugin_registry` 表 identifier/status

### 各插件真实 DB 路径（独立库）
| 插件 | DB 路径 |
|------|---------|
| analytics | `analytics/data/analytics.db`（项目根业务模块目录，非 plugins/） |
| ai_tools | `plugins/ai_tools/data/ai_tools.db` |
| ali_api | `plugins/ali_api/ali_api.db` |
| health_check | `data/health.db`（待启用后确认） |

## 六、部署拓扑（域名→端口，以服务器 nginx 真实配置为准）

| 域名/路径 | 端口 | 服务 |
|-----------|------|------|
| easykai.cn `/` | :8081 | 主站后端 |
| easykai.cn `/admin/` | :8084 | 管理后台 |
| easykai.cn `/auth/` `/subscribe` | :8083 | 认证/订阅 |
| platform.easykai.cn | :8083 | Platform |
| agent.easykai.cn | :8084 | Admin |

## 七、本轮涉及的关键文件清单

- `admin/app.py` — 启动调用 mount_active_routes
- `admin/templates/partials/icons.html` — 菜单渲染 + GROUP_KEYS 合并
- `admin/templates/partials/core.html` — goPlugin 真实 iframe
- `admin/templates/partials/plugins_admin.html` — New Plugins 过滤
- `plugin_manager/manager.py` — mount_active_routes / get_plugin_menus / 命名空间导入 / metadata 刷新
- `plugin_manager/base.py` — setup/deactivate 桥接旧钩子 + app property
- `plugin_manager/routes.py` — /admin/plugins/menus 端点
- `plugins/__init__.py` — 新建（命名空间包）
- `plugins/analytics/plugin.json`、`plugins/health_check/plugin.json`、`plugins/ai_tools/plugin.json`（group=Content）、`plugins/ali_api/plugin.json` — menu 配置
- `plugins/ai_tools/routes.py` — embed 仪表盘
- `plugins/ali_api/__init__.py` — on_enable 建表
- `plugins/ali_api/routes/admin.py` — make_response + args token 鉴权
- `plugins/ali_api/static/ali_console.js` — axios 注入 URL token
- `plugins/ali_api/models.py` — 合并重复 AliApiItem 类

## 八、Git 提交记录（本轮）

- feat: plugin menu injection - remove residual menus, add dynamic plugin menu rendering, goPlugin iframe loading, plugins_admin filtering fix
- fix: get_plugin_menus - use getattr for pinfo.instance to avoid AttributeError
- fix: mount enabled plugin routes at startup to fix 404 on plugin pages
- fix: load plugins via plugins.<id> namespace to avoid shadowing root modules (analytics/health_check)
- fix: merge plugin menus into existing groups by English key instead of creating duplicate groups
- fix: bridge BasePlugin.setup/deactivate to legacy on_enable/on_install hooks + add app property
- fix: move AI Tools plugin menu into Content group to avoid duplicate nested menu
- fix: refresh plugin metadata (menu/version) from disk plugin.json on startup
- fix: ali_api - init DB tables on enable + wrap render_template with make_response for set_cookie
- fix: ali_api models - merge duplicate AliApiItem class that shadowed create_table
- fix: plugin pages load via real iframe with URL token; ali_api auth + axios read URL token
