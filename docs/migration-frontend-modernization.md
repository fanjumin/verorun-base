# 前端现代化迁移方案

> 版本：v0.1 | 日期：2026-07-15 | 状态：方案阶段

---

## 一、现状分析

| 维度 | 当前状态 |
|------|----------|
| 模板引擎 | Jinja2 服务端渲染 |
| 模板数量 | admin 60 个、platform 42 个、site 42 个，+ 插件模板，共 150+ |
| JavaScript | 原生 JS（无框架），ECharts、Chart.js、Quill 等库 |
| CSS | 自有设计系统 + 5 套主题（default/light/nature/ocean/warm） |
| SDK | 5 个原生 JS SDK（common/wechat/telegram/douyin/line） |
| 构建工具 | 仅 esbuild 用于 SDK 打包 |

---

## 二、框架选型对比

| 框架 | 适合度 | 优势 | 劣势 | 适用阶段 |
|------|--------|------|------|----------|
| **HTMX + Alpine.js** | ★★★★★ | 改动最小，保留 Jinja2，渐进增强 | 非典型 SPA | Site 官网 |
| **Vue 3 + Vite** | ★★★★ | 渐进式，可逐页迁移，生态好 | 学习成本 | Admin + Platform |
| **React + Next.js** | ★★★ | 最现代，SSR/SSG | 全量重写 150+ 模板 | 不建议 |
| **Svelte / Solid** | ★★ | 性能好 | 小众，招聘困难 | 不建议 |

### 推荐组合策略

```
Admin 后台 (60 模板)  →  Vue 3 + Vite + Naive UI（全量 SPA）
Platform 控制台 (42)  →  Vue 3 渐进式（优先核心页面）
Site 官网 (42)        →  保留 Jinja2 + HTMX 增强（保持 SEO）
```

---

## 三、Admin 后台 Vue 3 方案（Phase 1）

### 3.1 技术栈

| 类别 | 选型 | 理由 |
|------|------|------|
| 框架 | Vue 3.4+ Composition API | 渐进式，与现有 Jinja2 共存 |
| 语言 | TypeScript | 类型安全 |
| 构建 | Vite 5 | 秒级热更新 |
| UI 库 | Naive UI | 完整企业级组件，内置暗色模式 |
| 路由 | Vue Router 4 | SPA 路由 |
| HTTP | Axios | 拦截器、请求取消、Token 刷新 |
| 状态管理 | Pinia | Vue 3 官方 |
| 图表 | ECharts 5（保留） | 封装为 Vue 组件 |
| 图表2 | Chart.js（保留） | 同上 |
| 编辑器 | Tiptap 或保留 Quill | Tiptap 对 Vue 3 支持更好 |
| 图标 | Unplugin Icons + Iconify | 按需加载 |
| 国际化 | vue-i18n | 配合现有 i18n 目录 |

### 3.2 目录结构

```
admin/frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.ts                    # 入口
│   ├── App.vue                    # 根组件
│   ├── router/
│   │   └── index.ts               # 47 条路由
│   ├── stores/
│   │   ├── auth.ts                # 认证状态
│   │   └── app.ts                 # 全局状态（侧栏折叠、主题等）
│   ├── api/
│   │   ├── client.ts              # Axios 实例（拦截器、错误处理）
│   │   ├── users.ts               # 用户 API
│   │   ├── products.ts            # 商品 API
│   │   ├── orders.ts              # 订单 API
│   │   ├── analytics.ts           # 分析 API
│   │   ├── subscriptions.ts       # 订阅 API
│   │   ├── plugins.ts             # 插件管理 API
│   │   ├── themes.ts              # 主题 API
│   │   └── ...                    # 每个模块一个文件
│   ├── views/
│   │   ├── DashboardView.vue
│   │   ├── UsersView.vue
│   │   ├── ShopProductsView.vue
│   │   └── ... (47 个页面组件)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AdminLayout.vue    # 后台布局（侧栏+顶栏+内容）
│   │   │   ├── SidebarNav.vue     # 侧栏导航
│   │   │   └── TopHeader.vue      # 顶栏
│   │   ├── DataTable.vue          # 通用数据表格（排序/筛选/分页）
│   │   ├── Modal.vue              # 通用弹窗
│   │   ├── ChartCard.vue          # 图表卡片容器
│   │   ├── SearchBar.vue          # 搜索栏
│   │   ├── Pagination.vue         # 分页组件
│   │   ├── ConfirmDialog.vue      # 确认对话框
│   │   ├── EmptyState.vue         # 空状态占位
│   │   ├── JsonEditor.vue         # JSON 配置编辑器
│   │   ├── FileUpload.vue         # 文件上传
│   │   └── StatusBadge.vue        # 状态标签
│   ├── composables/
│   │   ├── useApi.ts              # API 调用封装（loading/error 状态）
│   │   ├── useAuth.ts             # 认证逻辑（login/logout/token）
│   │   ├── usePagination.ts       # 分页逻辑
│   │   ├── useTable.ts            # 表格排序/筛选
│   │   ├── useTheme.ts            # 主题切换
│   │   └── useDebounce.ts         # 防抖
│   └── styles/
│       ├── variables.css          # CSS 变量
│       └── global.css             # 全局样式
```

