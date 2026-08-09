# 修改记录

## v0.55.2 — 2026-08-09

### Changes

- feat(deploy): 四脚本一键部署装完即用 — install 模式默认批准迁移与播种，无 TTY 凭据自动降级，print_summary 输出管理员登录信息

## v0.55.1 — 2026-08-09

### Changes

- fix(deploy): 部署脚本 v3 审计整改（--region 缺值报错、--skip-deps 生效、DEBUG 强制禁用、do_rollback 统一 before_commit）
- refactor(deploy): 抽取公共函数到 deploy/lib/common.sh（install.sh / install-local.sh / install-dev.sh / install-code.sh 共用）
- docs(deploy): 弃用 curl|bash 管道安装，统一 git clone 本地执行

## v0.55.0 — 2026-08-09

### Changes

- feat(admin): goPlugin() 双通道兼容，优先内联 l_<key>() 降级 iframe
- feat(admin): 解耦 l_site_builder()，修复侧边栏 site_builder 死链接
- feat(currency_converter): iframe → 内联 partial l_currency_converter()
- feat(subscription): iframe → 内联 partial l_subscription_admin()
- feat(vault): iframe → 内联 partial l_vault() 仪表盘
- feat(ali_api): iframe → 入口面板 + window.open() 独立窗口
- chore(plugins): 移除 6 个 plugin.json embed_url，移除 site_builder/mini_app 的 admin_url
- chore(discovery): admin_url 字段 deprecated 警告

## v0.54.0 — 2026-08-08

### Changes

- feat: site_builder 插件化发布（v2.1.0）— 独立数据库 site_builder + 内部 API + 菜单自动注册；legacy site_builder 从 sparse-checkout 移除
- feat(deploy): install-code.sh 本地源码全量部署脚本（无 git clone、无域名）；install-local.sh / install-code.sh 从 verorun-base 同步中排除
- feat(deploy): PLUGIN_AUTO_INSTALL 开关 — 部署默认不自动安装/启用插件，后台手动启用
- fix(deploy): admin 启动超时 — health_check.sh 增加 curl 超时 + gunicorn timeout 提升至 300s
- fix(db): 启动迁移串行化 + connect_timeout，解决低配机器启动挂起
- chore(deploy): 本地 LAN 部署启用 debug 模式

## v0.53.0 — 2026-08-07

### Changes

- feat(plugins): mini_app_builder v2.1.0 — 数据解耦至独立库 mini_app + 联邦身份
- feat(deploy): 本地无域名部署支持 — SSO cookie secure 跟随 DEPLOY_PROTOCOL + 子域转路径映射 + install-local.sh
- fix(plugins): 修复启动期数据库初始化错误 — analytics SQL 切分 + order_notify/wishlist 裸连接 + health_check/vault cursor 链式调用
- fix(plugins): mini_app_builder 审计修复 — oauth_config 依赖声明 + 会话仅写独立库

## v0.52.0 — 2026-08-07

### Changes

- feat(plugins): mini_app_builder v2.0.0 — 解耦小程序生成 + 合并 Developer Accounts 插件
- fix(agent_matrix): is_active 用 bool 适配 PostgreSQL boolean 列（create/update prompt）
- fix(plugins): mini_app_builder 审计修复 — plugin.json 规范化 + 弃用自动禁用 + 公开 API

## v0.51.0 — 2026-08-07

### Changes

- feat(agent_matrix): Dynamic Prompt System — PromptResolver 动态提示词解析引擎（数据库驱动、标签匹配、四层组装、降级回退）
- feat(plugins): 标准审计修复与发布 — 5 插件启用加固 + name/menu i18n 机制
- feat(plugins/vault): v2.2.0 安全复审计修复收尾 + 版本升级
- chore: 移除含凭据的临时测试脚本

## v0.50.1 — 2026-08-07

### Changes

- fix(plugins/store): 无截图/无图标插件自动渲染确定性色块占位（identifier hash → 12 色调色板），替代灰块/空白

## v0.50.0 — 2026-08-07

### Changes

- Version bump from v0.49.0
- feat(plugins): 前端框架插件便利层 — React 18 / Vue 3.4 本地 UMD 库（禁外网 CDN）+ 官方 react_plugin / vue_plugin 可复制模板（iframe + SSO token + window.__t i18n + design-system）
- feat(plugins): 插件标准 v1.4 → v1.5 — 新增 §15 前端框架插件指南、§16 插件审核规范（AI 辅助 + 人工审批，提示词规则待后续批次）；§12.11 iframe 例外条款；§9.2 框架插件目录约定；§11.3 前端安全交叉引用
- feat(admin): Vue 3.4.38 UMD 本地化（admin/static/lib/plugin-frameworks/，SHA256 锁定）

