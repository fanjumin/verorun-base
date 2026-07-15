# VeroRun 技术迁移实施计划

> 版本：v0.1 | 日期：2026-07-15 | 状态：执行手册

---

## 一、总体路线图

```
Phase 0：准备阶段（1 周）
  ├── 环境准备、代码基线、全项目 SQL 审计
  └── 输出：SQL 语法不兼容清单 + 迁移脚本验证通过

Phase 1：SQLite → PostgreSQL（4-6 周）
  ├── 1A - 核心层重写（database.py → cms.py → user.py → site.py）
  ├── 1B - 服务层适配（4 个服务入口）
  ├── 1C - 插件数据库迁移（5 个插件）
  ├── 1D - 数据迁移 + 全功能回归测试
  └── 验收：所有服务正常启动，数据完整

Phase 2：Admin 后台 Vue 3（12 周）
  ├── 2A - 项目搭建 + 布局 + API 层
  ├── 2B - 核心页面（Dashboard / Users / Products / Orders）
  ├── 2C - 内容管理（CMS / Posts / Comments / Media）
  ├── 2D - 运营管理（Subscriptions / Plans / Plugins / Themes）
  ├── 2E - 高级功能（Analytics / Health / Matrix / Automation）
  ├── 2F - 收尾（暗色模式 / 响应式 / i18n / 构建优化）
  └── 验收：47 个页面可访问，与 Jinja2 版本并行运行 1 周无差异
```

| 阶段 | 时间段 | 人天 | 里程碑 |
|------|--------|------|--------|
| Phase 0 | Week 0 | 5-7 | SQL 审计清单完成 |
| Phase 1 | Week 1-6 | 29-44 | PG 全量切换 |
| Phase 2 | Week 7-18 | 35-45 | Admin SPA 上线 |
| **合计** | Week 0-18 | **69-96** | |

---

## 二、Phase 0：准备阶段（Week 0）

### 2.1 Day 1：环境搭建

```bash
# 本地安装 PostgreSQL（开发用）
sudo apt install -y postgresql-16 postgresql-contrib

# 创建开发数据库
sudo -u postgres psql <<EOF
CREATE USER easykai_dev WITH PASSWORD 'dev_password';
CREATE DATABASE easykai_dev OWNER easykai_dev;
ALTER USER easykai_dev CREATEDB;
EOF

# 安装依赖
pip install psycopg2-binary==2.9.9

# 验证
python -c "import psycopg2; print('psycopg2 OK')"
```

### 2.2 Day 2-3：全项目 SQL 审计

```bash
# 搜索所有潜在的不兼容 SQL 模式
cd f:/Sites/VeroRun

# 1. PRAGMA 使用（需全部删除）
grep -rn "PRAGMA" --include="*.py" auth-center/ admin/ platform/ plugins/

# 2. ATTACH DATABASE（需替换为 search_path）
grep -rn "ATTACH" --include="*.py" auth-center/ admin/ platform/ plugins/

# 3. datetime('now' 模式（需替换为 NOW()）
grep -rn "datetime('now" --include="*.py" auth-center/ admin/ platform/ plugins/

# 4. AUTOINCREMENT（需替换为 IDENTITY）
grep -rn "AUTOINCREMENT" --include="*.py" auth-center/ admin/ platform/ plugins/

# 5. REPLACE INTO（需替换为 INSERT ON CONFLICT）
grep -rn "REPLACE INTO" --include="*.py" auth-center/ admin/ platform/ plugins/

# 6. IFNULL（需替换为 COALESCE）
grep -rn "IFNULL(" --include="*.py" auth-center/ admin/ platform/ plugins/

# 7. last_insert_rowid（需替换为 RETURNING id）
grep -rn "last_insert_rowid" --include="*.py" auth-center/ admin/ platform/ plugins/

# 8. json_extract（需替换为 ->> 操作符）
grep -rn "json_extract" --include="*.py" auth-center/ admin/ platform/ plugins/

# 9. strftime（需替换为 TO_CHAR）
grep -rn "strftime" --include="*.py" auth-center/ admin/ platform/ plugins/
```

**输出：将搜索结果汇总为 `docs/sql-audit-checklist.md`，确认所有需修改的文件和行号。**

