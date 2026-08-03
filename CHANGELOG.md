# 修改记录

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
- 服务器: 47.103.204.180
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
