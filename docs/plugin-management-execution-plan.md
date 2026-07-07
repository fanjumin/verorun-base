# 插件管理模块 — 详细执行计划

生成日期：2026-07-07
对应设计方案：`docs/plugin-management-system-design.md`

---

## 一、总体路线图

```
第1-2周       第3-5周       第6-8周       第9-10周      第11-12周     第13-14周    第15-16周
┌──────┐     ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ 阶段一 │     │ 阶段二   │    │ 阶段三   │    │ 阶段四   │    │ 阶段五   │    │ 阶段六   │    │ 阶段七   │
│ 核心   │────►│ 管理API │───►│ 标准化  │───►│ 高级   │───►│License │───►│ 支付    │───►│ 开发者  │
│ 引擎   │     │ + UI   │    │ + 钩子  │    │ 功能   │    │ + 商店 │    │ + 订阅  │    │ 中心   │
│ (P0)  │     │ (P0)   │    │ (P1)   │    │ (P2)   │    │ (P1)   │    │ (P2)   │    │ (P3)   │
└──────┘     └────────┘    └────────┘    └────────┘    └────────┘    └────────┘    └────────┘
    │            │            │            │             │             │            │
    ▼            ▼            ▼            ▼             ▼             ▼            ▼
  里程碑1      里程碑2      里程碑3      里程碑4       里程碑5       里程碑6      里程碑7
  核心可用    后台可管理    插件标准化    基础设施    可付费安装     线上交易    开放平台
```

**总预估周期**：约 16 周（4 个月），可根据人员投入缩短。

---

## 二、各阶段详细计划

### 阶段一：核心引擎 + 数据库（P0）

**里程碑**：`plugin_manager` 模块可初始化，能扫描 `plugins/` 目录并持久化插件状态。

**依赖前提**：无（新模块，独立开发）

#### 任务拆解

| ID | 任务 | 子任务 | 预计工时 | 依赖 | 交付物 |
|----|------|--------|---------|------|--------|
| 1.1 | 创建模块骨架 | 新建 `plugin_manager/` 目录、`__init__.py`、`setup.py`（如需要） | 0.5h | 无 | 目录结构 |
| 1.2 | 实现 PluginRegistry 模型 | `plugin_manager/models.py`：`PluginRegistry` 表（id, identifier, name, version, metadata JSON, status, config JSON, installed_at, updated_at, last_error） | 1h | 无 | `models.py` |
| 1.3 | 实现自定义异常体系 | `plugin_manager/exceptions.py`：`PluginError`(base)、`PluginNotFoundError`、`PluginDependencyError`、`PluginLicenseError`、`PluginConflictError` | 0.5h | 无 | `exceptions.py` |
| 1.4 | 实现 PluginDiscovery | `plugin_manager/discovery.py`：扫描 `plugins/*/plugin.json` → 解析元信息 → 返回 `PluginInfo` 列表 | 2h | 无 | `discovery.py` |
| 1.5 | 实现 PluginManager 核心类 | `plugin_manager/__init__.py`：`init_app()`、`discover()`、`install()`、`enable()`、`activate()`、`disable()`、`uninstall()` — 5 状态机完整实现 | 4h | 1.2, 1.3, 1.4 | `__init__.py` |
| 1.6 | 实现 PluginInfo 数据类 | `plugin_manager/models.py`：`@dataclass PluginInfo` + `PluginStatus` 枚举（UNKNOWN/INSTALLED/ENABLED/ACTIVE/DISABLED/UNINSTALLED） | 1h | 无 | models 扩展 |
| 1.7 | 扩展 BasePlugin 基类 | `plugins/base.py`：`setup()`、`activate()`、`deactivate()`、`get_config()`、`set_config()` — 从 PluginManager 接收 plugin_info 和 manager 引用 | 1h | 1.5 | `plugins/base.py` 改造 |
| 1.8 | 编写单元测试 | `tests/test_plugin_manager.py`：覆盖扫描、安装、启用、激活、禁用、卸载、重复安装报错、插件不存在的异常路径 | 3h | 1.5, 1.6, 1.7 | 测试文件 |
| 1.9 | 更新 sync_schema.py | 加入 `plugin_registry` 表到 `scripts/sync_schema.py` 的扫描范围 | 0.5h | 1.2 | schema 更新 |

