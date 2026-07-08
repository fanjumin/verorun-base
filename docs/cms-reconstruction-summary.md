# CMS 重构改动总览

> 生成日期：2026-07-08 | 数据来源：git 提交记录（真实核验）
> 提交范围：`1bc83c8` → `6858163`（本次会话 8 个提交）

---

## 一、提交清单（真实 git stat）

| 提交 | 说明 | 变更 |
|------|------|------|
| `1bc83c8` | 补全 6 个缺失图标（admins/ai_chat/channels/email/logs/tickets） | 2 文件 +29/-1 |
| `eb238cd` | 阶段三-A：Social Push、Publish History 接入 Automation 菜单 | 3 文件 +49/-12 |
| `3a4659c` | 阶段三 3.6：新建 workflow_triggers 表 | 1 文件 +17 |
| `e4541b8` | 阶段三 3.4：4 个内容工作流模板 + 只读 GET 端点 | 2 文件 +143 |
| `bd4712f` | 阶段三 3.5：发布事件分发匹配工作流 | 2 文件 +82 |
| `9879f45` | 文档：标记 3.4/3.5/3.6 完成，记录 commit bug 阻塞项 | 1 文件 +5/-3 |
| `6fe2625` | 修复：get_db() 自动 commit/rollback，写操作正确持久化 | 2 文件 +10/-2 |
| `6858163` | 文档：放弃 3.7（保留 Risk & Audit 分组以免丢功能） | 1 文件 +1/-1 |

> 注：阶段一/二的提交（`45faf64` / `b289c59` / `b3e6e12` / `c237eb7`）在更早的会话完成，不在本表统计范围内。

---

## 二、按功能模块的改动

### 1. 菜单结构（icons.html）
- 补全 6 个被引用但未定义的图标，消除前端 `I.xxx is not a function` 风险
- Automation 分组新增 `Social Push`、`Publish History` 两个入口

### 2. 社交发布与历史（social.html）
- 原孤立的 `l_social` 页面接入 `social` 菜单键
- 新增 `l_publish_history` 独立页，复用 `/admin/social/history` API

### 3. 工作流自动化（orchestrator/）
- **workflow_triggers 表**（models.py）：事件驱动基础，幂等建表，建在 orchestrator 库
- **4 个工作流模板**（workflow_templates.py，新建）：每日采集、定时静态生成、社交自动发布、知识库同步；作为只读蓝图，经 `GET /admin/automation/workflow-templates` 暴露
- **事件分发**（trigger_dispatch.py，新建）：`dispatch_event()` 按事件+条件匹配触发工作流，全程 try/except 不影响调用方

### 4. 发布主流程（cms_admin.py）
- `publish_post()` 发布后新增 fire-and-forget 调用 `dispatch_event('cms.published', ...)`，失败静默不影响发布

### 5. 缺陷修复（orchestrator/models.py）
- `get_db()` 上下文管理器：正常退出 `commit()`、异常 `rollback()`
- 修复了 create/update/delete 工作流与 cron 任务因缺少 commit 而被回滚、无法持久化的既有 bug

---

## 三、验证情况

| 改动 | 验证方式 | 结果 |
|------|---------|------|
| 图标补全 | git diff 前后对比 | 6 个图标确认存在 |
| 菜单/页面接入 | Grep 回读 + go() 路由链核对 | 通过 |
| workflow_triggers 表 | 临时库实跑建表，查 sqlite_master | 表/索引/8 字段确认 |
| 工作流模板 | 断言结构合法、节点类型有效、edge 无悬空、可 JSON 序列化 | 4 模板通过 |
| 事件分发 | 单元测试命中/不命中/空 context | ALL_PASS |
| commit 修复 | create/update/delete/instance/rollback 6 项 | ALL_PASS |

---

## 四、未完成 / 主动放弃

| 项 | 状态 | 原因 |
|----|------|------|
| 2.4 Agent 内容写入 cms_posts | 未做 | 原方案标注"可选" |
| 3.7 删除 Risk & Audit 分组 | 放弃 | 前提 2.4 未落地；Post Audit（agent_experiences 表）与 All Content（cms_posts 表）数据源不同，无法替代；Comment Moderation 为独立功能。保功能优先于菜单精简 |

---

## 五、部署注意事项

1. **数据库**：workflow_triggers 表通过 `init_orchestrator_tables()` 幂等创建，无需手动迁移
2. **触发器目前为空**：workflow_triggers 表已就绪但无预置数据，发布事件暂不会触发任何工作流，需后续在管理界面绑定触发器
3. **模板为只读蓝图**：不写库，用户需从模板实例化后才生成可运行工作流
4. 所有改动向后兼容，未删除任何现有 API 路由