## v0.49.0 — 2026-08-05

### Changes

- Version bump from v0.48.0
- feat(plugins): 插件商店 UX 改造 — 卡片缩略图 + 移除直接安装按钮 + 详情弹窗 README + 安装按钮 + 标准文档 v1.4
- feat(plugins): 自研插件上传功能 — upload API + 前端上传按钮 + Custom 徽标 + source 字段 + License 豁免
- fix(plugins): 修复 store_admin_save 与 _upsert_cache SQL 参数计数缺陷
- fix(plugins): store_admin_save enabled 参数化 + 增加 min_app_version/depends_on 字段支持
- chore(plugins): 上传端点增加文件大小限制、rate limiting、magic bytes 校验、min_app_version 兼容检查
- docs(plugins): plugin-standard v1.3 → v1.4 — 新增 §14 商店展示规范 + 展示字段规范

## v0.48.0 — 2026-08-05

### Changes

- Version bump from v0.47.2
- feat(analytics): 世界地图点击缩放（GeoJSON 国家质心计算 + 返回按钮），移除 World/China 切换统一世界地图，/static/ 免登录（world.json 可在 iframe 加载），版本升级 1.3.0
- feat(vault): 升级 2.1.1 — seed 默认 administrator、插件标准引用 v1.3
- feat(plugins): 商店版本发现 — check_updates 对比逻辑 + has_update 徽标
- docs: 双仓库（verorun-code 私有 / verorun-base 公开）双分发模式文档化 — README、deploy/README、GUIDE 统一仓库路径、安装方式与版本号；供应商数量更新为 9（新增 KIMI）
- chore: 删除失效的 scripts/dev_start.py（引用不存在的 site/platform/captcha-service 入口）

## v0.47.2 — 2026-08-05

### Changes

- fix(analytics): GeoLite2 绝对数据路径修复 + CDN 下载后 init_geoip
- feat(analytics): GeoLite2 CDN 镜像下载（jsDelivr，免费免 MaxMind 账号）+ 新 API URL + Basic Auth + 手动 .mmdb 上传；地图标题精简；版本升级 1.4.0；iframe 内复用 admin toast
- fix(vault): 插件表隔离到独立 vault schema（插件标准 v1.2）、幂等迁移、全宽 dashboard、restore/drill 长超时 Nginx location
- feat(admin): Dashboard 收入数据合并（subscription/order 表）+ Revenue Trend 卡片可点击
- fix: agent_token_daily ON CONFLICT upsert 列名歧义修复
- refactor: design-system.css 拆分为插件专用 variables + 主站 landing.css，消除 10 处 CSS 类冲突；.glass-card::before pointer-events 修复
- ci: verorun-base 同步时更新源指向自身仓库

## v0.47.0 — 2026-08-05

### Changes

- feat(vault): 备份插件 2.1 — S3/OSS/Azure Blob/GCS/WebDAV 存储适配器、Schedule/Storage CRUD API、恢复执行 + PITR 演练、ECharts 趋势、智能告警、带宽限制/重试/轮转/分层存储、跨环境恢复、合规报告、HMAC 签名、5 个专属页面模板
- feat: Shop 商城模块从核心解耦为独立插件
- feat(admin): Dashboard 重构 — 3 层响应式栅格（KPI/运营/参考）、大屏模式、DashboardService 组件级缓存、一键导航、骨架屏、widget 独立刷新；修复订阅 No Data、token spend 查询、插件优雅降级
- fix(admin): 插件菜单点击无响应（3 个根因）；插件 iframe 通过 query param 传递 JWT token
- feat(i18n): 80+ 硬编码中文字符串包装进 16 个插件
- fix(deploy): admin/main_site 入口 load_dotenv()；健康检查超时 180s + systemd TimeoutStartSec=300
- fix(analytics): 下载进度条、China/World 地图切换、toast 可见性、代码审查修复（P0-P3）、401 下载修复
- refactor: 7 个插件内联 CSS :root 统一到 design-system.css（含兼容别名）；新增插件中英文 README
- chore(ali_api): 升级 2.0.1，移除旧 zh-CN README

## v0.46.2 — 2026-08-04

### Changes

