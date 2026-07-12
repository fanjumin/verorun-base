# REGRESSIONS.md - 错误防回归记录（最高优先级，仅次于 AGENTS.md）

**本文件所有内容优先级极高**，Agent 必须在每次响应前内部检查是否违反本文件中的任何记录。

## 已记录的高频错误及永久防范（持续追加）

### 2026-06-24 系列
- **问题**：不先输出方案，直接修改代码/执行工具。
- **防范**：任何修改前必须先给完整方案 + 等待用户明确“同意/执行”等词。

- **问题**：忘记 Git 先提交就改动。
- **防范**：修改前必须检查并先 commit 未提交更改。

- **问题**：直接在服务器改文件。
- **防范**：默认只在本地改，通过 scp 同步。

（以后每次犯错，你就简单追加一条，我帮你写标准格式）

---

**Agent 执行指令**：每次思考/行动前，必须默念并检查："当前操作是否违反 REGRESSIONS.md 中的任何一条？"如果违反，必须先报告，不得执行。

---

## 2026-07-12 插件 i18n 翻译丢失事故 — 从全英文页面到"中英混杂"的完整根因

### 问题现象
- analytics 模板 tab 行从全英文（Trend / Page / Source / Geo / Devices / Event / Alerts）变成中英混杂（趋势 / Page / Source / 地区 / 设备 / Event / 告警）
- 用户反复质疑"为什么源码里是杂乱的？之前页面确实是全英文的"
- 其他插件（email、coupons、ads）存在同样问题：中文 key 硬编码、yml 不匹配、YAML 解析失败

### 根本原因 — 四环叠加事故链

#### 第一环（源头）：「AI 批量翻译」把中文 key 的译文写进 DB 而非 yml
- `i18n/translate.py` 批量调用通义千问，将中文 key 的英文译文写入了**数据库 `i18n_strings` 表**，而非插件的 `i18n/en.yml`
- 备份 DB `backups/data_20260708_143015/x7k2m9a4.db` 的 `i18n_strings` 表有 2678 条记录，其中 en 翻译 2658 条
- analytics 的 12 个中文 key（趋势、Page、Source、地区、设备、Event、告警等）在 DB 中全部有英文译文，命中率 **12/12**
- **后果**：用户看到的全英文页面是靠 DB 翻译撑起来的，而模板源码仍然是中文 key — 埋下隐患

#### 第二环（致命一击）：「插件化重构」从全局 yml 删 key 但没补进插件 yml
- 全局 `i18n/en.yml` 曾经包含 analytics 所有 key 的英文翻译（如 `趋势: Trend`）
- 提交 `dfb9f6d`（"remove plugin i18n keys from main i18n"）把这些 key 从全局 yml 删除
- 但 `plugins/analytics/i18n/en.yml` **从创建起就只配了 4 条路由 key**（Dashboard、Overview、Realtime、Historical），全部 85 个模板 key 没有任何 en 翻译
- **后果**：DB 成了 analytics 翻译的唯一残存副本，yml 权威源体系实际上不存在

#### 第三环（毁灭）：「删库重建」清除了唯一残存副本
- 提交 `ed9dd88`（"重建空白数据库"）删除了所有数据，包括 `i18n_strings` 表
- DB 中的 2658 条 en 翻译全部消失
- **后果**：`_('趋势')` 在 en 环境下查不到翻译 → 回退原文 `趋势` → 页面显示"趋势/Page/Source/地区/设备/Event/告警" = 用户看到的"中英混杂"

#### 第四环（蔓延）：「未统一 i18n 架构」导致其他插件同样有病
- 大部分插件模板用中文 key 硬编码（coupons: `智能优惠券`、email: `[收起]`、ads: 模板用英文 key 但 yml 用中文 key）
- 多个插件 yml 文件存在 YAML 语法错误：
  - `currency_converter/i18n/en.yml` L22: `Rates synced::` 含冒号未加引号
  - `order_notify/i18n/en.yml` + `zh-CN.yml`: key 含 `%s`/`%.2f` 未加引号
  - `reviews/i18n/en.yml`: key 含 `%d` 未加引号
- ads 的 yml 用中文 key（`广告管理: 广告管理`），模板用英文 key（`Ad Management`），两套完全不匹配
- coupons 的 `_ai_recommend.html` partial 被 `.gitignore` 的 `_*.html` 规则误伤，未纳入版本控制

### 证据链（可追溯、可复现）

1. **备份 DB `backups/data_20260708_143015/x7k2m9a4.db`**：
   ```sql
   -- i18n_strings 表有 2678 条，en 翻译 2658 条
   SELECT count(*) FROM i18n_strings WHERE locale='en';  -- 2658
   SELECT string_key, translation FROM i18n_strings WHERE locale='en' AND string_key IN ('趋势','地区','设备','告警','Page','Source','Event');
   -- 全部有翻译: 趋势→Trend, 地区→Geo, 设备→Devices, 告警→Alerts, Page→Page, Source→Source, Event→Event
   ```