**阶段一小计**：约 **13.5h**（2 个工作日内）

#### 验收标准

- [ ] `PluginManager(app).init_app(app)` 能正常初始化，不报错
- [ ] 在 `plugins/` 下放入带 `plugin.json` 的目录，`discover()` 能正确识别
- [ ] `install()` → `enable()` → `activate()` 串联调用成功，状态正确流转
- [ ] 禁用后 `disable()` 回到 DISABLED 状态，`uninstall()` 清除记录
- [ ] 重复安装同一插件报 `PluginConflictError`
- [ ] 单元测试通过（`pytest tests/test_plugin_manager.py -v`）

#### 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 插件目录路径在本地和服务器不一致 | 中 | 低 | `init_app()` 中使用 `app.root_path` 拼装，支持配置覆盖 |
| JSON Schema 解析兼容性 | 低 | 中 | 使用 `json.loads()` 标准库，`plugin.json` 键缺失时使用默认值 |

---

### 阶段二：管理 API + 后台 UI（P0）

**里程碑**：管理员可通过后台管理插件列表、启用/禁用、查看详情、修改配置。

**依赖前提**：阶段一完成（PluginManager 核心类可用）

#### 任务拆解

| ID | 任务 | 子任务 | 预计工时 | 依赖 | 交付物 |
|----|------|--------|---------|------|--------|
| 2.1 | 实现 routes.py — 插件 CRUD API | `plugin_manager/routes.py`： | 4h | 1.5 | `routes.py` |
| | | `GET /admin/plugins` — 列表（支持 status 过滤、分页、排序） | | | |
| | | `POST /admin/plugins/discover` — 发现新插件 | | | |
| | | `POST /admin/plugins/<id>/install` — 安装 | | | |
| | | `POST /admin/plugins/<id>/enable` — 启用（含错误返回） | | | |
| | | `POST /admin/plugins/<id>/disable` — 禁用 | | | |
| | | `POST /admin/plugins/<id>/uninstall` — 卸载 | | | |
| | | `GET /admin/plugins/<id>` — 详情 | | | |
| | | `GET /admin/plugins/<id>/config` / `POST ...` — 配置读写 | | | |
| | | `GET /admin/plugins/<id>/status` — 健康状态 | | | |
| 2.2 | 实现插件列表页模板 | `templates/plugin_list.html`：表格展示所有插件（状态标签、版本、作者、操作按钮），支持 filter 切换 | 2h | 2.1 | HTML 模板 |
| 2.3 | 实现插件详情页模板 | `templates/plugin_detail.html`：展示插件完整信息（元信息、依赖树、钩子列表、权限声明）、操作区（启用/禁用/卸载按钮，根据状态禁用不可用操作） | 2h | 2.1 | HTML 模板 |
| 2.4 | 实现插件配置页模板 | `templates/plugin_settings.html`：根据 `plugin.json` 中的 `settings_schema` 动态渲染表单（支持 string/number/boolean/select），POST 提交保存到 `registry.config` | 3h | 2.1 | HTML 模板 |
| 2.5 | 集成到管理后台导航 | 修改现有 admin 导航菜单，添加"插件管理"入口 | 0.5h | 2.1 | 导航修改 |
| 2.6 | 集成测试 | 测试 API 端点的正确性、错误响应（404/400）、权限校验 | 2h | 2.1-2.5 | |

**阶段二小计**：约 **13.5h**（2 个工作日内）

#### 验收标准

- [ ] 9 个 API 端点均可正常调用，返回正确的 JSON
- [ ] 后台上可通过 UI 完成插件的安装 → 启用 → 配置 → 禁用 → 卸载 全流程
- [ ] 配置页面能根据 `settings_schema` 自动渲染表单
- [ ] 错误场景（插件不存在、依赖不满足）返回友好的错误提示
- [ ] 导航菜单正确显示"插件管理"入口