- feat(vault): 备份插件 2.0.0 — 数据备份/上传/恢复引擎
- feat(health): 1.4.0 — 新增 3 个检查器（veroguard / ai_gateway / plugin_store），移除 8090 引用
- feat: .gitattributes 控制 verorun-base 导出范围（双仓库分发）
- feat(deploy): install.sh SSH key 认证 + verorun-code 部署指南
- feat(plugins): 插件发布管道 + 商店目录（GitHub Raw）
- fix(analytics): Settings 保存、IP 市场检测、下载修复、自定义弹窗

## v0.46.1 — 2026-08-03

### Changes

- fix(ci): release 上传 contents:write 权限、patchelf 安装、Nuitka 直接调用、完整性 manifest 生成、cryptography 依赖

## v0.46.0 — 2026-08-03

### Changes

- feat: CI 工作流（build-binaries / bump-version / sync-to-base）+ verorun-base 初始化文件 + VeroRun Base EULA v1.0
- feat(analytics): 1.2.0 — GeoIP 自动下载、双 GeoIP 配置指南（ip2region 免费 + MaxMind Basic Auth）、市场检测重构、动态地图标题
- fix(install.sh): pip 超时 120s / PyPI 镜像、printf 替换 heredoc（CRLF 管道兼容）、服务就绪轮询 60s

## v0.45.1 — 2026-08-02

### Changes

- fix(admin): 更新状态文件移到 /run/verorun/（systemd RuntimeDirectory）— 修复 Update Now 按钮 root 权限 500 错误

## v0.45.0 — 2026-08-02

### Changes

- feat: 双区域 API 路由（cn/global）+ 插件商店下载管道

## v0.44.3 — 2026-08-02

### Changes

- fix(admin): 插件与 i18n 菜单默认折叠；health __main__ 语法错误修复

## v0.44.2 — 2026-08-02

### Changes

- fix(admin): check-update 对比 commit hash 而非仅 tag
- fix(install.sh): 从脚本位置自动检测 APP_HOME
- fix: seed_default_agents 处理 UNIQUE(name, role_type) 冲突

## v0.44.0 — 2026-08-02

### Changes

- feat: 邮件注册为默认注册方式 — /auth/email/register、login-methods 邮件注册方法、register.html 动态 Email/Phone 切换
- feat(i18n): 登录/注册翻译补齐 + 移除硬编码 ICP
- fix: 根目录 login.js 与 main_site 同步（登录页崩溃根因）、/register 路由

## v0.43.6 — 2026-08-02

### Changes

- fix(install.sh): sudo exec 恢复 APP_USER/APP_HOME/VENV_DIR 环境变量（自更新后路径错误）
- fix: do_update 自动恢复本地修改的已跟踪文件；health_check.sh 可执行权限

## v0.43.5 — 2026-08-02

### Changes

- feat: 统一插件商店目录 — 异步商店同步、Installed/Store 双视图、下载+安装流程、i18n

## v0.43.4 — 2026-08-02

### Changes

- fix: 在线更新子进程分离 + install.sh 写最终状态（存活 admin 重启）

## v0.43.3 — 2026-08-02

### Changes

- fix: 登录页静态资源版本号 cache-busting；health_service 恢复纳入 + root 路由；install.sh sudo env

## v0.43.2 — 2026-08-02

### Changes

- fix: 健康检查提取为独立脚本 deploy/health_check.sh（修复 systemd ExecStartPost 引号错误）
- refactor: Agent 角色更名 shop→business、steward→finance

## v0.43.1 — 2026-08-02

### Changes

- fix: 在线更新输出流式写入日志 + 实时状态 — /admin/api/update-status 轮询、5s 进度刷新
- fix(install.sh): git fetch 失败显式退出

## v0.43.0 — 2026-08-02

### Changes

- feat: 动态插件化登录/注册 UI — GET /auth/login-methods，SMS/OAuth 插件动态注册登录方式，登录页完全动态渲染，全部 i18n 化

## v0.42.2 — 2026-08-01

### Changes

- fix: 各插件 PostgreSQL 占位符 ? → %s（ali_api 9 处、social_push 2 处、revenue strftime→to_char）；i18n advisory lock 使用确定性 md5
- feat: 新增 KIMI + 智谱（Zhipu）供应商；移除 Azure TTS（仅保留 Edge-TTS）；供应商下拉动态加载 + 15 个新模型 + agent matrix 种子配置
- fix: pin pydantic<3 解决 openai>=2.52 依赖冲突；install.sh 自动检测 GitHub 连通性 + ghproxy 回退

## v0.42.1 — 2026-08-01

### Changes