2. **Git 提交记录**：
   - `dfb9f6d` - "remove plugin i18n keys from main i18n" — 从全局 yml 删 analytics key
   - `ed9dd88` - "重建空白数据库" — 清空 DB（含 i18n_strings）

3. **全局 `i18n/en.yml` 旧版本（在 dfb9f6d 之前）**：包含 `趋势: Trend` 等 analytics 翻译
4. **`plugins/analytics/i18n/en.yml` 所有版本**：从未包含超过 4 条 key

### 修复的三类问题及改动文件

#### 类型一：模板 key 从中文改为英文（源码级别）
| 插件 | 文件 | 改动要点 |
|------|------|---------|
| analytics | `plugins/analytics/templates/analytics.html` | 63 处中文 key → 英文（如 `_('趋势')`→`_('Trend')`） |
| email | `plugins/email/templates/admin_email.html` | 2 处中文 key → 英文（`[收起]`→`[Collapse]`、`[展开]`→`[Expand]`） |
| coupons | `plugins/coupons/templates/admin_coupons.html` | 72 个中文 key → 英文（94 处替换） |
| coupons | `plugins/coupons/templates/_ai_recommend.html` | 6 处中文 key → 英文（首次纳入 git） |

#### 类型二：yml 从零重建（对齐英文 key 架构）
| 文件 | 改动要点 |
|------|---------|
| `plugins/analytics/i18n/zh-CN.yml` | 89 条 `英文key: 中文`（覆盖全部模板 key） |
| `plugins/analytics/i18n/en.yml` | 8 条路由 key（模板英文 key 回退即英文） |
| `plugins/coupons/i18n/en.yml` | 118 条 `英文key: 英文`，从中文 key 模式重建 |
| `plugins/coupons/i18n/zh-CN.yml` | 118 条 `英文key: 中文` |
| `plugins/ads/i18n/en.yml` + `zh-CN.yml` | 76 条 `英文key: 英文/中文`，从中英错配重建 |
| `plugins/email/i18n/en.yml` + `zh-CN.yml` | 补充 `[Collapse]`/`[Expand]` 映射 |

#### 类型三：YAML 语法错误修复
| 文件 | 问题 | 修复 |
|------|------|------|
| `plugins/currency_converter/i18n/en.yml` | L22 `Rates synced::` 冒号未引号 | 双引号包裹全部 key/value |
| `plugins/order_notify/i18n/en.yml` | key 含 `%s`/`%.2f` 未引号 | 双引号包裹 |
| `plugins/order_notify/i18n/zh-CN.yml` | 同上 | 双引号包裹 |
| `plugins/reviews/i18n/en.yml` | key 含 `%d` 未引号 | 双引号包裹 |

#### 类型四：基础设施修复
| 文件 | 改动 |
|------|------|
| `.gitignore` | L20 下方增加 `!plugins/**/templates/_*.html`，放行插件 partial 模板 |

### 新架构原则（修复后确立）
1. **模板源码统一使用英文 key**，`_('English Key')`，不出现中文
2. **`zh-CN.yml` 是中文映射的权威源**：`English Key: 中文翻译`
3. **`en.yml` 留空或只配少数特殊 key**：英文 key 查不到翻译时回退即英文本身
4. **数据库 `i18n_strings` 仅作为运行时缓存**：可随时从 yml 重建（`seed_plugin_translations()`）
5. **DB 被删时 yml 不受影响**：下次启动自动 seed，翻译恢复

### 提交记录
```
617c695 - fix: analytics i18n - english keys, zh-CN.yml, en.yml
e19ddb6 - fix: plugin i18n issues - email, coupons, currency_converter, order_notify, reviews yml
7729846 - fix: ads yml key mismatch, restore _ai_recommend.html, gitignore exception
```

### 永久防范
1. **模板源码禁止出现 `_('中文...')`** — 所有 `_()` 参数必须是英文
2. **yml 是翻译权威源，DB 是缓存** — 确保删除 DB 后 yml 能完整恢复翻译，不依赖任何运行时状态
3. **新增插件 i18n 必须两步走**：① 模板用英文 key → ② zh-CN.yml 配齐映射（en.yml 留空即可）
4. **涉及"插件化拆分"时，必须确保**：从全局 yml 删除的 key 已写入对应插件的 yml，且覆盖全部模板 key
5. **.yml 文件必须通过 `yaml.safe_load()` 校验** — key 含 `:/%` 等特殊字符必须用双引号包裹
6. **`_(*.html` 类 gitignore 规则必须有例外**：`!plugins/**/templates/_*.html`
7. **删库/重建 DB 前检查 `i18n_strings`** — 如果 yml 未配齐，必须有警告机制阻止破坏唯一翻译副本
8. **每周/每次大版本前运行全量扫描**：`grep -rn "_('" plugins/*/templates/ | grep -P "_\('[^a-zA-Z]"` 检查是否混入中文 key