### 3.3 页面 → 组件映射（47 个页面）

```
admin/templates/partials/           admin/frontend/src/views/
─────────────────────────           ───────────────────────────
dashboard.html              →       DashboardView.vue
users.html                  →       UsersView.vue
customers.html              →       CustomersView.vue
admins.html                 →       AdminsView.vue
agents.html                 →       AgentsView.vue
customer_agents.html        →       CustomerAgentsView.vue
posts.html                  →       PostsView.vue
all_content.html            →       AllContentView.vue
cms.html                    →       CmsView.vue
comments.html               →       CommentsView.vue
shop_products.html          →       ShopProductsView.vue
shop_categories.html        →       ShopCategoriesView.vue
shop_orders.html            →       ShopOrdersView.vue
shop_purchases.html         →       ShopPurchasesView.vue
orders.html                 →       OrdersView.vue
sub_orders.html             →       SubOrdersView.vue
subscriptions.html          →       SubscriptionsView.vue
sub_events.html             →       SubEventsView.vue
sub_stats.html              →       SubStatsView.vue
plans.html                  →       PlansView.vue
feature_orders.html         →       FeatureOrdersView.vue
reward_rules.html           →       RewardRulesView.vue
plugins_admin.html          →       PluginsAdminView.vue
plugins_store.html          →       PluginsStoreView.vue
themes.html                 →       ThemesView.vue
analytics.html              →       AnalyticsView.vue
health.html                 →       HealthView.vue
logs.html                   →       LogsView.vue
token_monitoring.html       →       TokenMonitoringView.vue
automation.html             →       AutomationView.vue
model_providers.html        →       ModelProvidersView.vue
matrix.html                 →       MatrixView.vue
notifications.html          →       NotificationsView.vue
sms.html                    →       SmsView.vue
tickets.html                →       TicketsView.vue
media_library.html          →       MediaLibraryView.vue
mini_apps.html              →       MiniAppsView.vue
site_settings.html          →       SiteSettingsView.vue
nav_settings.html           →       NavSettingsView.vue
config.html                 →       ConfigView.vue
brand.html                  →       BrandView.vue
deploy.html                 →       DeployView.vue
downloads.html              →       DownloadsView.vue
cleaner.html                →       CleanerView.vue
api_keys.html               →       ApiKeysView.vue
i18n_translations.html      →       I18nTranslationsView.vue
```

### 3.4 API 层实现

```typescript
// admin/frontend/src/api/client.ts
import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth'

const apiClient: AxiosInstance = axios.create({
  baseURL: '/admin/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,  // 携带 Cookie 用于 JWT 跨子域认证
})

// 请求拦截器：自动附带 Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore().logout()
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

```typescript
// admin/frontend/src/api/users.ts
import apiClient from './client'