### 2.3 Day 4-5：代码基线

```bash
# 确保所有改动已提交
git add -A
git commit -m "chore: 迁移前基线提交 - SQLite + Jinja2 全功能版本"

# 创建迁移分支
git checkout -b migration/pg-vue

# 全量备份 SQLite 数据
cp data/x7k2m9a4.db backups/x7k2m9a4_pre_migration_$(date +%Y%m%d).db
cp data/shop.db backups/shop_pre_migration_$(date +%Y%m%d).db
```

---

## 三、Phase 1：SQLite → PostgreSQL（Week 1-6）

### 3.1 里程碑 A：核心层重写（Week 1-2）

| 步骤 | 文件 | 操作 | 检查点 |
|------|------|------|--------|
| 1.1 | `auth-center/models/database.py` | 重写连接管理器（见迁移方案 2.1） | 连接池初始化不报错 |
| 1.2 | `auth-center/models/database.py` | 建表函数全部替换为 PG 语法 | DDL 执行无错误 |
| 1.3 | `auth-center/models/database.py` | 删除所有 PRAGMA、ATTACH、check_same_thread | 搜索确认无残留 |
| 1.4 | `auth-center/models/cms.py` | 逐行审查 50 处 SQL（占位符 + 函数） | CMS 相关 API 返回正常 |
| 1.5 | `auth-center/models/user.py` | 用户 CRUD 改造 | 登录、注册、个人信息正常 |
| 1.6 | `auth-center/models/site.py` | 站点 CRUD 改造 | 站点创建、编辑正常 |

**A 验收标准：**

```bash
# 启动 auth 服务，验证核心功能
python auth_server.py &

# 测试：用户登录
curl -X POST http://localhost:8081/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# 测试：CMS 查询
curl http://localhost:8081/api/posts?page=1

# 测试：用户信息
curl http://localhost:8081/user/profile -H "Authorization: Bearer $TOKEN"
```

### 3.2 里程碑 B：服务层适配（Week 3）

| 步骤 | 文件 | 操作 |
|------|------|------|
| 2.1 | `auth_server.py` | 入口处确认 `get_db()` 引用最新连接池 |
| 2.2 | `platform/app.py` | 逐文件审查 SQL 占位符，`?` → `%s` |
| 2.3 | `admin/app.py` | 逐文件审查 SQL 占位符，`?` → `%s` |
| 2.4 | `health_service/app.py` | 健康检查涉及的 SQL 审查 |

**B 验收标准：**

```bash
# 全部服务启动验证
sudo systemctl restart verorun-auth
sudo systemctl restart verorun-platform
sudo systemctl restart verorun-admin
sudo systemctl restart verorun-health

# 健康检查
curl -s http://localhost:8081/health
curl -s http://localhost:8083/health
curl -s http://localhost:8084/health
curl -s http://localhost:8085/health

# 所有返回 {"status":"ok"}
```

### 3.3 里程碑 C：插件数据库迁移（Week 4）

| 步骤 | 插件 | 操作 | 验证 |
|------|------|------|------|
| 3.1 | `plugins/analytics/` | 改连接为 `analytics` schema | 分析数据可查询 |
| 3.2 | `plugins/health_check/` | 改连接为 `health` schema | 健康数据可写入 |
| 3.3 | `plugins/payment/` | 改连接为 `payment` schema | 支付记录正常 |
| 3.4 | `plugins/order_notify/` | 改连接为 `order_notify` schema | 通知记录正常 |
| 3.5 | `captcha-service/` | 迁入 public schema | 验证码生成/验证正常 |

**C 验收标准：**

```bash
# 逐个插件验证
python -c "
from plugin_manager import get_plugin
p = get_plugin('analytics')
print(p.status())  # 应返回 active
"

python -c "
from plugin_manager import get_plugin
p = get_plugin('payment')
result = p.test_connection()  # 应返回 True
print(result)
"
```

### 3.4 里程碑 D：数据迁移 + 全功能回归（Week 5-6）

**D1 - 执行迁移脚本：**