- feat: VeroGuard Phase 1-5 完成 — 完整性校验（SHA256 manifest）、设备指纹、运行时探测、加密心跳（AES/HMAC/TLS）、远程命令（6 种）、self_protect 双进程、Nuitka 编译 + install.sh 集成 + DB 迁移
- fix: 重启死锁 5 层防御（advisory lock + post_fork + graceful shutdown + health check + pre-flight）
- fix: Vault 插件 Blueprint url_prefix 与 embed_url 不匹配

## v0.42.0 — 2026-08-01

### Changes

- feat: VeroGuard 统一守护进程 Phase 1 骨架 + PROBE_SECRET
- fix: Admin 504 — i18n 死锁 + HealthCheck SQL 占位符；install.sh 自更新保留 APP_HOME

## v0.41.0 — 2026-08-01

### Changes

- feat: .cache/ 运行时缓存 — LLM 响应缓存 + 会话摘要缓存，自动 TTL 和容量限制
- refactor: APP_HOME 默认值从 verorun-workspace 简化为 verorun

## v0.40.0 — 2026-08-01

### Changes

- Version bump from v0.39.4

## v0.39.4 — 2026-07-31

### One-click update testing release

- Fix checkUpdate() JS TypeError on deleted currentVer element (showed "Failed")
- Fix .git permission issues on server (sudo git pull)

## v0.39.3 — 2026-07-31

### Optimize install.sh update — skip pip install when requirements.txt unchanged

- Add md5 hash cache for requirements.txt in deploy/install.sh
- Only run pip install when requirements.txt has changed since last run

## v0.39.2 — 2026-07-31

### Agent Discussion — Revised Design v2.0 + Version bump

- Bump system version to 0.39.2 (consistent across VERSION, package.json, README.md, admin/app.py)
- Fix admin/app.py stale version string (was v0.32.2)
- Agent Discussion v2.0 design document: 5 critical fixes + 6 supplementary improvements + 7-phase roadmap

## v0.8.6 — 2026-06-20

### Agent Matrix P0 修复 + 新增供应链/商城Agent

- P0: dispatch_sub_tasks() 改为 ThreadPoolExecutor 并行执行 + 300s 超时熔断
- 新增 Supply Chain Agent（1688 商品采集、AI 标题优化、商城发布）
- 注册关键词模板和 chat/tool 意图路由
- 提取 _execute_standard_agent() / _execute_image_agent() 独立方法

## v0.8.5 — 2026-06-15

### 品牌变更：睿策AI → 易站AI

- 系统名称从"睿策AI"变更为"易站AI"
- 后台标题更新为"易站AI"
- 所有"睿策"字样替换为"易站"
- OAuth 配置管理支持多平台（抖音、微信、支付宝）
- Client Secret 隐藏显示（*** + 后4位）
- 微信服务支持多租户配置
- 新增支付宝 OAuth 服务

## v0.8.4 — 2026-06-15

### 修复：登录系统全面修复（用户名密码/手机验证码/抖音扫码）

#### 问题描述
- 所有登录方式登录后，导航栏"注册|登录"变为"控制台"但实际未真正登录
- 刷新页面后登录状态丢失
- platform.easykai.cn 控制台页面无法识别已登录用户
- 不同账号可能相互干扰

#### 根因

1. **platform/services/jwt_service.py 文件损坏**
   - `def create_token()` 函数定义缺失
   - 导致 platform 服务无法生成/验证 token

2. **CMS 首页与 platform 控制台的 cookie 验证逻辑不一致**
   - platform.easykai.cn/ 缺少 cookie → 登录态的完整回写
   - easykai.cn/ 主站 CMS 页面未正确传递 `is_logged_in` 状态

3. **trademind (8081) API 服务的 cookie 验证逻辑失效**
   - 仅支持 `Authorization: Bearer <token>` header
   - 浏览器 cookie 方式请求 API 时被拒绝

4. **Cookie Domain 配置与登录回调**
   - `/?token=xxx` 登录回调后重定向至 `/`，cookie Domain 设置为 `easykai.cn`（支持子域共享）
   - platform.easykai.cn/ 页面正确读取 `sso_token` cookie 并验证

#### 修复内容

| 文件 | 修改 |
|------|------|
| platform/services/jwt_service.py | 从 auth-center 复制完整版本，确保 `create_token/validate_token` 齐全 |
| auth-center/routes/user.py | `_get_token_from_request()` 支持 cookie：同时支持 Authorization header 和 `sso_token` cookie |
| platform/app.py | `/` 路由增加 cookie 验证；`/?token=xxx` 回调设置 Domain=easykai.cn HttpOnly cookie |
| auth-center/routes/auth.py | `/auth/sms/login` 新用户自动创建账号，phone_verified=1，开通 free tier |