#### 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 动态表单渲染兼容性问题 | 低 | 中 | 限制支持的类型为常见 JSON Schema 子集，不支持的字段 fallback 为 text |
| API 权限未做校验 | 中 | 高 | 所有端点加 `@admin_required` 装饰器（复用现有权限体系） |

---

### 阶段三：5 个插件标准化 + 钩子系统（P1）

**里程碑**：所有现有插件符合新规范，Action/Filter 钩子系统可用，系统关键路径植入钩子。

**依赖前提**：阶段一完成（需要 BasePlugin 和 PluginManager 作为基座）

#### 任务拆解

| ID | 任务 | 子任务 | 预计工时 | 依赖 | 交付物 |
|----|------|--------|---------|------|--------|
| 3.1 | 实现 HookRegistry | `plugin_manager/hooks.py`： | 3h | 1.5 | `hooks.py` |
| | | `add_action(name, callback, priority=10)` | | | |
| | | `remove_action(name, callback, priority)` | | | |
| | | `do_action(name, *args, **kwargs)` — 按 priority 排序串行执行 | | | |
| | | `add_filter(name, callback, priority=10)` | | | |
| | | `remove_filter(name, callback, priority)` | | | |
| | | `apply_filters(name, value, *args, **kwargs)` — 管道模式 | | | |
| | | 优先级数值相同按注册顺序执行 | | | |
| 3.2 | 实现 EventBus | `plugin_manager/events.py`： | 1.5h | 无 | `events.py` |
| | | `publish(event_name, data=None)` — 同步或入队 | | | |
| | | `subscribe(event_name, callback)` | | | |
| | | `unsubscribe(event_name, callback)` | | | |
| | | `on(event_name)` 装饰器 | | | |
| 3.3 | 在系统关键路径植入预定义钩子 | 植入点： | 2h | 3.1, 3.2 | 多处修改 |
| | | `app.before_request` / `app.after_request` — `request` 开始/结束 | | | |
| | | `app.template_context` — 模板变量注入 | | | |
| | | 支付成功后触发 `order.paid` Action | | | |
| | | 用户注册后触发 `user.registered` Action | | | |
| 3.4 | ali_api 标准化 | 新建 `plugin.json`，`__init__.py` 加 `__plugin__` 变量，适配 BasePlugin | 1h | 1.7 | `plugins/ali_api/` |
| 3.5 | coupons 标准化 | 同上 | 0.5h | 1.7 | `plugins/coupons/` |
| 3.6 | reviews 标准化 | 同上 | 0.5h | 1.7 | `plugins/reviews/` |
| 3.7 | wishlist 标准化 | 同上 | 0.5h | 1.7 | `plugins/wishlist/` |
| 3.8 | order_notify 标准化 | 同上 | 0.5h | 1.7 | `plugins/order_notify/` |
| 3.9 | 修复 `self.t()` 作用域 | 将各插件 routes 中的 `self.t()` 改为模块级函数或注入到 `g` 对象 | 2h | 3.4-3.8 | 多处修改 |
| 3.10 | 钩子系统单元测试 | 覆盖 action 执行顺序、filter 管道传递、事件 publish/subscribe、异常处理 | 2h | 3.1, 3.2 | 测试文件 |

**阶段三小计**：约 **13.5h**（2 个工作日内）

#### 验收标准

- [ ] `do_action('order.paid', order=...)` 能被所有注册的回调接收并执行
- [ ] `apply_filters('page.render', html)` 按 priority 顺序逐个处理返回值
- [ ] 5 个插件均包含 `plugin.json`，且内容完整有效
- [ ] 5 个插件均适配 BasePlugin，`activate()`/`deactivate()` 正常执行
- [ ] 修复后 `self.t()` 在路由中不再报错

#### 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 钩子回调执行时间过长影响请求响应 | 中 | 高 | 增加超时机制（`signal.alarm` 或 `concurrent.futures`），超时视为失败 |
| 插件适配后原有功能回归 | 中 | 高 | 每个插件适配后人工验证核心功能流程 |

---

### 阶段四：高级功能（P2）