### 2026-06-24 JWT_SECRET 不一致导致登录循环
- **问题**：部署重构后的 `platform/app.py` 时，用临时密钥 `JWT_SECRET=dev_secret_key_2026` 重启了 platform 服务（8083），但 auth-center 服务（8081）的实际密钥来自 `/etc/environment.easykai`(`30e55814...`)。登录 API 走 8081 生成 token，OAuth 回调验证走 8083，密钥不同导致 token 验证失败，用户陷入登录循环。
- **永久防范**：
  - 重启 platform 等依赖 JWT 的服务时，**禁止使用测试/临时密钥**，必须从 `/etc/environment.easykai` 读取正式密钥。
  - 如不确定生产环境的密钥值，先通过 `cat /proc/<PID>/environ | tr '\0' '\n' | grep JWT_SECRET` 从正在运行的老进程环境变量中获取。
  - 以后重构涉及跨服务认证逻辑时，必须在方案中注明 "需验证两端的 JWT_SECRET 一致"。

## 2026-06-24 工作目录漂移问题
- **问题**：Agent 突然将代码操作到父目录 `/home/easykai/easykai-workspace/`，而不是正确目录 `/home/easykai/easykai-workspace/easykai.cn/`，并在两个目录间反复切换。
- **永久防范**：
  - 必须始终使用绝对路径 `/home/easykai/easykai-workspace/easykai.cn/` 作为项目根。
  - 每次响应中必须内部确认当前操作路径是否正确。
  - 任何文件创建/修改前，必须先说明将要使用的完整绝对路径。
  - 禁止使用相对路径或父目录路径。
  - 日你妈了个臭逼，你反复将金融主题覆盖网站建设主题，你妈了个逼 是怎么回事，找出原因，添加到下面？

## 2026-06-26 旧版反复覆盖服务器文件 — 完整根因及修复

### 问题现象
- 每次在服务器上部署新版（v0.9.3），马上被旧版（v0.8.6）覆盖
- tm.easykai.cn 和 community.easykai.cn 被反复恢复
- 首页从"网站建设"主题变回"金融版"

### 根本原因（按严重程度排序）

**根因 1：deploy 脚本使用 `pkill` + `nohup` 重启方式，与 systemd `Restart=always` 冲突**
- `deploy.py` 和 `deploy.bat` 的执行流程：上传文件 → `pkill -f 'app.py 8083'` → `nohup python3 -B app.py 8083 ...`
- systemd 的 `platform.service` 配置了 `Restart=always` + `RestartSec=5`
- `pkill` 杀死进程后，systemd 在 5 秒内自动重启了旧版的 `app.py 8083`
- 然后 `nohup` 新实例因为端口被 systemd 占用而启动失败
- **最终结果：systemd 管理的旧进程继续运行，deploy 的更新被静默吞掉**

**根因 2：本地文件不是最新版，deploy 脚本无脑覆盖**
- 本地 `f:\Sites\EasyKaiSite` 目录下的模板文件（如 `index.html`）版本落后于服务器
- Agent 运行本地 deploy 脚本时，使用 `pscp` 将本地旧文件上传到服务器
- 上传是无条件覆盖，没有任何版本比对或 MD5 校验
- **最终结果：服务器新版文件被本地旧版文件直接覆盖**

**根因 3：服务器上有 git 仓库（被 Agent 创建）**
- 服务器 `/home/easykai/easykai-workspace/easykai.cn/.git/` 目录存在（是 Agent 此前操作创建的）
- git 仓库在 `merge/prod-and-github` 分支，版本停留在 v0.8.6（6月19日）
- 仓库中包含 `server-backup-20260619` 备份分支
- 虽然 git hooks 未激活不会自动恢复，但仓库的存在混淆了开发者和 Agent
- **已处理**：2026-06-26 删除服务器 `.git/` 目录

**根因 4：服务器残留 15 个旧的 deploy 脚本**
- 服务器项目根目录下有 `deploy_all.py`、`deploy_v2.py`、`deploy_reverted.py`、`deploy_rollback_login.py` 等 15 个历史 deploy 脚本
- 这些脚本可能被误执行，造成不可预期的覆盖
- **已处理**：2026-06-26 全部删除

### 修复措施
1. **`deploy.py` 和 `deploy.bat`**：`pkill + nohup` 改为 `systemctl restart platform.service`
2. **服务器 `.git/` 目录**：已删除
3. **服务器旧 deploy 脚本**：15 个已全部删除
4. **服务器 nginx**：删除 `community.easykai.cn.conf`，清理 community/tm 注释，reload
5. **服务器 `community/` `trademind/` 目录**：已删除
6. **本地 `trademind/` 目录**：已删除并 git commit

### 永久防范
- **禁止使用 `pkill` + `nohup` 模式重启生产服务**，一律用 `systemctl restart <service>`
- **禁止在服务器上创建 git 仓库**，生产服务器不应有 `.git/` 目录
- **部署前必须检查本地文件版本**，确保本地文件不旧于服务器
- **删除服务器上的历史残留脚本文件**，只保留当前可用的 deploy 脚本
- **非用户明确要求，禁止运行 deploy 脚本**