#### 验证结果
- ✓ 用户名密码登录正常
- ✓ 手机验证码登录正常（新用户自动注册）
- ✓ 抖音扫码登录正常
- ✓ 登录后 easykai.cn/ 显示"控制台"
- ✓ platform.easykai.cn/ Dashboard 正常加载用户数据
- ✓ trademind (8081) API 通过 cookie 验证正常
- ✓ 不同账号登录显示不同用户信息，无串号问题

#### 部署
- 服务器: ***REMOVED***
- 重启服务: platform (8083) + trademind (8081)
- Nginx 无需变更，已有 Domain=easykai.cn 的 cookie 转发

---

## v0.8.3 — 2026-05-xx

### 新增：实名认证功能
- 用户可提交实名认证信息
- 管理后台审核流程

---

## v0.8.2 — 2026-05-19

### 修复：密码登录报 Internal Server Error

#### 根因
5月19日部署实名认证功能时，将本地 user.py（含5月13日新增的 `last_active` session 写入逻辑）一起部署。该逻辑引用了 `user_sessions` 表中不存在的 `last_active` 列，导致密码登录成功后 session 写入抛异常 → 500。

#### 修复
1. `user_sessions` 表加 `last_active TEXT DEFAULT ''` 列
2. `database.py` CREATE TABLE 同步更新
3. `regions` 表缺失修复：导入 regions_seed.sql (3760 条省市区)

### 修复：用户控制台刷新就退出登录

#### 根因
`platform/templates/index.html` 中 URL token 写入时缺少 `document.cookie` 写入。
服务器 `app.py` 刷新时检查 `sso_token` cookie 判断登录态，找不到就重定向 `/login`。

#### 修复
index.html 补回 `document.cookie` 写入逻辑

---

## 2026-08-06 — 修复：管理员后台卡死 "Verifying Identity..."

### 问题描述
管理员后台无法进入，页面只显示 "Verifying Identity..."，控制台报：
`admin:13553 Uncaught SyntaxError: Unexpected identifier 'width'`

### 根因（两个问题叠加）

1. **plugins_store.html 第 45 行转义引号错误（v0.49.0 回归）**
   - `admin/templates/partials/plugins_store.html` 第 45 行（v0.49.0 插件商店 UX 改造新增的卡片缩略图 `onerror` 代码）中，JS 单引号字符串内出现 `\\'`：
     - JS 中 `\\` 被解释为字面量反斜杠，紧随的 `'` 直接终止字符串
     - 后面的 `width:100%...` 变成裸标识符 → `SyntaxError: Unexpected identifier 'width'`
   - 该错误位于 admin 主 `<script>` 块内，导致整个 admin JS 崩溃，页面永远停在 "Verifying Identity..."
   - 注：此问题曾在历史提交 `c389b61` 修复过（9 处 `\\'`），本次为 v0.49.0 UX 改造重新引入

2. **admin_coupons.html 违规包含 `<script>` 标签**
   - `plugins/coupons/templates/admin_coupons.html` 第 2/217 行含 `<script>`/`</script>`，违反 `docs/plugin-standard-v1.3.md` §12.11「前端模板铁律：禁止 `<script>` 标签」
   - admin 所有 partial/插件模板是裸 JS，由 core.html 开外层大 `<script>`、tail.html 统一闭合；插件模板自带 `<script>` 会提前截断外层 script，导致后续所有 partial 的 JS 变成裸 HTML（`Unexpected token '<'` / `xxx is not defined`）

### 修复内容

| 文件 | 修改 |
|------|------|
| `admin/templates/partials/plugins_store.html` | 第 45 行 `\\'` → HTML 实体 `&quot;`（style 属性双引号改用实体，避免字符串提前截断） |
| `plugins/coupons/templates/admin_coupons.html` | 删除第 2 行 `<script>` 与第 217 行 `</script>`，回归裸 JS 铁律 |

### 验证结果
- 本地真实 Jinja2 渲染 admin.html（15053 行），主 script 块（约 1.48 万行 JS）通过 `node --check` **零语法错误**
- `<script>` 标签仅剩 head checkUpdate 块与主块两对，coupon 违规标签已消除

### 部署提示
- 服务器生效需重启 admin 服务(8084)：`admin/app.py` 设置了 `TEMPLATES_AUTO_RELOAD=False` + jinja2 字节码缓存，模板修改后不会自动热加载