```bash
# 先在本地开发环境执行
export PG_DSN="host=localhost dbname=easykai_dev user=easykai_dev password=dev_password"
python scripts/sqlite_to_pg_migrate.py

# 验证行数
python -c "
import psycopg2, sqlite3

pg = psycopg2.connect('host=localhost dbname=easykai_dev user=easykai_dev')
sq = sqlite3.connect('data/x7k2m9a4.db')

tables = ['users', 'sites', 'posts', 'comments', 'products', 'orders']
for t in tables:
    pg_count = pg.cursor().execute(f'SELECT COUNT(*) FROM public.{t}').fetchone()[0]
    sq_count = sq.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    match = '✅' if pg_count == sq_count else '❌'
    print(f'{match} {t}: SQLite={sq_count}, PG={pg_count}')
"
```

**D2 - 全功能回归测试清单：**

| # | 功能 | 验证方式 | 通过 |
|---|------|----------|------|
| 1 | 用户注册/登录/登出 | curl 测试 + 浏览器 | [ ] |
| 2 | JWT Token 签发/验证 | curl 测试 | [ ] |
| 3 | 站点创建/编辑/删除 | 管理后台操作 | [ ] |
| 4 | CMS 内容发布/编辑 | 管理后台操作 | [ ] |
| 5 | 商城下单全流程 | 前端模拟 | [ ] |
| 6 | 支付记录写入 | 插件验证 | [ ] |
| 7 | 短信/邮件通知发送 | 插件验证 | [ ] |
| 8 | 验证码生成/校验 | API 测试 | [ ] |
| 9 | 数据分析查询 | 管理后台图表 | [ ] |
| 10 | 健康检查 | 各个 `/health` 端点 | [ ] |
| 11 | 插件加载/卸载 | 插件管理页面 | [ ] |
| 12 | 备份脚本（pg_dump） | 命令行验证 | [ ] |

### 3.5 Phase 1 服务器部署

```bash
# 1. 服务器安装 PG
ssh easykai@***REMOVED***
sudo apt install -y postgresql-16 postgresql-contrib

# 2. 创建数据库
sudo -u postgres psql <<EOF
CREATE USER easykai WITH PASSWORD '***REMOVED***';
CREATE DATABASE easykai OWNER easykai;
GRANT ALL PRIVILEGES ON DATABASE easykai TO easykai;
EOF

# 3. 本地同步代码到服务器
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.db' \
  f:/Sites/VeroRun/ easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/

# 4. 服务器安装依赖
ssh easykai@***REMOVED*** "cd /home/easykai/easykai-workspace/easykai.cn && pip install psycopg2-binary==2.9.9"

# 5. 上传 SQLite 文件到服务器
scp data/x7k2m9a4.db easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/data/
scp data/shop.db easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/data/

# 6. 执行迁移
ssh easykai@***REMOVED*** "cd /home/easykai/easykai-workspace/easykai.cn && python scripts/sqlite_to_pg_migrate.py"

# 7. 更新 .env 并重启
ssh easykai@***REMOVED*** <<'REMOTE_SCRIPT'
cd /home/easykai/easykai-workspace/easykai.cn
cat >> .env <<EOF
DB_ENGINE=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_DB=easykai
PG_USER=easykai
PG_PASSWORD=***REMOVED***
EOF
sudo systemctl restart verorun-*
REMOTE_SCRIPT

# 8. 验证
curl -s https://easykai.cn/health
```

---

## 四、Phase 2：Admin 后台 Vue 3（Week 7-18）

### 4.1 Sprint 1：项目搭建（Week 7-8）

**Day 1-3：脚手架**

```bash
cd f:/Sites/VeroRun/admin

# 使用 Vite 创建 Vue 3 + TS 项目
npm create vite@latest frontend -- --template vue-ts
cd frontend

# 安装依赖
npm install
npm install vue-router@4 pinia axios
npm install naive-ui @vicons/ionicons5
npm install echarts chart.js vue-echarts
npm install @tiptap/vue-3 @tiptap/starter-kit
npm install vue-i18n@9
npm install unplugin-vue-components unplugin-auto-import -D
npm install unplugin-icons @iconify/json -D

# 验证
npm run dev
```

**Day 4-7：布局 + 路由 + API 层**