export interface User {
  id: number
  username: string
  display_name: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

export const usersApi = {
  list(params: { page?: number; search?: string; role?: string }) {
    return apiClient.get<PaginatedResponse<User>>('/users', { params })
  },
  get(id: number) {
    return apiClient.get<User>(`/users/${id}`)
  },
  create(data: Partial<User>) {
    return apiClient.post<User>('/users', data)
  },
  update(id: number, data: Partial<User>) {
    return apiClient.put<User>(`/users/${id}`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/users/${id}`)
  },
}
```

### 3.5 后端 API 适配（Flask 新增 REST 端点）

```python
# admin/api_v1.py —— 新增 REST API 端点（与现有 Jinja2 渲染并存）
from flask import Blueprint, request, jsonify
from auth_center.models import get_db

api_bp = Blueprint('admin_api_v1', __name__, url_prefix='/admin/api')


@api_bp.route('/users', methods=['GET'])
def list_users():
    """GET /admin/api/users?page=1&search=xxx&per_page=20"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    per_page = request.args.get('per_page', 20, type=int)
    offset = (page - 1) * per_page

    with get_db() as db:
        # 计数
        count_sql = "SELECT COUNT(*) FROM users WHERE username ILIKE %s OR display_name ILIKE %s"
        row = db.execute(count_sql, (f'%{search}%', f'%{search}%')).fetchone()
        total = row[0]

        # 查询
        data_sql = """
            SELECT id, username, display_name, email, role, is_active, created_at
            FROM users
            WHERE username ILIKE %s OR display_name ILIKE %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = db.execute(data_sql, (f'%{search}%', f'%{search}%', per_page, offset)).fetchall()

        items = [dict(r) for r in rows]

    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


# ... 其他 CRUD 端点类似
```

Flask 注册 API 蓝图：

```python
# admin/app.py
from flask import Flask
from admin.api_v1 import api_bp

app = Flask(__name__)
app.register_blueprint(api_bp)
# 旧的 Jinja2 路由逐步退役
```

---

## 四、JWT SSO 适配

当前跨子域 SSO 基于 Cookie：

```
easykai.cn           → Set-Cookie: token=xxx; Domain=.easykai.cn; HttpOnly; Secure
admin.easykai.cn     → 自动携带 Cookie（同父域）
platform.easykai.cn  → 自动携带 Cookie
```

迁移到 Vue SPA 后方案：

### 方案 A：保留 Cookie 认证（推荐）

```typescript
// 零改动。Axios 设置 withCredentials: true
// Cookie 自动携带，无需额外 Token 管理
// 适用于同一父域下的子域
```

### 方案 B：Bearer Token（如需跨域）

```typescript
// admin/frontend/src/composables/useAuth.ts
import { ref } from 'vue'
import apiClient from '@/api/client'

const useAuth = () => {
  const isAuthenticated = ref(false)

  const login = async (username: string, password: string) => {
    const res = await apiClient.post('/login', { username, password })
    localStorage.setItem('admin_token', res.data.access_token)
    localStorage.setItem('admin_refresh_token', res.data.refresh_token)
    isAuthenticated.value = true
  }

  const refreshToken = async () => {
    const refresh = localStorage.getItem('admin_refresh_token')
    if (!refresh) return false
    try {
      const res = await apiClient.post('/token/refresh', { refresh_token: refresh })
      localStorage.setItem('admin_token', res.data.access_token)
      return true
    } catch {
      logout()
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_refresh_token')
    apiClient.post('/logout')
    isAuthenticated.value = false
    window.location.href = '/admin/login'
  }

  return { isAuthenticated, login, logout, refreshToken }
}

export default useAuth
```

---

## 五、主题系统迁移

5 套 CSS 主题转为 CSS Variables + Naive UI 主题覆盖：

```css
/* admin/frontend/src/styles/variables.css */
:root {
  --color-primary: #4F46E5;
  --color-primary-hover: #4338CA;
  --color-bg: #F9FAFB;
  --color-surface: #FFFFFF;
  --color-text: #111827;
  --color-text-secondary: #6B7280;
  --color-border: #E5E7EB;
  --radius-sm: 6px;
  --radius-md: 8px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
}

[data-theme="light"] {
  --color-primary: #4F46E5;
  --color-bg: #FFFFFF;
}

[data-theme="nature"] {
  --color-primary: #16A34A;
  --color-primary-hover: #15803D;
}

[data-theme="ocean"] {
  --color-primary: #0891B2;
  --color-primary-hover: #0E7490;
}

[data-theme="warm"] {
  --color-primary: #DC2626;
  --color-primary-hover: #B91C1C;
}
```

```typescript
// admin/frontend/src/composables/useTheme.ts
import { darkTheme, type GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: Record<string, GlobalThemeOverrides> = {
  default: { common: { primaryColor: '#4F46E5' } },
  nature:  { common: { primaryColor: '#16A34A' } },
  ocean:   { common: { primaryColor: '#0891B2' } },
  warm:    { common: { primaryColor: '#DC2626' } },
}

export const useTheme = () => {
  const applyTheme = (themeName: string) => {
    document.documentElement.setAttribute('data-theme', themeName)
    // Naive UI 主题通过 provide 注入，见 App.vue
  }
  return { applyTheme, themeOverrides }
}
```

---

## 六、渐进迁移部署（与 Flask 共存）

### 6.1 Nginx 配置

```nginx
# /etc/nginx/sites-enabled/easykai.conf

# Admin 后台 —— SPA 静态资源 + API 代理分离
location /admin/ {
    # API 请求转发到 Flask 后端
    location /admin/api/ {
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 登录页保留 Flask Jinja2 渲染（安全考虑）
    location /admin/login {
        proxy_pass http://127.0.0.1:8084;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # SPA 静态资源（Vite 构建产物）
    location /admin/assets/ {
        alias /home/easykai/easykai-workspace/easykai.cn/admin/frontend/dist/assets/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 其他路由交给 Vue SPA（history mode）
    location /admin/ {
        alias /home/easykai/easykai-workspace/easykai.cn/admin/frontend/dist/;
        try_files $uri $uri/ /admin/index.html;
    }
}
```

### 6.2 构建命令

```bash
cd admin/frontend

# 开发
npm run dev                # Vite dev server，代理 API 到 Flask

# 生产构建
npm run build              # 输出到 dist/

# 部署
rsync -av dist/ /home/easykai/easykai-workspace/easykai.cn/admin/frontend/dist/
```

### 6.3 Vite 开发代理配置

```typescript
// admin/frontend/vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/admin/',
  server: {
    port: 5173,
    proxy: {
      '/admin/api': {
        target: 'http://127.0.0.1:8084',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        // 代码分割：按模块拆分
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-ui': ['naive-ui'],
          'vendor-charts': ['echarts', 'chart.js'],
        },
      },
    },
  },
})
```

---

## 七、实施时间线

```
Week 1-2:  项目搭建
           ├── Vite + Vue 3 + Naive UI 初始化
           ├── TypeScript 配置
           ├── 路由结构、布局组件（AdminLayout / SidebarNav / TopHeader）
           └── Axios 封装、API 客户端

Week 3-4:  核心页面
           ├── DashboardView.vue（含 ECharts 封装）
           ├── UsersView.vue（CRUD 表格）
           ├── ShopProductsView.vue（商品管理）
           ├── ShopOrdersView.vue（订单管理）
           └── DataTable / Modal / Pagination 共享组件

Week 5-6:  内容管理
           ├── CmsView.vue
           ├── PostsView.vue
           ├── CommentsView.vue
           ├── MediaLibraryView.vue
           └── 集成 Tiptap 编辑器

Week 7-8:  运营管理
           ├── OrdersView / SubscriptionsView
           ├── PlansView / CouponsView
           ├── PluginsAdminView
           ├── ThemesView（主题预览切换）
           └── NotificationsView

Week 9-10: 高级功能
           ├── AnalyticsView（ECharts + Chart.js 封装）
           ├── HealthView（实时监控面板）
           ├── MatrixView（Agent 矩阵配置）
           ├── AutomationView（工作流编排）
           └── ConfigView（JSON 编辑器）

Week 11:   收尾
           ├── 暗色模式切换
           ├── 响应式适配（平板/手机）
           ├── 国际化（vue-i18n 集成）
           └── 构建优化、代码分割、Tree Shaking

Week 12:   部署 & 并行运行
           ├── Nginx 配置（API → Flask, 其余 → SPA）
           ├── 与 Jinja2 版本并行运行 1 周
           ├── 用户验收测试
           └── 全量切换
```

---

## 八、工作量估算

| 阶段 | 范围 | 预估算（人天） |
|------|------|---------------|
| Phase 1 | Admin 后台 Vue 3 全量 SPA（47 页面） | 35-45 |
| Phase 2 | Platform 控制台 Vue 3 渐进式（核心页面） | 20-28 |
| Phase 3 | Site 官网 Jinja2 + HTMX 增强 | 5-8 |
| **合计** | | **60-81 人天** |

---

## 九、风险清单

| 风险等级 | 描述 | 缓解措施 |
|----------|------|----------|
| **高** | 150+ 模板逐个重构，遗漏页面 | 建立页面映射清单，逐项追踪 |
| **高** | 原生 JS 函数（如 `window.l_plugins()`）迁移遗漏 | 全局搜索 `window.` 前缀函数，建立迁移清单 |
| **中** | 5 套主题视觉一致性 | 建立 Storybook 或主题对比页面 |
| **中** | SDK 兼容（原 5 个原生 JS SDK） | 先在 Vue 中用 `<script>` 直接引用，后续包装 |
| **中** | JWT Cookie 跨子域在 SPA 模式下可能变化 | 保留 Cookie 方案，避免改动认证逻辑 |
| **低** | IE 兼容性 | 不兼容 IE，仅现代浏览器 |
