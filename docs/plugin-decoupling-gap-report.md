# 插件解耦完整度差距报告

> 生成日期：2026-07-11
> 依据：`docs/plugin-standard-v1.1.md`（§12.2 标准目录）+ `docs/plugin-migration-plan.md`（Phase 2/3/5）
> 目标：为「统一管理 + 订阅制」补齐 3 个半成品插件的物理自包含
> 性质：**只读分析报告，未修改任何代码**

---

## 一、总体结论

17 个插件中 **14 个已彻底自包含**（A 类），符合 v1.1 §12.2 标准目录，可作为订阅制授权单元。

**3 个为半成品（B 类）**：`analytics` / `health_check` / `captcha_embedded`。它们做完了迁移计划的「插件壳 + 独立 DB + 注册解耦」，但**最后一步「实现代码物理迁入 `plugins/<id>/`」未执行**，实现体仍留在顶层目录。

### 对订阅制的直接影响（核心风险）

| 风险 | 说明 |
|------|------|
| **授权闸门可被绕过** | 实现代码在顶层 `analytics/`、`health_check/`，任何模块可 `from analytics.xxx import` 直接调用，**绕过插件壳的订阅/License 校验**。付费订阅形同虚设。 |
| **卸载不干净** | 卸载插件壳后，顶层实现仍在，无法真正"下架"。 |
| **开发范式不统一** | 新人不知该学 A 类还是 B 类，增量混乱。 |

---

## 二、逐模块差距明细

### 2.1 analytics（迁移计划 Phase 2）

**现状**
- 插件壳：`plugins/analytics/`（仅 `__init__.py` + `plugin.json` + `i18n/`）
- 实现体：顶层 `analytics/`（10 个核心 .py + `ip2region/` + `static/china.json` + `templates/analytics.html`）
- DB：`analytics/data/analytics.db`（⚠️ 不符合规范要求的 `plugins/analytics/analytics.db`）

**外部直连点（绕过插件壳）**
| 位置 | 引用 |
|------|------|
| `agent_matrix/tools.py:132` | `from analytics.tracker import generate_report, generate_insight_text` |
| `analytics/workflow_nodes.py` | 注册 orchestrator 工作流节点 `register_analytics_handlers` |
| `platform/app.py:93`、`site/app.py:117` | 已注释（历史遗留，无实际调用） |

**补齐待办**
1. 将 `analytics/` 下实现文件（除 `scripts/` 一次性脚本外）移入 `plugins/analytics/`
2. 改所有 `from analytics.xxx` → `from plugins.analytics.xxx`（或包内相对导入）
3. DB 路径改为 `plugins/analytics/analytics.db`，符合 §12.2
4. `agent_matrix/tools.py:132` 的直连改为经插件壳暴露的接口（或经 hooks）
5. `analytics/scripts/*`（一次性调试脚本，20+ 个）应清理，不随迁移带入

---

### 2.2 health_check（迁移计划 Phase 5）

**现状**
- 插件壳：`plugins/health_check/`（仅 `__init__.py` + `plugin.json` + `i18n/`）
- 实现体：顶层 `health_check/`（ai_fixer/alerter/checkers/discovery/metrics/models/routes/scheduler_setup + `templates/health.html`）
- DB：`data/health.db`（⚠️ 不符合 `plugins/health_check/health_check.db`）

**外部直连点**
| 位置 | 引用 | 说明 |
|------|------|------|
| `agent_matrix/tools.py:87` | `from health_check.models import get_db` | Agent 工具直连 |
| `health_service/app.py:25-26` | `from health_check.routes import health_bp` 等 | ⚠️ **独立服务** health_service 依赖它 |
| `orchestrator` cron_jobs | `scheduler_setup.seed_health_schedules()` 注册定时巡检 | 跨模块耦合 |

**补齐待办**
1. 实现文件移入 `plugins/health_check/`，改引用为 `plugins.health_check.xxx`
2. DB 路径改为 `plugins/health_check/health_check.db`
3. `agent_matrix/tools.py:87` 直连改为经插件接口
4. **`health_service/`（独立服务）需重新定位**：它是否仍要独立部署？若是，则 health_check 实现在插件目录后，health_service 需改为从 `plugins.health_check` 导入——这是本模块最大的耦合点，需专门评估
5. orchestrator cron 注册方式保持（迁移计划 Phase 5 已注明"改 cron_jobs 注册方式"）

---

### 2.3 captcha_embedded（迁移计划 Phase 3）

**现状**
- 插件壳：`plugins/captcha_embedded/`（仅 `__init__.py` + `plugin.json` + `i18n/`）
- 实现体：顶层 `captcha_bp.py` + `captcha-service/`（**独立服务，端口 8090**）
- 插件壳 `from captcha_bp import captcha_bp, init_i18n`

**关键特殊性**
- `captcha-service/` 是**独立运行的 Flask 服务（8090）**，通过 Platform/Admin 反向代理接入
- `captcha_bp.py` 是嵌入式蓝图（同进程），与独立服务是**两套并存**

**补齐待办**
1. 明确定位：captcha 到底是「嵌入式插件」还是「独立服务」？两者当前并存，需二选一或明确分工
2. 若走插件路线：`captcha_bp.py` + 核心逻辑移入 `plugins/captcha_embedded/`
3. 独立服务 `captcha-service/` 的去留需单独决策（它不在 plugins 管理范畴）

---

## 三、明确保留不动（核心组件，非插件）

依据 migration-plan「保留不动」清单：
- `agent_matrix/` — AI Agent 矩阵，与 AI 引擎内核绑定
- `cognition-service/` — RAG 向量检索，核心依赖
- `orchestrator/` — 工作流引擎（被多插件依赖的基础设施）
- `site_builder/` — 建站核心（非可插拔业务插件）
- `providers/` — 第三方 provider 适配层（公共服务，§12.5 规定"公共服务原地保留"）

---

## 四、建议推进顺序（风险从低到高）

| 顺序 | 模块 | 风险 | 理由 |
|------|------|------|------|
| ① | **captcha_embedded** | 中 | 外部直连少（仅插件壳），但需先决策独立服务去留 |
| ② | **analytics** | 中高 | 直连点少（tools.py + workflow_nodes），但文件多、DB 路径要迁 |
| ③ | **health_check** | 高 | 被独立服务 health_service + agent_matrix + orchestrator 三方依赖，耦合最深 |

**每个模块迁移遵循**：物理移入 → 改引用 → 改 DB 路径 → 验证 `node --check`/服务启动 → 单独提交，逐个验证，杜绝一次性大改。

---

## 五、订阅制落地的前置结论

- 底座已就绪：`plugin_manager/subscription.py`（SubscriptionManager）+ `license.py`（校验）+ `store.py`/`payment.py`
- **订阅制要真正生效（授权不可绕过），依赖上述 3 个模块彻底自包含**——否则顶层实现可被直连绕过闸门
- 建议：先完成本报告的 3 个模块补齐，再全量补 plugin.json 订阅字段 + 在 enable/activate 接入订阅校验