**里程碑**：插件依赖管理、配置校验、独立日志通道、健康检查。

**依赖前提**：阶段一完成（依赖 PluginManager 核心）

#### 任务拆解

| ID | 任务 | 子任务 | 预计工时 | 依赖 | 交付物 |
|----|------|--------|---------|------|--------|
| 4.1 | 依赖解析器 | `plugin_manager/deps.py`： | 3h | 1.5 | `deps.py` |
| | | 拓扑排序解析 plugin.json 中的 `dependencies` | | | |
| | | 循环依赖检测（Tarjan 或 DFS 染色） | | | |
| | | 版本范围匹配（支持 `>=X.Y.Z`、`==X.Y.Z`、`>=X,<Y`） | | | |
| | | 对缺失依赖给出精确的错误信息 | | | |
| 4.2 | 配置校验器 | `plugin_manager/validators.py`： | 2h | 无 | `validators.py` |
| | | 根据 `settings_schema` 的 JSON Schema 校验用户提交的配置 | | | |
| | | 返回精确的校验错误（哪个字段、什么原因） | | | |
| 4.3 | 独立日志通道 | `plugin_manager/logging.py`： | 1.5h | 1.5 | `logging.py` |
| | | 为每个启用的插件创建独立的日志记录器 `logging.getLogger(f'plugin.{id}')` | | | |
| | | 日志文件写入 `logs/plugins/<name>.log` | | | |
| | | 日志格式包含时间、级别、插件标识 | | | |
| 4.4 | 健康检查 API | `GET /admin/plugins/<id>/status` 增强： | 1.5h | 2.1 | routes 扩展 |
| | | 返回插件运行时间、内存占用（粗略）、依赖状态、License 状态 | | | |
| 4.5 | 单元测试 | 依赖解析循环检测、版本匹配、配置校验 | 2h | 4.1, 4.2 | 测试文件 |

**阶段四小计**：约 **10h**（1.5 个工作日内）

#### 验收标准

- [ ] 依赖解析器能正确检测 A→B→C 链式依赖和 A→B→A 循环依赖
- [ ] 版本匹配 `>=1.0` 能正确匹配 `1.5.0`，拒绝 `0.9.0`
- [ ] 配置校验能正确拒绝类型不匹配、缺少必填字段
- [ ] 插件日志文件独立写入，非插件日志不混入

#### 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| SemVer 版本比较在 Python 中需要外部库 | 低 | 低 | 使用 `packaging` 库（项目可能已存在）或实现简化版 |

---

### 阶段五：License + 本地商店（P1）

**里程碑**：安装免费/付费插件，支持 License 密钥激活和在线/离线校验。

**依赖前提**：阶段一、阶段二完成

#### 任务拆解

| ID | 任务 | 子任务 | 预计工时 | 依赖 | 交付物 |
|----|------|--------|---------|------|--------|
| 5.1 | 实现 LicenseRecord 模型 | `plugin_manager/models_store.py`：`LicenseRecord` 表（plugin_id, site_id, license_key, license_type, license_status, activated_at, expires_at, trial_ends_at, subscription_id, next_billing_at, auto_renew, order_id, customer_email, max_sites） | 1.5h | 无 | `models_store.py` |
| 5.2 | 实现 StorePlugin 模型 | 同上：缓存远程商店的插件目录（identifier, name, description, version, author, price_type, price_amount, price_interval, trial_days, download_url, package_hash, file_size, category, tags, downloads, rating） | 1h | 无 | models_store 扩展 |
| 5.3 | 实现 License 引擎 — 在线验证 | `plugin_manager/license.py`：`LicenseManager` 类、`validate()` 方法调用远程 API、`activate()` 首次激活、`deactivate()` 反激活 | 3h | 5.1, 5.4 | `license.py` |
| 5.4 | 实现 License 引擎 — 离线验证 | 离线 token 生成/解密（对称加密）、站点绑定校验、离线宽容期（72h）逻辑 | 2h | 5.3 | license 扩展 |
| 5.5 | 实现商店客户端 | `plugin_manager/store.py`：`StoreAPIClient` 类，调用远程商店 API（search/list/detail/download），本地缓存到 `StorePlugin` 表 | 2h | 5.2 | `store.py` |
| 5.6 | 集成到 PluginManager 生命周期 | 在 `enable()` → `activate()` 之间插入 `license_check()`，免费插件跳过 | 1h | 5.3, 1.5 | `__init__.py` 修改 |
| 5.7 | 商店浏览 API + 页面 | `GET /admin/plugins/store` — 浏览商店插件列表、搜索、按分类筛选 | 2h | 5.5, 2.1 | routes + template |
| 5.8 | License 管理 API + 页面 | `POST /admin/plugins/<id>/activate-license`、`/deactivate-license`、`GET /admin/plugins/licenses` | 2h | 5.3, 2.1 | routes + template |
| 5.9 | 更新 sync_schema.py | 加入 plugin_licenses、store_plugins 表 | 0.5h | 5.1, 5.2 | schema 更新 |
| 5.10 | License 引擎单元测试 | mock 远程调用，覆盖在线/离线/过期/未购买/免费插件跳过等场景 | 2h | 5.3, 5.4 | 测试文件 |