交付物：
- `src/router/index.ts` — 47 条路由
- `src/components/layout/AdminLayout.vue` — 骨架布局
- `src/components/layout/SidebarNav.vue` — 侧栏导航
- `src/components/layout/TopHeader.vue` — 顶栏
- `src/api/client.ts` — Axios 封装
- `src/stores/auth.ts` — 认证 Pinia store
- `src/stores/app.ts` — 全局状态

**Week 7-8 验收标准：**

- [ ] 路由 `/admin/` → 显示侧栏 + 顶栏布局
- [ ] 所有 47 条路由可点击跳转（页面为占位内容）
- [ ] Axios 实例可发起请求并收到 200 响应
- [ ] 登录页面能正常渲染

### 4.2 Sprint 2：核心页面（Week 9-10）

| 页面 | 关键功能 |
|------|----------|
| DashboardView.vue | ECharts 图表封装，实时数据卡片 |
| UsersView.vue | CRUD 表格，搜索，分页，角色筛选 |
| AdminsView.vue | 类似 UsersView，额外权限管理 |
| CustomersView.vue | 用户列表 + 关联站点信息 |
| AgentsView.vue | Agent 配置管理 |

共享组件交付：
- `DataTable.vue` — 排序、筛选、分页、行选择
- `Modal.vue` — 表单弹窗
- `Pagination.vue` — 通用分页
- `SearchBar.vue` — 搜索 + 筛选栏
- `StatusBadge.vue` — 状态标签
- `EmptyState.vue` — 空状态

**Week 9-10 验收标准：**

- [ ] 仪表盘正常加载，图表可交互
- [ ] 用户列表：搜索、排序、分页、新增、编辑、删除均生效
- [ ] DataTable 组件可通过 props 配置复用

### 4.3 Sprint 3：电商核心（Week 11-12）

| 页面 | 关键功能 |
|------|----------|
| ShopProductsView.vue | 商品 CRUD，图片上传，规格管理 |
| ShopCategoriesView.vue | 分类树形管理 |
| ShopOrdersView.vue | 订单列表，状态流转 |
| OrdersView.vue | 全站订单总览 |
| SubOrdersView.vue | 子订单管理 |
| PlansView.vue | 套餐计划管理 |
| SubscriptionsView.vue | 订阅管理 |

共享组件交付：
- `FileUpload.vue` — 拖拽上传 + 预览
- `JsonEditor.vue` — JSON 配置编辑（用于产品 AI 配置）
- `ConfirmDialog.vue` — 确认对话框

**Week 11-12 验收标准：**

- [ ] 商品完整 CRUD，图片可上传
- [ ] 订单状态可流转（待支付→已支付→已发货→已完成）
- [ ] 套餐/订阅管理可用

### 4.4 Sprint 4：内容管理（Week 13-14）

| 页面 | 关键功能 |
|------|----------|
| CmsView.vue | 页面/内容管理 |
| PostsView.vue | 文章 CRUD，Tiptap 编辑器集成 |
| CommentsView.vue | 评论审核 |
| MediaLibraryView.vue | 媒体库管理 |
| AllContentView.vue | 全站内容总览 |
| NotificationsView.vue | 通知管理 |

**Week 13-14 验收标准：**

- [ ] Tiptap 富文本编辑器正常，图片/视频可插入
- [ ] 媒体库可上传、预览、删除
- [ ] 评论可审核通过/拒绝

### 4.5 Sprint 5：运营 + 系统管理（Week 15-16）

| 页面 | 关键功能 |
|------|----------|
| PluginsAdminView.vue | 插件列表、启用/禁用 |
| PluginsStoreView.vue | 插件市场 |
| ThemesView.vue | 主题切换预览 |
| ConfigView.vue | 系统配置 |
| BrandView.vue | 品牌设置 |
| SiteSettingsView.vue | 站点设置 |
| NavSettingsView.vue | 导航配置 |
| DeployView.vue | 部署管理 |
| ApiKeysView.vue | API 密钥管理 |
| I18nTranslationsView.vue | 翻译管理 |

**Week 15-16 验收标准：**

- [ ] 插件可启用/禁用
- [ ] 5 套主题实时切换预览
- [ ] API 密钥可创建/删除