---

## 2026-06-25/26 支付宝第三方登录修复记录
- **问题 1: `alipay.system.oauth.token` API 参数位置错误**
  - **表现**：支付宝返回 `"isv.grant-type-invalid"`（grant_type参数不正确）
  - **根因**：`grant_type` 和 `code` 被放在 `biz_content` 里发送，但此 API 不使用 `biz_content`，这两个参数必须是顶级参数
  - **教训**：不是所有支付宝 API 都使用 `biz_content`，必须查阅 API 文档确认参数层级

- **问题 2: 未读取支付宝 API 的 `error_response`**
  - **表现**：始终返回硬编码的 `'支付宝API错误'`，看不到真实错误信息
  - **根因**：`result.get('alipay_system_oauth_token_response', {})` 在错误响应时返回空字典，但代码未检查 `result['error_response']`
  - **教训**：支付宝 API 的 JSON 响应可能包含 `alipay_xxx_response`（成功）或 `error_response`（失败），必须同时处理两种情况

- **问题 3: 数据库表缺少 `alipay_user_id` 列**
  - **表现**：`sqlite3.OperationalError: no such column: alipay_user_id`
  - **根因**：OAuth 回调中 `SELECT * FROM users WHERE alipay_user_id=?`，但此列未添加到 `users` 表
  - **教训**：新增 OAuth 提供商时，必须同步添加对应的数据库字段，不能只改代码

- **问题 4: RSA2 签名密钥格式处理不鲁棒**
  - **表现**：数据库中的私钥可能不带 `-----BEGIN PRIVATE KEY-----` 头尾，签名失败
  - **根因**：不同来源（环境变量、数据库、文件）的密钥格式不一致
  - **教训**：密钥读取逻辑必须自动补全 PEM 头尾标记，不依赖外部输入格式

---

## 2026-06-26 easykai.cn 首页/登录页 302 循环（ERR_TOO_MANY_REDIRECTS）

### 问题现象
- 访问 `easykai.cn/` 或 `easykai.cn/login` 时浏览器报 `ERR_TOO_MANY_REDIRECTS`
- `platform.easykai.cn` 和 `agent.easykai.cn` 不受影响，正常显示

### 根本原因
- **`easykai.cn` 的 `is_platform_host=False`** — 不走 `handle_platform_auth`（管理后台认证），而是去数据库查 CMS `page_blocks('home')`
- **首页无 CMS 块** — 服务器数据库 `page_blocks` 表不存在/为空 → `if not blocks: return redirect('/login')`
- **登录页有 token 就回首页** — `/login` 读到 `sso_token` cookie 有效 → `redirect('/')` → 死循环

```
easykai.cn/ → page_blocks为空 → 302到/login
/login     → token有效 → 302回/
/          → 又空 → 302到/login → 死循环
```

### 修复措施
1. **`/` 路由**：`redirect('/login')` → `redirect('/login?redirect=/')`，显式声明目标
2. **`/login` 路由**：`target = request.args.get('redirect', '') or '/'; redirect(target)` → `target = request.args.get('redirect', ''); if target and target != '/': redirect(target)`，如果目标是 `/` 就不跳转，停在登录页

### 永久防范
- 任何涉及 **Cookie/Token 跨子域名验证 + 重定向路径**的修改，必须测试所有 Host 场景（主域名 vs 子域名）
- 登录页的 `redirect()` 必须有循环检测：`if target != self_referencing_path`
- `is_platform_host=False` 的场景（CMS 展示站）需要单独做重定向测试，不能只测管理后台
- 首页无内容时应显示 fallback 模板，不应 redirect 到可能产生循环的路径

---

## 2026-06-29 管理员后台套餐列表一直为空 — 前端响应结构不匹配

### 问题现象
- 用户在 `agent.easykai.cn` → 运营支撑 → 套餐管理，看到的是"暂无套餐"
- 用户反复反馈"管理员后台没有数据"
- 后端 API `GET /subscription/admin/plans` 返回 `200`，数据库 `subscription_plans` 表有 9 条数据

### 根本原因
- **API 返回结构**: `{success: true, data: {plans: [...]}}`
- **前端读取代码** (`admin.html:1718`): `plansData = d.data || []`
- `d.data` 的值是 `{plans: [...]}`（对象），不是数组
- `plansData.length` 为 `undefined`（falsy）→ 显示"暂无套餐"
- **第 10130 行也有同样问题**：`d.data.forEach()` 但 `d.data` 是对象没有 `.forEach()`，导致部署计划下拉也为空

### 为什么排查方向错了（更严重的教训）
- 用户多次反馈"管理员后台没有数据"时，Agent 一直在排查**后端**：检查数据库、API 路由、认证日志、文件是否部署
- 但实际上所有后端都是正常的（API 返回 200，DB 有数据），问题在前端 **1 行 JavaScript 代码**
- **当用户反馈"页面无数据"时，应该先从前端验证 API 响应**，而不是默认认为后端有问题

