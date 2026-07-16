# 500 错误修复记录（第 1 轮）

> 日期：2026-07-16
> 扫描工具：路由端点自动检测（扫描 :18084 本地实例）
> 扫描结果：392 条路由，344 条报错

## 修复成果

| 轮次 | 提交 | 修复内容 | 状态 |
|------|------|----------|------|
| 1 | `5ad466b` | 4 个 PG 兼容性 Bug：移除 OVERRIDING SYSTEM VALUE、删除过时 ALTER TABLE、修复空集合 DELETE IN 子句、`?`→`%s`（i18n） | ✅ 已部署 |
| 2 | `ed49726` | 8 个 plugins `_PgConnection.execute()` 添加 `sql.replace('?', '%s')` 自动转换 | ✅ 已部署 |

## 错误分类

### 🚨 真实 Bug（已修复）

**1. `InFailedSqlTransaction`（覆盖率最高，影响所有模块）**

根因：`init_db()` 中 `OVERRIDING SYSTEM VALUE` 语法错误 + 重复 ALTER TABLE 列，导致事务中断，后续所有查询报错。

修复：`auth-center/models/database.py` — 移除 OV overriding SYSTEM VALUE 和 4 条过时 ALTER TABLE

**2. 空集合 `NOT IN ()`（影响 agent_matrix）**

根因：YAML 角色集合为空时，`DELETE FROM ... WHERE agent_type NOT IN ()` 为非法 SQL。

修复：`agent_matrix/models.py` — 添加 `if yaml_slugs:` 守卫

**3. `i18n/__init__.py` `?` 占位符（影响 seed_from_yaml）**

根因：`?` 占位符 psycopg2 不识别，需用 `%s`。

修复：`i18n/__init__.py` — 5 处 `?`→`%s`

**4. 43 处 `?` 占位符（影响 8 个插件模块）**

根因：`plugins/ads/routes.py`（17 处）、`plugins/content_factory/routes.py`（26 处）使用 SQLite 风格 `?`，底层 `_PgConnection.execute()` 直接传给 psycopg2 报错。

修复：在 `_PgConnection.execute()` 统一加 `sql.replace('?', '%s')`，波及 8 个文件：

| 文件 | 效果 |
|------|------|
| `plugins/ads/models.py` | 修复 `GET /admin/ads/api/v1/ads` 500 |
| `plugins/content_factory/models.py` | 修复 `GET /api/v1/skills`、`POST /cron/tick` 500 |
| `plugins/ali_api/models.py` | 防御性修复 |
| `plugins/analytics/models.py` | 防御性修复 |
| `plugins/chatbot/models.py` | 防御性修复 |
| `plugins/coupons/models.py` | 防御性修复 |
| `plugins/currency_converter/models.py` | 防御性修复 |
| `plugins/email/models.py` | 防御性修复 |

### ⚠️ 预期 500（无需修复）

| 端点 | 原因 |
|------|------|
| `GET /admin/api/license-status` | try/except 捕获异常返回 500, LicenseService 不可用时预期行为 |
| `POST /admin/api/license-refresh` | 同上 |
| `POST /admin/chatbot/qa_check` | LLM 调用失败时预期行为 |
| `POST /auth/logout` | 扫描未带 token，已修复 |
| `GET /user/verification/callback` | 参数缺失返回 400，已修复 |

### ✅ 已正常工作的公开路由（200 OK）

共 48 条普通 200 路线，涵盖认证、CMS、健康检查等公开接口，未受影响。

## 部署记录

部署工具：`tools/deploy_minor.py`

- 第 1 轮（`5ad466b`）：`agent_matrix/models.py` + `auth-center/models/database.py` + `i18n/__init__.py`
- 第 2 轮（`ed49726`）：8 个 plugins `models.py`

验证结果：`:8081→200, :8083→302, :8084→302, 管理员登录正常`

## 未解决问题

- `plugin.json` BOM 警告（编码问题，不影响功能）
- `seed_from_yaml` 旧日志残留（重启前遗留，已修复）
