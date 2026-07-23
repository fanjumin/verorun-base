# RavoRun AI v0.35.4 Bug 修复计划

> 基于代码审查结论，2026-07-23

---

## 代码审查结论

| 报告 Bug | 审查结果 | 说明 |
|----------|----------|------|
| BUG-001 LLMGateway 未定义 | 残留引用 | LLMGateway 已合并为 UnifiedLLM，但注释/docstring 残留过时引用 |
| BUG-002 任务 ID 重复键冲突 | **确认存在** | SUBSTR(4) vs {06d} 位数不匹配 + 跨进程不安全 |
| BUG-003 Save 按钮超时 | 确认存在 | fetch 无 .catch/.finally，API 失败时按钮卡死 |
| BUG-004 Mini Programs 模块 | 函数名对不上 | 代码中是 l_mini_apps()，报告报 l_mini_app() |
| BUG-005 AI Chat 响应为空 | 依赖 BUG-001/002 | 修复前两者后大概率自动恢复 |

---

## 修复清单

### BUG-001：清理 LLMGateway 过时引用（P0）

**涉及文件（4 个）：**

| 文件 | 行号 | 内容 |
|------|------|------|
| `agent_matrix/engine.py` | 265 | docstring "合并 AIEngine + 旧 LLMGateway" |
| `auth-center/services/ai_content_generator.py` | 33 | docstring "Call Qwen via LLMGateway" |
| `plugins/content_factory/services/ai_processor.py` | 21 | docstring "Call Qwen via LLMGateway" |
| `plugins/analytics/workflow_nodes.py` | 235 | 注释 "使用 LLMGateway" |

**修复**：替换为 "UnifiedLLM" 或移除过时描述。

---

### BUG-002：修复任务 ID 生成器（P0）

**文件**：`agent_matrix/models.py`（第 92-115 行）

**根因**：
- `_init_task_counter()` 用 `SUBSTR(task_id, -4)` 取 4 位
- `_next_task_id()` 用 `{_task_counter:06d}` 格式化为 6 位
- 内存计数器跨 Gunicorn worker 进程不安全
- 重启后计数器可能归零

**修复方案**：改用 `secrets.token_hex(4)` 生成唯一后缀（与 session ID 和 site builder 一致）

**改动**：
1. 删除 `_task_counter`、`_task_counter_lock`、`_init_task_counter()`
2. 重写 `_next_task_id()` 为 `f'AT-{date}-{secrets.token_hex(4).upper()}'`

---

### BUG-003：修复 Save 按钮错误处理（P1）

**文件**：`admin/templates/partials/provider_api_keys.html`（第 96-117 行）

**修复**：为 `saveKey()` 中的 fetch 添加 `.catch()` 错误提示和 `.finally()` 恢复按钮状态。

---

### BUG-004：Mini Programs 函数名验证（P1）

部署后在服务器执行验证，确认实际注册的函数名。

---

## 执行顺序

1. BUG-001 → 清理注释
2. BUG-002 → 改任务 ID 生成器
3. BUG-003 → 加错误处理
4. 部署 → rsync + 重启服务
5. BUG-004 → 服务器验证
6. 全功能回归测试