### 教训清单
1. **用户说"空"时，优先从前端排查** — F12 Network 看 API 实际返回了什么，而不是假设后端有问题
2. **前后端数据结构必须严格对齐** — 后端 `api_res({'plans': plans})` 产生 `data.plans`，前端就不能只读 `d.data`
3. **用户反复说有问题就一定有** — 不要在自己认为对的地方死磕，换个视角（前端 vs 后端）去查
4. **所有 API 调用的响应处理必须统一验证** — 检查项目中所有 `d.data` 的使用方式，确保和 API 返回结构一致

### 永久防范
- 修改涉及列表数据的 API 调用后，在浏览器 F12 验证实际响应结构和前端读取方式是否匹配
- 用户反馈"数据为空"时，第一件事：**打开浏览器开发者工具 → Network → 看 API 返回了什么**
- 同一个 API 若被多处调用，必须逐一检查所有调用点
- API 响应尽量扁平化，减少前端取数据的出错机会

---

## 2026-06-29 三连炸 — 订阅页全死 + platform/root 域名混淆

### 错误清单
1. **不该改 `app.py` 路由** — 加了 `/subscribe/success` 路由到 `pricing_page()`，导致 `platform.service` 重启后出现异常，`platform.easykai.cn` 和 `www.easykai.cn` 都显示营销页（控制台消失）。
2. **不该反复部署 `subscribe.html` 然后重启 `platform.service`** — `subscribe.html` 是纯静态模板，不需要重启就能生效，每次重启都让服务有几率翻车。
3. **对 `platform.easykai.cn` 和 `www.easykai.cn` 共用同一个 Flask 进程的架构缺乏敬畏** — 两个域名只靠 `request.host` 一行 `if` 区分，任何代码改动、部署、重启都可能破坏这个脆弱的区分逻辑。

### 死规矩（永远不得违反）

**Nginx 绝对不能碰。** 无论修改什么功能、什么页面，都不允许修改 `/etc/nginx/sites-enabled/easykai.conf`。Nginx 配置与代码修改无关。

**两个域名的区分只能通过代码逻辑修，不准改 Nginx。**
- `www.easykai.cn` = 营销官网（`public_home.html`）
- `platform.easykai.cn` = 已登录用户控制台（`index.html`）
- `agent.easykai.cn` = 管理后台（独立端口 8084）
- 这条区分逻辑在 `app.py` 的 `index()` 里，改这里，不改 Nginx

**静态模板更新不准重启服务。**
- `templates/*.html` 的改动只需要上传文件，Flask 的 `auto_reload` 或 `debug=True` 在新请求时会自动重新加载模板
- 除非改了 `app.py` 路由或 Python 逻辑，否则不允许 `systemctl restart platform.service`

**部署前必须自查三项：**
1. 是不是改了 `app.py`？ → 是的话检查 `/` 路由的 `is_root_domain` 分支
2. 是不是改了 Nginx 配置？ → **不允许改，report 给用户**
3. 是不是改了模板文件？ → 只上传，不重启服务

**Agent 执行指令**：每次思考/行动前，必须默念并检查："当前操作是否违反 REGRESSIONS.md 中的任何一条？"如果违反，必须先报告，不得执行。

---

## 2026-06-30 管理员后台"验证身份中..."卡死 — i18n `_()` 在 JS 中的两类致命错误

### 问题现象
- 访问 `agent.easykai.cn/admin` 后页面永远显示"验证身份中..."，没有任何变化
- 上午修过一次（68c202a），下午又复现
- 服务器端测试全部通过（curl 返回 200、模板渲染正确、API 正常），但浏览器端 JS 无法执行

### 根本原因：两类 `_()` 调用在 JS 上下文中产生语法错误

**类型 A：`_()` 在 JS 数组/表达式中缺少外层引号**

GROUPS 数组中的 `_()` 调用渲染后缺少引号包裹，导致 JS 语法错误：

```javascript
// 错误（模板源码）
[{{ _('消息与支持') }},true,[...]]
// 渲染后变成
[Messages & Support,true,[...]]   // ← Messages 不是合法的 JS 标识符

// 正确
["{{ _('消息与支持') }}",true,[...]]
// 渲染后
["Messages & Support",true,[...]] // ← 合法 JS 字符串
```

**类型 B：`_()` 参数中包含 `\n` 等 Python 转义序列，渲染为真实换行符破坏 JS 字符串**

`_()` 的参数是 Python 字符串，`\n` 被 Python 解释为真实换行符（0x0A）。Jinja2 渲染后，真实换行符直接出现在 JS 字符串字面量中，形成跨行字符串 → JS 语法错误。