**阶段五小计**：约 **17h**（2.5 个工作日内）

#### 验收标准

- [ ] 免费插件安装启用后自动进入 ACTIVE，无需 License
- [ ] 付费插件安装后未激活显示 LICENSE_PENDING，激活后进入 ACTIVE
- [ ] 在线验证不可达时，离线 token 验证生效，宽容期内可正常使用
- [ ] 订阅过期后自动标记 LICENSE_EXPIRED
- [ ] 商店页面能展示远程插件列表，已购插件可一键下载安装

#### 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 远程商店 API 尚未部署 | 高 | 高 | License 引擎设计为 SPI 模式，store.py 和验证 API 可先 mock 开发，后期替换为真实端点 |
| 站点唯一标识（site_id）生成策略 | 中 | 中 | 使用 MAC 地址 + 机器名 + 磁盘序列号组合哈希 |
| 对称加密密钥安全性 | 中 | 高 | 密钥不硬编码，通过环境变量 `PLUGIN_LICENSE_SECRET` 传入 |

---

### 阶段六：支付 + 订阅（P2）

**里程碑**：用户可在商店内购买/订阅插件，支付成功后自动激活 License。

**依赖前提**：阶段五完成（商店和 License 引擎就绪）

#### 任务拆解

| ID | 任务 | 子任务 | 预计工时 | 依赖 | 交付物 |
|----|------|--------|---------|------|--------|
| 6.1 | 实现支付抽象接口 | `plugin_manager/payment.py`：`PaymentProvider` 抽象基类 + `PaymentRouter` 路由 | 1h | 无 | `payment.py` |
| 6.2 | 实现支付宝支付对接 | `AlipayProvider`：当面付（扫码支付）、创建订单、验证回调、退款 | 3h | 6.1 | payment 扩展 |
| 6.3 | 实现微信支付对接（可选） | `WechatPayProvider`：Native 支付 | 2h | 6.1 | payment 扩展 |
| 6.4 | 实现订阅管理 | `plugin_manager/subscription.py`：创建订阅、取消订阅、续费处理、到期提醒 | 2h | 6.1 | `subscription.py` |
| 6.5 | 支付回调 Webhook | POST `/admin/plugins/payment/webhook` — 处理异步通知（支付成功/订阅续费/退款） | 1.5h | 6.1-6.3 | routes 扩展 |
| 6.6 | 购买 API | `POST /admin/plugins/store/<id>/purchase` — 创建订单、返回支付链接 | 1h | 6.1, 5.5 | routes 扩展 |
| 6.7 | 订阅管理 API | `GET /admin/plugins/subscriptions`、`POST /admin/plugins/subscriptions/<id>/cancel` | 1h | 6.4 | routes 扩展 |
| 6.8 | 购买页面 | `templates/plugin_purchase.html`：插件详情、价格展示、扫码支付、支付状态轮询 | 2h | 6.6 | HTML 模板 |
| 6.9 | 授权管理页面 | `templates/plugin_licenses.html`：已购插件列表、License 信息、订阅状态、取消订阅按钮 | 1.5h | 6.7 | HTML 模板 |
| 6.10 | License 服务端 API | `license_server/`：独立的 License 验证 + 生成服务（Flask 蓝图），部署为独立子服务或集成到主站 | 3h | 5.3 | 新服务 |
| 6.11 | 集成测试 | mock 支付回调 + Webhook 全流程验证 | 2h | 6.1-6.10 | |