### 4.6 Sprint 6：高级功能（Week 17）

| 页面 | 关键功能 |
|------|----------|
| AnalyticsView.vue | ECharts + Chart.js 数据分析面板 |
| HealthView.vue | 实时监控面板 |
| MatrixView.vue | Agent 矩阵配置 |
| AutomationView.vue | 自动化流程配置 |
| ModelProvidersView.vue | AI 模型提供商配置 |
| TokenMonitoringView.vue | Token 用量监控 |
| LogsView.vue | 系统日志查看 |
| MiniAppsView.vue | 小程序管理 |
| TicketsView.vue | 工单管理 |
| SmsView.vue | 短信管理 |
| DownloadsView.vue | 下载管理 |
| CleanerView.vue | 数据清理 |
| FeatureOrdersView.vue | 功能订单 |
| RewardRulesView.vue | 奖励规则 |
| SubStatsView.vue | 订阅统计 |
| SubEventsView.vue | 订阅事件 |
| ShopPurchasesView.vue | 购买记录 |

**Week 17 验收标准：**

- [ ] 所有剩余 17 个页面可正常渲染和功能可用

### 4.7 Sprint 7：收尾（Week 18）

| 任务 | 内容 |
|------|------|
| 暗色模式 | Naive UI `darkTheme` 切换，CSS 变量适配 |
| 响应式适配 | 平板/手机断点优化 |
| 国际化 | vue-i18n 集成，从 `i18n/` 目录加载翻译 |
| 构建优化 | 代码分割（见 vite.config.ts），Tree Shaking |
| 性能 | 首屏加载 < 3s，Lighthouse > 90 |

### 4.8 Admin SPA 部署

```bash
# 构建
cd admin/frontend
npm run build

# Nginx 配置更新
# 参考 docs/migration-frontend-modernization.md 第 6.1 节

# 部署静态文件
rsync -av dist/ easykai@***REMOVED***:/home/easykai/easykai-workspace/easykai.cn/admin/frontend/dist/

# 服务器重载 Nginx
ssh easykai@***REMOVED*** "sudo nginx -t && sudo nginx -s reload"

# 验证
curl -s https://easykai.cn/admin/ | head -20
# 应返回 <!doctype html> Vue SPA 入口
```

---

## 五、风险控制矩阵

| 风险 | 发生概率 | 影响 | 缓解措施 | 触发条件 | 负责人 |
|------|----------|------|----------|----------|--------|
| PG 迁移后 SQL 语法错误 | 中 | 高 | 全项目审计清单 + 逐文件审查 | 任何服务启动后 500 错误 | 后端 |
| 迁移后数据不一致 | 低 | 极高 | 行数校验脚本 + 抽样比对 | 校验脚本报差异 | 后端 |
| Admin SPA 进度延后 | 中 | 中 | 2 周 Sprint 节奏，超时则砍页面范围 | 连续 2 个 Sprint 未完成 | 前端 |
| 主题视觉效果不一致 | 中 | 低 | Storybook 组件级对比 | 用户差评 | 前端 |
| SPA + Jinja2 共存期混乱 | 低 | 中 | Nginx 精确路由匹配，API 走 Flask / 页面走 SPA | 页面 404 | 运维 |
| 服务器 PG 安装冲突 | 低 | 高 | 先在 staging 环境验证，再上生产 | 安装命令失败 | 运维 |

---

## 六、每日站会议程模板

```
1. 昨天完成：按照计划，完成了哪些任务？
2. 今天计划：今天要完成什么？
3. 阻塞项：有没有卡住的问题？
4. 风险更新：有没有新的风险出现？
```

---

## 七、文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| 数据库迁移方案 | [docs/migration-sqlite-to-postgresql.md](migration-sqlite-to-postgresql.md) | SQL 语法转换规则、迁移脚本、回滚方案 |
| 前端现代化方案 | [docs/migration-frontend-modernization.md](migration-frontend-modernization.md) | 目录结构、47 页面映射、Vue 技术选型 |
| 实施计划（本文档） | [docs/implementation-plan.md](implementation-plan.md) | 每日执行手册、里程碑、验收标准 |