```javascript
// 错误（模板源码）
var fileCtx="{{ _('\n\n[已上传文件]:\n') }}";
// _() 收到的是含真实换行的字符串，渲染后变成：
var fileCtx="

[已上传文件]:
";
// ↑ JS 字符串跨行，语法错误！

// 正确（把 \n 放在 _() 外面，让它们作为 JS 转义序列保留）
var fileCtx="\n\n{{ _('[已上传文件]') }}:\n";
// 渲染后 \n 保持为字面量 \n，JS 引擎正确解释为换行符
var fileCtx="\n\n[已上传文件]:\n";
```

### 具体受影响位置（共 3 处）

| # | 行号 | 错误代码 | 类型 | 修复 |
|---|------|---------|------|------|
| 1 | 222-225 | `[{{ _('消息与支持') }},true,[...]]` 等 4 行 | A | 加外层引号 `["{{ _('...') }}",...]` |
| 2 | 4698, 4895 | `_('\n\n[已上传文件]:\n')` | B | `"\n\n{{ _('[已上传文件]') }}:\n"` |
| 3 | 5379 | `_('🧠 测试结果\n━━━\n')` | B | `"{{ _('🧠 测试结果') }}" + "\n━━━\n"` |

### 为什么服务器端 curl 测试全部通过但浏览器仍然卡死
- curl 只验证 HTML 是否正确返回，不执行 JavaScript
- 模板渲染在服务器端是正常的（Jinja2 输出正确），但渲染结果中的 JS 语法错误只在浏览器端暴露
- **必须用 Node.js `node --check` 或浏览器 Console 验证 JS 语法，不能只依赖 curl**

### 永久防范

1. **任何 `_()` 调用出现在 `<script>` 标签内时，必须保证渲染后的 JS 语法合法**
   - `_()` 作为 JS 表达式（非字符串内）→ 必须加引号：`"{{ _('key') }}"`
   - `_()` 作为 JS 字符串内容 → 参数中禁止出现 `\n`、`\r`、`\t` 等 Python 转义序列，必须把转义序列移到 `_()` 外面

2. **`_()` 参数中禁止使用以下 Python 转义序列**（在 JS 上下文中）：
   - `\n` → 改为 `_()` 外面写 `\n`（JS 字面量）
   - `\r` → 同上
   - `\t` → 同上
   - `\'` → 用 `'` 或改用双引号包裹
   - 任何其他会被 Python 字符串解释的转义序列

3. **修改涉及 `_()` 的 JS 代码后，必须执行以下验证**：
   ```bash
   # 1. 获取渲染后的 HTML
   curl -s "https://agent.easykai.cn/admin?token=XXX" -o /tmp/admin.html
   # 2. 提取所有 <script> 内容并用 Node.js 检查语法
   python3 -c "
   import re
   html = open('/tmp/admin.html').read()
   for i, s in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)):
       open(f'/tmp/js_{i}.js','w').write(s)
   "
   for f in /tmp/js_*.js; do node --check "$f" || echo "FAIL: $f"; done
   ```

4. **排查"页面卡死"类问题时，优先检查浏览器 Console 的 JS 错误**，而不是只查后端 API 和 HTML 返回

5. **i18n 改造时，先在本地用 `node --check` 验证所有 `<script>` 标签内渲染后的 JS 合法性**，再部署到服务器

### 根本教训
- `_()` 是为 HTML 文本设计的国际化函数，**不是为 JS 代码设计的**
- 在 JS 上下文中使用 `_()` 时，必须从 JS 引擎的角度思考渲染结果，而不是从 Jinja2 模板的角度
- curl 能验证 HTML 结构，但**不能验证 JS 语法**

### 为什么修复了十几次才找到根因 — 调试方法论反思

**核心错误：全程用 curl 做验证，从未用 JS 引擎（Node.js / 浏览器 Console）检查语法。**

| 调试步骤 | 工具 | 结果 | 为什么是盲区 |
|---------|------|------|------------|
| 检查模板渲染 | curl + 看 size | 611KB，渲染正常 | curl 不执行 JS，JS 语法错误对它透明 |
| 检查 GROUPS 数组 | 肉眼对比 | 引号修好了 | 只修了类型 A，类型 B 不在这个位置 |
| 检查 `init()` 函数 | grep 看源码 | 逻辑正确 | 源码中 `\n` 看起来正常，不知道渲染后会变成真换行 |
| 扫描裸 `_()` 调用 | 正则匹配 | 找到的都是误报 | 正则 `_\(.*\\\\n` 匹配模板源码中的 `\n` 字面量失败 |
| 检查 API 响应 | curl API | 200 + JSON 正常 | 后端没问题，问题在前端 JS 解析阶段 |
| 检查 Nginx 配置 | grep | 无缓存 | 方向完全错误，问题不在网络层 |
| **最终** | **Node.js `node --check`** | **SCRIPT_4_ERROR line 4544** | **一击命中** |