**阶段六小计**：约 **20h**（3 个工作日内）

#### 验收标准

- [ ] 用户可浏览商店、选择插件、发起购买、扫码支付
- [ ] 支付成功后自动激活 License，插件状态变为 ACTIVE
- [ ] 订阅到期前自动续费（如果开启了自动续费），续费成功延长有效期
- [ ] 取消订阅后不再续费，到期自动标记 LICENSE_EXPIRED
- [ ] License 服务端 API 可独立部署，反向代理集成
- [ ] 支付回调验证签名且幂等（重复通知不重复激活）

#### 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 支付宝/微信支付需要企业资质 | 高 | 高 | 阶段六设计为抽象接口，可先接支付宝沙箱开发，正式上线需企业认证 |
| 支付回调安全性 | 低 | 高 | 必须验证支付宝/微信签名，使用其 SDK 的 verify 方法 |
| 订阅扣款失败 | 中 | 中 | 自动重试 3 次后发送通知给管理员和用户 |

---

### 阶段七：开发者中心（P3）

**里程碑**：第三方开发者可注册、提交插件、上架商店、查看收益。

**依赖前提**：阶段五（商店）、阶段六（支付结算）

#### 任务拆解

| ID | 任务 | 子任务 | 预计工时 | 依赖 | 交付物 |
|----|------|--------|---------|------|--------|
| 7.1 | 实现 Publisher 模型 | `plugin_manager/models_store.py`：`Publisher` 表（name, email, website, verified, revenue_share, payout_email, total_earnings, pending_payout） | 0.5h | 无 | models_store 扩展 |
| 7.2 | 实现开发者管理 | `plugin_manager/publisher.py`：注册、认证、信息修改 | 2h | 7.1 | `publisher.py` |
| 7.3 | 插件提交 API | `POST /admin/plugins/publisher/submit` — 上传 zip 包 + plugin.json，写入待审核队列 | 2h | 7.2 | routes 扩展 |
| 7.4 | 审核流程 | 审核 API（平台管理员审核/拒绝）、安全扫描集成位点 | 2h | 7.3 | 审核模块 |
| 7.5 | 收益统计 API | `GET /admin/plugins/publisher/earnings` — 总收益、待结算、已结算 | 1h | 6.1, 7.2 | routes 扩展 |
| 7.6 | 打包工具 | `scripts/package_plugin.py`：验证 plugin.json 完整性 → 打包为 zip → 生成数字签名 | 2h | 无 | CLI 脚本 |
| 7.7 | 开发者页面 | `templates/plugin_publisher.html`：提交插件表单、已提交列表、审核状态、收益面板 | 2h | 7.3, 7.5 | HTML 模板 |
| 7.8 | 插件下载验签 | 安装时验证 `signature.sig` 与插件内容匹配 | 1h | 7.6, 1.5 | store 扩展 |
| 7.9 | 编写开发者文档 | `docs/plugin-dev-guide.md`：完整的开发指南、API 参考、示例插件 | 3h | 7.6 | 文档 |

**阶段七小计**：约 **15.5h**（2 个工作日内）

#### 验收标准

- [ ] 开发者可注册账号、提交插件包
- [ ] 管理员可审核通过/拒绝插件，审核通过后自动上架商店
- [ ] 其他用户可在商店看到新上架的插件并购买
- [ ] 购买后开发者收益计入待结算
- [ ] 打包工具能生成规范的 zip + 签名文件
- [ ] 安装时发现签名不匹配则拒绝安装

