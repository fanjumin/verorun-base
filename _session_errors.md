# 会话错误总结 (2026-07-12)

## 根因

1. **用旧 `easykai.db`（46MB，含插件表 + 旧 i18n_strings 4000+ 条）作为数据源导入服务器**，导致已分离的系统数据库被插件表和旧翻译残留污染。

2. **清理数据库时只 `DROP TABLE` 删了插件表，没清 `i18n_strings` 表**（该表存着 1676 条旧翻译残留，其中 1600+ 是插件翻译和旧数据），`_()` 函数优先读 DB，导致页面始终显示旧翻译。

3. **commit `af56cdea` 覆盖了用户做好的 `plugins/analytics/i18n/zh-CN.yml`**，用了旧混杂版本（带 emoji、identity 翻译）。

4. **同步后服务重启**，`init_db()` 重建插件表，`seed_plugin_translations()` 又把插件翻译注入 `i18n_strings`，上传的干净数据库立刻变脏。

5. **`init_db()` 中残留 12 张插件表的 `CREATE TABLE IF NOT EXISTS`**，每次重启都重建，删除操作无效。

## 已修复

- 从本地 `x7k2m9a4.db` 删除 29 张插件残留表
- `i18n_strings` 表：旧 1676 行 → 用当前 YAML（2518 zh-CN + 2495 en）重写为 5013 行
- 所有 `plugins/*/i18n/*.yml` 全量取回远程版本（42 个文件干净）
- 创建管理员 `administrator` / `M!T6?iWh.aLfpRFt`
- 删除本地和服务器旧数据库
- 服务器已同步代码 + 数据库 + 重启服务

## 未修复（`init_db()` 重建插件表）

`auth-center/models/database.py` 的 `init_db()` 中需要删除 12 处插件表创建：

| 行号 | 表名 | 插件 |
|------|------|------|
| L270 | `sms_templates` | sms |
| L350 | `sms_codes` | sms |
| L360 | `sms_rate_limits` | sms |
| L367 | `email_codes` | email |
| L504 | `email_sent` | email |
| L517 | `social_push_logs` | social_push |
| L753 | `payment_events` | payment |
| L944 | `verification_requests` | verification |
| L1101 | `channel_configs` | im_gateway |
| L1227 | `notification_logs` | order_notify |
| L1734 | `oauth_providers` | oauth_config |
| L1920 | `express_companies` | logistics |

## Analytics 国际化状态

- 模板 `analytics.html` 已用 `{{ _('...') }}`（85 个 key）
- 插件 `i18n/zh-CN.yml` 只有 4 行（只覆盖了路由层的 `_t()` 调用）
- 远程也不完整——需要补齐 81 条模板翻译到插件 i18n 文件