**错误模式：**
1. **"后端思维"惯性** — 页面卡死，第一反应是查后端（API、路由、Nginx、服务状态），但 JS 语法错误是纯前端问题
2. **curl 作为唯一验证手段** — curl 只能证明"服务器返回了 HTML"，不能证明"浏览器能执行 JS"
3. **同症状就假设同病因** — 上午修了 GROUPS 引号，下午看到同样的"验证身份中..."就以为还是引号问题，实际是 `\n` 换行问题
4. **正则扫描的假阴性** — `_('\n\n[已上传文件]:\n')` 在模板源码中看起来正常，正则、肉眼都看不出问题，只有渲染后才知道

**永久防范（追加）：**
- **页面卡死/白屏类问题，第二轮排查就必须上 `node --check`**，不准超过两轮 curl-only 调试
- **同症状不等于同病因** — 每次复现都要从头排查，不能假设就是上次的 bug
- **curl 验证通过 ≠ 页面正常** — curl 只验证 HTTP 层，JS 层必须用 Node.js 或浏览器 Console 验证

---

## 2026-07-01 platform.easykai.cn 500 — index.html 同样存在 `\'` 转义问题

### 问题现象
- `platform.easykai.cn/` 已登录用户访问时报 Internal Server Error (500)
- 未登录用户跳转 `/login` 正常，问题只在渲染 `index.html` 时触发

### 根本原因
- `index.html` 第 371 行：`placeholder="{{ _(\'Set display name\') }}"`
- `{{ }}` 内 Jinja2 不认识 `\'` 转义 → `TemplateSyntaxError: unexpected char '\\'`
- 这跟 2026-06-30 修 `admin.html` 的 Type B 错误是同一类问题
- **为什么漏了**：6月30日只扫描修复了 `admin.html`，没检查 `index.html`

### 修复
- 第 371 行：`{{ _(\'Set display name\') }}` → `{{ _("Set display name") }}`
- 第 394 行：`{{ _(\'6-digit code\') }}` → `{{ _("6-digit code") }}`

### 永久防范（追加）
1. **修完 admin.html 中 `_()` 相关 JS 错误后，必须同步 grep 检查 `index.html`**（两个文件都大量使用 `_()` 内嵌 JS）
2. **全量扫描命令**：
   ```bash
   grep -rn "_(\'.*\\\\" platform/templates/ admin/templates/ auth-center/templates/
   ```
   找所有 `_('...\'...')` 模式，这是 Jinja2 模板中的非法语法
3. **每次部署前必须对改过的模板跑 `node --check` 验证**

---

## 2026-07-02 密码/SMS 登录后跳回 easykai.cn — 缺少跨子域 SSO Cookie

### 问题现象
- 用户使用「用户名+密码」登录成功，刷新后访问 `platform.easykai.cn` 立即跳回 `easykai.cn`
- 但用「抖音/第三方 OAuth」登录后可以正常访问 `platform.easykai.cn`
- 管理员后台 `agent.easykai.cn` 同样是 Loading...（但域名不同原因不同）

### 根本原因
- **密码登录** (`/user/password/login`) 和 **SMS 登录** (`/auth/sms/login`) 的 Flask 路由只返回 `jsonify({'success': True, 'data': {'token': '...'}})`，**没有设置 `sso_token` cookie**
- 前端 JS 把返回的 token 存到 `localStorage.setItem('sso_token', token)`，但 **`localStorage` 是按域名隔离的**
- 用户在 `easykai.cn` 域名下登录，token 存到了 `easykai.cn` 的 localStorage 中
- 访问 `platform.easykai.cn` 时，浏览器读不到 `easykai.cn` 的 localStorage，也读不到跨域 cookie（因为根本没设 cookie）
- `platform.app.py` 的 `index()` 路由发现没有 cookie → `redirect(f'{site_url}/login?redirect=...')` → 跳回 `easykai.cn`
- **OAuth 登录正常的原因**：OAuth callback 路由明确执行了 `resp.set_cookie('sso_token', jwt, domain='.' + main_domain, ...)`，设置了跨子域 cookie，所以 `platform.easykai.cn` 能读到

### 修复措施
修改了 **3 个文件**，确保所有登录方式都设置 `domain=.easykai.cn` 的跨子域 cookie：

| 文件 | 修改内容 |
|------|----------|
| `auth_server.py` (`/` 主页路由) | 处理 `?token=` URL 参数：验证 token 有效后设置 `sso_token` cookie 在 `.easykai.cn` 域，确保 OAuth 回调跳到首页时 cookie 写入 |
| `auth-center/routes/auth.py` (`sms_login()`) | 返回 JSON 前，用 `make_response()` 包裹，额外 `set_cookie('sso_token', token, domain='.' + main_domain, ...)` |
| `auth-center/routes/user.py` (`password_login()`) | 同上 |

### 永久防范
1. **任何登录/认证相关的后端 API，只要返回 token，都必须同时设置跨子域 cookie**，不能只返回 JSON body 让前端自己存 localStorage
2. **登录流程测试清单**（新增登录方式时必须验证）：
   - 密码登录 → 成功后带 cookie 直接访问子域名 → 不跳回
   - SMS 登录 → 同上
   - OAuth 登录 → 同上
   - 刷新页面 → token 仍然有效