#### 风险

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 插件上传安全风险（恶意代码） | 中 | 高 | 审核流程必须包含人工审查 + 自动安全扫描（沙箱运行验证） |
| 收益结算涉及税务合规 | 高 | 中 | 初期仅记录内部收益数据，正式结算需法务介入 |

---

## 三、阶段依赖关系图

```
阶段一 ────→ 阶段二 ────→ 阶段三
   │                      │
   │                      │
   └──────→ 阶段四 ───────┤
                          │
                          ▼
                    ┌──────┴──────┐
                    │              │
              阶段五 ──────→ 阶段六
                    │              │
                    │              │
                    └──→ 阶段七 ←──┘
```

说明：
- 阶段一、二、三 建议**串行**（核心引擎 → 管理界面 → 标准化，依次依赖）
- 阶段四 可在阶段一后**并行**启动
- 阶段五 需阶段一、二完成
- 阶段六 需阶段五完成
- 阶段七 需阶段五、六完成

**并行优化建议**（如果有多人参与）：

```
人员A：阶段一 → 阶段二 → 阶段五 → 阶段六
人员B：阶段三 → 阶段四 → 阶段七
```

总工期可从 16 周缩短至 **10-12 周**。

---

## 四、关键设计决策清单（需确认）

以下决策影响多个阶段的实现，需要在阶段一启动前确认：

| ID | 决策项 | 选项 | 建议 | 影响范围 |
|----|--------|------|------|---------|
| D1 | PluginRegistry 表放在主库还是插件管理独立库？ | A) 主库 B) `plugin_manager/plugin_manager.db` | **A) 主库** — 便于统一备份和管理 | 阶段一 |
| D2 | 插件状态持久化策略 | A) 仅数据库 B) 数据库 + 文件锁双重记录 | **A) 仅数据库** — 减少复杂性 | 阶段一 |
| D3 | 远程商店/License 服务端部署方式 | A) 集成到主站中的一个蓝图 B) 独立子服务 | **B) 独立子服务** — License 服务端与主站分离，保证即使主站代码泄露 License 核验逻辑不暴露 | 阶段五/六 |
| D4 | 支付接入 | A) 仅支付宝 B) 支付宝 + 微信 | **A) 先仅支付宝** — 降低初期复杂度，微信后续扩展 | 阶段六 |
| D5 | 离线 License 加密算法 | A) AES-256-CBC B) RSA-2048 | **B) RSA-2048** — 非对称加密，私钥仅存服务端，更安全 | 阶段五 |
| D6 | 站点绑定策略 | A) 单站点绑定 B) 按客户绑定（max_sites 控制） | **B) 按客户绑定** — 源码交付模式下，License Key 绑定客户维度，可在 max_sites 个站点激活，不绑定具体域名/机器 | 阶段五 |

---

## 五、插件动态性影响说明

你提到"插件动态性太强，随时更新、新增"，这对系统的几个关键设计点有直接影响：

### 5.1 商店目录实时同步
- 后台商店页面每次加载时，**先请求远程商店目录**，再缓存到本地 `store_plugins` 表
- 远程商店返回的版本号与本地已安装版本对比 → 自动提示更新

### 5.2 版本更新机制
- 安装/启用插件时，自动检查远程商店是否有更新版本
- 有更新时在插件列表页显示"有新版本"标记
- 更新操作 = 下载新版 zip → 停用旧版 → 覆盖文件 → 启用新版

### 5.3 新插件发现
- 商店首页默认按"最新上架"排序
- 已购买未安装的插件在商店中标记"已购"，一键安装
- 不依赖系统版本发布，新插件随时上架即被客户看到

### 5.4 轻量化打包
- 插件包就是 `plugin.json` + 源码，**不需要复杂的编译或构建步骤**
- 开发者提交即上架，减少发布延迟

### 5.5 向后兼容约定
- 插件更新必须保持 `identifier` 不变
- 数据库 Schema 变更只增不删（加列不删列）
- 配置项新增使用默认值，不破坏已有配置

---

## 六、Commit 策略（按阶段）

根据项目 Git 规范（小步提交，不超过 3 个文件），建议各阶段的 Commit 拆分：

