# 下一会话计划

> 由 2026-06-22 会话生成
> 在新会话中，先让 AI 读取此文件，然后说："加载计划并继续"

## 一、会话状态

### 已完成并部署（生产运行中）

| 任务 | 涉及文件 | 状态 |
|------|---------|------|
| 收入看板增强 | `auth-center/routes/admin.py` — `/admin/revenue/dashboard` API | ✅ 已部署 |
| 优惠券系统升级 | `auth-center/routes/shop_admin.py` — 统计/发放/记录 API | ✅ 已部署 |
| 优惠券验证增强 | `platform/routes/shop_public.py` — 新人专享/每人限用/免邮 | ✅ 已部署 |
| 优惠券表扩展 | `auth-center/models/database.py` — 5 个新字段 | ✅ 已部署 |
| 后台优惠券管理UI | `admin/templates/admin.html` — 统计卡片+搜索+发放 | ✅ 已部署 |
| 后台收入看板UI | `admin/templates/admin.html` — 趋势图+分类统计 | ✅ 已部署 |
| 订单集成进控制台 | `platform/templates/index.html` — billing 页展示商城+订阅订单 | ✅ 已部署 |
| 发票系统 | `invoice_service.py` — `invoices` 表 + PDF 生成 + 下载 API | ✅ 已部署 |
| 1688 OAuth CSRF 防护 | `ali_api/` — 持久化 state + system_config 读取密钥 | ✅ 已部署 |
| 支付配置规范化 | system_config 表驱动支付宝/微信支付配置 | ✅ 已部署 |
| UCenter 导航增强 | 订阅管理入口 + 订单优化样式 | ✅ 已部署 |
| Git v0.8.9 | 22 files, 2898 insertions, 297 deletions | ✅ `e5df96c` |

### 已恢复（不存在的改动）

| 改动 | 状态 |
|------|------|
| `console.html` 独立控制台页面 | ❌ 已删除，服务器已清理 |
| `/console` 路由 | ❌ 已从 app.py/shop_public.py 删除 |
| `site_routes.py` 白名单改动 | ❌ 已恢复原始 catch-all |
| `subscribe_portal.html` 导航链接 | ❌ 已恢复为"用户中心" |

### 遗留问题

1. **`/console` 返回 308/500** — 这是 Flask 默认行为 + `site_bp` catch-all (`/<slug>/`) 拦截的结果，不响应用户功能，但如果你想彻底清除这个 308 响应，需要进一步排查。

---

## 二、系统架构要点（不要踩的坑）

### 路由优先级
- **app 路由** > **蓝图路由** > **蓝图 catch-all**（`/<slug>/`）
- `site_bp` 的 `/<slug>/` 会拦截所有单段路径（如 `/console`、`/xxx`）
- **不要建独立页面路由**（如 `/console`），**不要新建独立模板文件**

### 用户订单在哪
- **订阅订单** → `subscription_orders` 表，API: `/subscription/orders`
- **商城订单** → `order_items` 表，API: `/shop/api/orders`
- **用户面展示** → 已集成进控制台 `loadBilling()`（财务→订阅与账单）

### 关键原则
- 用户端功能**必须集成进** `platform.easykai.cn` 现有控制台（`index.html`）
- 不要单独建页面（如 `/shop/ucenter` 是历史遗留，可以逐步迁移但不要新建同类型）
- 管理后台在 `admin.easykai.cn`（`admin/templates/admin.html`）

---

## 三、P1 待做（防止收入流失）

### 1. Dunning 通知（扣款失败通知）
- 现状：`renewal.py` 已有 Dunning 重试逻辑（1/3/7天），已集成站内信 + SMS 通知（`renewal_reminder.py`）
- 状态：✅ 已完成

### 2. 缴费挽回流程
- 现状：扣款失败后标记 `past_due`，`POST /subscription/retry-payment` 提供重试支付入口
- 涉及文件：`auth-center/routes/subscription/__init__.py` + `platform/templates/subscribe_portal.html`
- 状态：✅ 已完成

### 3. 宽限期降级保护
- 现状：已有 7 天宽限期，到期自动 expired 并降 Free，已集成降级通知（站内信 + SMS）
- 涉及文件：`auth-center/routes/subscription/renewal.py` + `auth-center/services/renewal_reminder.py`
- 状态：✅ 已完成

---

## 四、P2 待做（管理与运营）

### 4. 收入看板增强（✅ 完整完成）
- 已完成：MRR/ARR/趋势图/分类统计/支付方式分布
- 已完成：流失率计算（本月/上月/12月趋势）、活跃订阅数日趋势图
- 涉及文件：`auth-center/routes/admin.py` + `platform/templates/admin.html`

### 5. 优惠券升级（✅ 完整完成）
- 已完成：百分比/新人专享/满减/免邮/每人限用/适用商品/统计/批量发放
- 已完成：**首月特价**（`first_month_percent` 类型，仅限首月生效）、**叠加规则**（stackable 标记）、**限时折扣**（active_from/active_to 时间窗口）
- 涉及文件：`auth-center/models/database.py` + `auth-center/routes/subscription/__init__.py` + `admin/templates/admin.html`

### 6. 发票系统（✅ 完整完成）
- 新增 `invoices` 表（自动迁移）
- 支付成功后自动生成电子发票（`invoice_service.py`，依赖 fpdf2）
- `GET /subscription/my/invoices` — 用户发票列表
- `GET /subscription/my/invoices/<no>/download` — PDF 下载（JS Blob 下载，携带 JWT）
- 订阅门户展示发票列表 + 下载按钮
- 涉及文件：`auth-center/models/database.py` + `auth-center/routes/subscription/__init__.py` + `auth-center/services/invoice_service.py` + `platform/templates/subscribe_portal.html`

---

## 五、其他改动（非此会话）

### ali_api 相关改动
以下文件有 uncommitted 改动，但**不属于本次会话的重点**，可能来自其他工作：

- `ali_api/config.py`
- `ali_api/models.py`
- `ali_api/routes/admin.py`
- `ali_api/services/rate_limiter.py`
- `ali_api/static/ali_console.js`
- `auth-center/routes/subscription/__init__.py`
- `auth-center/routes/subscription/gateway/alipay.py`
- `auth-center/routes/subscription/gateway/wechat.py`
- `auth-center/routes/user.py`
- `platform/app.py`
- `platform/routes/site_routes.py`
- `platform/templates/admin.html`
- `platform/templates/shop_detail.html`
- `platform/templates/subscribe.html`

这些改动用 `git diff HEAD` 可以查看详情，建议在新会话中确认是否需要 commit 或恢复。

---

## 六、部署方式

```python
# 部署单个文件（index.html 等模板用）
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('***REMOVED***', username='easykai', password='***REMOVED***', ...)
sftp = ssh.open_sftp()
sftp.put(local_path, remote_path)
sftp.close()
# 重启
ssh.exec_command('echo ***REMOVED*** | sudo -S systemctl restart platform.service')
ssh.close()

# 部署 Python 文件需要清理缓存
# echo ***REMOVED*** | sudo -S find ... -name "__pycache__" -type d -exec rm -rf {} +
```

### 服务端口
| 服务 | 端口 |
|------|------|
| platform (platform.easykai.cn) | 8083 |
| admin (admin.easykai.cn) | 8084 |
| subscription captcha | 8090 |