3. **JSON-only token 返回是高风险模式**：前端 JS 存 localStorage 是按域名隔离的，多个子域名必须靠 `domain=.xxx.com` 的 cookie 共享
4. **排查"登录后跳回"问题时，第一件事**：用浏览器 DevTools → Application → Cookies 看 `sso_token` cookie 是否存在，domain 是什么，path 是什么

---

## 2026-07-11 admin 后台 partial 含 `<style>`/`<div>` 静态 HTML 混入主 `<script>` — 一个 bug 三种错法

### 问题现象（分三个阶段暴露）
- **阶段一**：`agent.easykai.cn/admin` 控制台报 `Uncaught SyntaxError: Unexpected token '<'`、`"'+(item.service_port||'')+'" cannot be parsed`、`'+esc(filePath)+'` / `'+u+'` 资源 404。媒体库、站点域名等模块的 JS 拼接串被当成 HTML 文本渲染。
- **阶段二**：修完阶段一后页面永远停在"验证身份中..."，无侧边栏。
- **阶段三**：修完阶段二后能登录，但每个模块右侧都常驻一份 Site Settings 界面，布局混乱。

### 根本原因（同一个结构性问题的三种表现）
`admin.html` 把 icons.html 到 tail.html 之间的**所有 partial 拼进同一个大 `<script>`**。而 `partials/site_settings.html` 是异类：它自带 `<style>` + `<div id="stApp">` 静态 HTML + 自己的 `<script>...</script>`。

- **阶段一根因**：site_settings 内部的 `</script>`（在主脚本区中间）把主 `<script>` 提前闭合，其后的 media_library/site_domains 等 partial 脱离脚本上下文，JS 源码被当 HTML 文本渲染 → 拼接串 `'+esc(...)+'` 直接进 DOM。
- **阶段二根因**：只删了 site_settings 的 `<script>/</script>` 标签，却把它的 `<style>`+`<div>` 裸留在主脚本 JS 流里。`<style>` 在 JS 上下文是非法 token → 整段主脚本语法错误 → `init()` 无法执行 → 卡"验证身份中"。
- **阶段三根因**：把整个 site_settings include 移到主 `</script>` 之后（tail 内），JS 语法虽合法，但它的静态 `<div id="stApp">` 被渲染在 `#mc` 主容器之外、常驻 `<body>` → 每个模块都能看到。

### 最终正确修复
让 site_settings **对齐框架的"单一 `#mc` + `window.l_xxx()` 动态渲染"模式**（其它所有 partial 都是纯裸 JS，靠 `l_xxx()` 往 `#mc` 注入 innerHTML）：
1. 删除静态 `<style>` → 改由 JS 一次性注入 `<head>`（用 `#stStyles` 去重）
2. 删除静态 `<div id="stApp">` → 改由 `l_site_settings()` 动态 `innerHTML` 注入 `#mc`
3. 删除自带 `<script>/</script>` → 变纯裸 JS 融入主脚本
4. tail.html / admin.html 的 include 位置回退到常规位置

### 为什么绕了三轮（教训）
- **同症状不同病因**：三个阶段现象各异，但都源于"static HTML 不该待在主 `<script>` 里/外"这一个结构问题。前两次都是"头痛医头"，没从框架契约层面根治。
- **服务重启方式错误一度掩盖修复效果**：8084 是 gunicorn（systemd `admin.service`，2 worker），最初用 `pkill + nohup python3 app.py` 重启**完全无效**，旧 worker 一直缓存旧模板，误以为"文件改了没用"。正确方式：对 gunicorn master `kill -HUP` 热重载（无需 sudo、不中断服务），或 `systemctl restart admin.service`。这与 2026-06-26 记录的"禁止 pkill+nohup"一致。
- **curl 验证不了 JS**：全靠 `node --check` 抓渲染后每个 `<script>` 的语法，一击命中 `<style>` 那行（呼应 2026-06-30 教训）。

### 永久防范
1. **admin.html/其它聚合页里被 include 进大 `<script>` 的 partial，必须是纯裸 JS**，绝对不能含 `<style>`、`<div>`、`</script>` 等 HTML 标签。
2. **新增 admin 模块 partial 必须遵循框架契约**：只写 `window.l_<key>=function(){...}`，界面用 JS 往 `#mc` 注入 innerHTML，样式用 JS 注入 `<head>` 或写进全局 head.html，不得在 partial 里放静态 HTML/style。
3. **改完 admin 模板后，必须用 `node --check` 校验渲染后每个 `<script>`**，并 `grep -c 'id="xxx"'` 确认没有意外常驻的静态 DOM 节点。
4. **重启 8084(admin)/8083(platform) 一律用 `systemctl restart` 或对 gunicorn master `kill -HUP`**，禁止 `pkill + nohup python3 app.py`。