| 阶段 | 建议 Commit 数 | 典型 Commit 示例 |
|------|---------------|-----------------|
| 阶段一 | 4-5 个 | 1. feat: 创建 plugin_manager 模块骨架 + PluginRegistry 模型<br>2. feat: 实现 PluginDiscovery 扫描器<br>3. feat: 实现 PluginManager 5 状态机<br>4. feat: 扩展 BasePlugin 基类<br>5. feat: 更新 sync_schema.py + 单元测试 |
| 阶段二 | 3-4 个 | 1. feat: 实现插件管理 REST API<br>2. feat: 实现插件列表 + 详情页 UI<br>3. feat: 实现动态配置表单 + 管理导航集成<br>4. test: API 集成测试 |
| 阶段三 | 5-6 个 | 1. feat: 实现 HookRegistry 钩子系统<br>2. feat: 实现 EventBus<br>3. feat: 在系统关键路径植入钩子点<br>4. feat: ali_api + coupons 插件标准化<br>5. feat: 其余 3 个插件标准化<br>6. fix: 修复 self.t() 作用域问题 |
| 阶段四 | 3-4 个 | 1. feat: 依赖解析器（拓扑排序 + 循环检测）<br>2. feat: 配置 JSON Schema 校验<br>3. feat: 插件独立日志通道<br>4. feat: 增强健康检查 API |
| 阶段五 | 4-5 个 | 1. feat: LicenseRecord + StorePlugin 模型<br>2. feat: License 引擎（在线 + 离线）<br>3. feat: 商店客户端 + 浏览 API<br>4. feat: 集成 License 校验到生命周期<br>5. feat: 商店 + License 管理 UI |
| 阶段六 | 4-5 个 | 1. feat: 支付抽象接口 + 支付宝对接<br>2. feat: 订阅管理模块<br>3. feat: 购买 API + Webhook<br>4. feat: 购买 + License 管理 UI<br>5. feat: License 服务端 API |
| 阶段七 | 4-5 个 | 1. feat: Publisher 模型 + 开发者管理<br>2. feat: 插件提交 + 审核流程<br>3. feat: 打包工具 + 安装验签<br>4. feat: 收益统计 API + 开发者页面<br>5. docs: 插件开发指南 |

---

## 七、每个阶段启动前 Checklist

每个阶段开始前，必须确认：

- [ ] 前置阶段是否已完成并验收通过？
- [ ] 涉及的新表是否已更新到 `sync_schema.py`？
- [ ] 是否有新增的配置项需要加到 `config.py`？
- [ ] 本阶段涉及的 API 是否已考虑安全/权限？
- [ ] 本阶段完成后是否需要同步更新 `docs/` 下的文档？
- [ ] 是否已通知相关协作者（如有）？

---

## 八、总结

| 阶段 | 内容 | 优先级 | 工时 | 建议启动时间 |
|------|------|--------|------|------------|
| 一 | 核心引擎 + 数据库 | P0 | 13.5h | 第 1 周 |
| 二 | 管理 API + 后台 UI | P0 | 13.5h | 第 3 周 |
| 三 | 5 个插件标准化 + 钩子系统 | P1 | 13.5h | 第 6 周 |
| 四 | 高级功能 | P2 | 10h | 第 6 周（可并行） |
| 五 | License + 本地商店 | P1 | 17h | 第 9 周 |
| 六 | 支付 + 订阅 | P2 | 20h | 第 11 周 |
| 七 | 开发者中心 | P3 | 15.5h | 第 13 周 |

**总计工时**：约 **103h**（单人约 16 周，双人约 10 周，三人约 8 周）

---

## 附录：工时估算参考

| 任务类型 | 估算基准 |
|---------|---------|
| 单表模型 + CRUD | 1-2h |
| 新的 Python 类 + 测试 | 2-4h |
| 第三方 API 对接 | 3-4h（含调试） |
| HTML 模板（简单） | 1-2h |
| HTML 模板（复杂，含动态表单） | 2-3h |
| 集成测试 | 2-3h |
| 文档编写 | 1-3h |
