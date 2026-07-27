# 2026-07-26 Dashboard 数据修复方案

## 概述

Dashboard（管理后台首页）部分数据无法正确获取，共涉及 4 类问题，需要修改 3 个文件。

---

## 问题 1：Token Spend / Token 排行榜数据缺失

**现象：** `today_tokens` 和 `top_token_agents` 两个字段不在 API 响应中，图表显示空。

**根因：** `agent_token_daily` 表的 `stat_date` 列是 `TEXT` 类型，但查询/写入时使用 `CURRENT_DATE`（DATE 类型）。PostgreSQL 不支持 `text = date` 隐式转换，导致查询失败、INSERT 失败。

### 修复点

| 文件 | 行 | 查询 | 改动 |
|------|-----|------|------|
| `plugins/analytics/__init__.py` | 195 | `WHERE stat_date=CURRENT_DATE` | → `CURRENT_DATE::text` |
| `plugins/analytics/__init__.py` | 205 | `WHERE t.stat_date=CURRENT_DATE` | → `CURRENT_DATE::text` |
| `agent_matrix/engine.py` | 672 | `VALUES (..., CURRENT_DATE, ...)` | → `CURRENT_DATE::text` |

第 3 处（`engine.py`）修复的是**写入端**——Tokenizer 调用后写日志时因类型不匹配静默失败，导致历史数据断在 7 月 18 日。

---

## 问题 2：recent_users 缺失 + 多个字段被连锁拖垮

**现象：** `recent_users` 不在 API 响应中，`published_posts`、`draft_posts`、`open_tickets`、`urgent_tickets`、`pending_feedback` 等多个字段也为 0。

**根因：** `_build_dashboard_data()` 中 `total_products` 查询 `shop.products` 表 → 表不存在 → 查询失败 → PostgreSQL 事务进入 aborted 状态 → 后续所有查询全部失败。`recent_users` 是"牺牲品"，它本身查询没问题，但被前面的事务中止状态拖累。

### 修复点

| 文件 | 范围 | 改动 |
|------|------|------|
| `auth-center/routes/admin.py` | 6 处 except 块 | `except: pass` → 添加 `conn._conn.rollback()` |

涉及查询：`total_products`、`pending_shipments`、`published_posts/draft_posts`、`open_tickets`、`urgent_tickets`、`pending_feedback`

---

## 问题 3：Agents 计数显示 0

**现象：** `total_agents` 和 `active_agents` 为 0，但系统中实际有 8 个活跃 Agent。

**根因：** 查询了错误的表 `user_agents`（始终为空），应该查 `agent_matrix`。

### 修复点

| 文件 | 行 | 查询 | 改动 |
|------|-----|------|------|
| `auth-center/routes/admin.py` | 165-168 | `FROM user_agents` | → `FROM agent_matrix` |
| | | `WHERE status='active'` | → `WHERE is_active=1` |

---

## 问题 4：API Calls 计数显示 0

**现象：** `today_calls` 和 `total_calls` 为 0。

**根因：** 查询了错误的表 `api_keys` + `agent_api_keys`（均为空），应该查 `agent_token_logs`。API 调用日志实际记录在 `agent_token_logs` 中。

### 修复点

| 文件 | 行 | 查询 | 改动 |
|------|-----|------|------|
| `auth-center/routes/admin.py` | 171-176 | `FROM api_keys` + `FROM agent_api_keys` | → `FROM agent_token_logs`，按 `created_at::date=CURRENT_DATE` 计数 |

---

## 改动文件汇总

| # | 文件 | 改动数 | 影响 |
|---|------|--------|------|
| 1 | `auth-center/routes/admin.py` | 2 处（表名修正 + rollback） | 8083 |
| 2 | `plugins/analytics/__init__.py` | 2 处（CURRENT_DATE::text） | 8083 |
| 3 | `agent_matrix/engine.py` | 1 处（CURRENT_DATE::text） | 8083 |
